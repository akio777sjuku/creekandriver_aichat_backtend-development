import re
import json
import tiktoken
from uuid import uuid1
from quart import current_app
from typing import List
from azure.cosmos import PartitionKey
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_random_exponential,
)
from openai.types.chat import (
    ChatCompletion,
    ChatCompletionMessageParam,
    ChatCompletionToolParam,
)
from azure.search.documents.models import VectorizedQuery

from openai import RateLimitError
from openai_messages_token_helper import build_messages, get_token_limit
from app.extensions import get_openai_client, get_cosmos_client
from app.utils.log_utils import get_logger
from app.exceptions.service_exception import ServiceException
from openai.types.chat import ChatCompletionMessageParam
from app.constants import GPT_4O_MODEL, EMBEDING_MODEL, CHAT_CONTAINER

logger = get_logger("aoai_backend")


class EmbeddingBatch:
    """
    Represents a batch of text that is going to be embedded
    """

    def __init__(self, texts: List[str], token_length: int):
        self.texts = texts
        self.token_length = token_length


class OpenaiService():

    def __init__(self):
        self.openai_client = get_openai_client()
        self.openai_model = current_app.config["OPENAI_MODEL"]
        cosmos_db = get_cosmos_client().create_database_if_not_exists(
            id=current_app.config["COSMOSDB_DATABASE"])
        self.chat_cosmos = cosmos_db.create_container_if_not_exists(id=CHAT_CONTAINER,
                                                                    partition_key=PartitionKey(path="/type"))

    def __calculate_token_length(self, text: str):
        encoding = tiktoken.encoding_for_model(
            self.openai_model[EMBEDING_MODEL])
        return len(encoding.encode(text))

    def __split_text_into_batches(self, texts: List[str]) -> List[EmbeddingBatch]:
        SUPPORTED_BATCH_AOAI_MODEL = {
            "text-embedding-ada-002": {"token_limit": 8100, "max_batch_size": 16},
            "text-embedding-3-small": {"token_limit": 8100, "max_batch_size": 16},
            "text-embedding-3-large": {"token_limit": 8100, "max_batch_size": 16},
        }
        batch_info = SUPPORTED_BATCH_AOAI_MODEL[EMBEDING_MODEL]
        batch_token_limit = batch_info["token_limit"]
        batch_max_size = batch_info["max_batch_size"]

        batches: List[EmbeddingBatch] = []
        batch: List[str] = []
        batch_token_length = 0
        for text in texts:
            text_token_length = self.__calculate_token_length(text)
            if batch_token_length + text_token_length >= batch_token_limit and len(batch) > 0:
                batches.append(EmbeddingBatch(batch, batch_token_length))
                batch = []
                batch_token_length = 0

            batch.append(text)
            batch_token_length = batch_token_length + text_token_length
            if len(batch) == batch_max_size:
                batches.append(EmbeddingBatch(batch, batch_token_length))
                batch = []
                batch_token_length = 0

        if len(batch) > 0:
            batches.append(EmbeddingBatch(batch, batch_token_length))

        return batches

    def __before_retry_sleep(self, retry_state):
        logger.info(
            "Rate limited on the OpenAI embeddings API, sleeping before retrying...")

    async def create_embedding_batch(self, texts: List[str]) -> List[List[float]]:
        try:
            batches = self.__split_text_into_batches(texts)
            embeddings = []
            for batch in batches:
                async for attempt in AsyncRetrying(
                    retry=retry_if_exception_type(RateLimitError),
                    wait=wait_random_exponential(min=15, max=60),
                    stop=stop_after_attempt(15),
                    before_sleep=self.__before_retry_sleep,
                ):
                    with attempt:
                        emb_response = await self.openai_client.embeddings.create(
                            model=self.openai_model[EMBEDING_MODEL], input=batch.texts
                        )
                        embeddings.extend(
                            [data.embedding for data in emb_response.data])
                        logger.info(
                            "Computed embeddings in batch. Batch size: %d, Token count: %d",
                            len(batch.texts),
                            batch.token_length,
                        )
            return embeddings
        except Exception as e:
            logger.exception(f"エンベディング（バッチ）する際にエラーが発生します。: {e}")
            raise ServiceException(
                "エンベディング（バッチ）する際にエラーが発生します。", status_code=500)

    async def create_embedding_single(self, text: str) -> List[float]:
        try:
            async for attempt in AsyncRetrying(
                retry=retry_if_exception_type(RateLimitError),
                wait=wait_random_exponential(min=15, max=60),
                stop=stop_after_attempt(15),
                before_sleep=self.__before_retry_sleep,
            ):
                with attempt:
                    emb_response = await self.openai_client.embeddings.create(
                        model=self.openai_model[EMBEDING_MODEL], input=text
                    )
                    logger.info(
                        "Computed embedding for text section. Character count: %d", len(text))
            return emb_response.data[0].embedding
        except Exception as e:
            logger.exception(f"エンベディング（シングル）する際にエラーが発生します。: {e}")
            raise ServiceException(
                "エンベディング（シングル）する際にエラーが発生します。", status_code=500)

    async def compute_text_embedding(self, q: str):
        try:
            embedding = await self.openai_client.embeddings.create(
                model=self.openai_model[EMBEDING_MODEL],
                input=q
            )
            query_vector = embedding.data[0].embedding
            return VectorizedQuery(vector=query_vector, k_nearest_neighbors=50, fields="embedding")
        except Exception as e:
            logger.exception(f"エンベディング（検索）する際にエラーが発生します。: {e}")
            raise ServiceException(
                "エンベディングする際にエラーが発生します。", status_code=500)

    async def generateSearchQuery(self, history) -> str:
        NO_RESPONSE = "0"
        query_prompt_template = """Below is a history of the conversation so far, and a new question asked by the user that needs to be answered by searching in a knowledge base.
        You have access to Azure AI Search index with 100's of documents.
        Generate a search query based on the conversation and the new question.
        Do not include cited source filenames and document names e.g info.txt or doc.pdf in the search query terms.
        Do not include any text inside [] or <<>> in the search query terms.
        Do not include any special characters like '+'.
        If you cannot generate a search query, return just the number 0.
        """
        query_prompt_few_shots: list[ChatCompletionMessageParam] = [
            {"role": "user", "content": "How did crypto do last year?"},
            {"role": "assistant",
                "content": "Summarize Cryptocurrency Market Dynamics from last year"},
            {"role": "user", "content": "What are my health plans?"},
            {"role": "assistant", "content": "Show available health plans"},
        ]
        query_response_token_limit = 100
        tools: List[ChatCompletionToolParam] = [
            {
                "type": "function",
                "function": {
                    "name": "search_sources",
                    "description": "Retrieve sources from the Azure AI Search index",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "search_query": {
                                "type": "string",
                                "description": "Query string to retrieve documents from azure search",
                            }
                        },
                        "required": ["search_query"],
                    },
                },
            }
        ]
        messages: list[ChatCompletionMessageParam] = []
        try:
            for item in history[:-1]:
                messages.append({"role": "user", "content": item["user"]})
                messages.append({"role": "assistant", "content": item["bot"]})
            user_query_request = "Generate search query for: " + \
                history[-1]["user"]
            query_messages = build_messages(
                model=GPT_4O_MODEL,
                system_prompt=query_prompt_template,
                tools=tools,
                few_shots=query_prompt_few_shots,
                past_messages=messages,
                new_user_content=user_query_request,
                max_tokens=get_token_limit(
                    GPT_4O_MODEL) - query_response_token_limit,
            )
            chat_completion: ChatCompletion = await self.openai_client.chat.completions.create(
                messages=query_messages,
                model=self.openai_model[GPT_4O_MODEL],
                temperature=0.0,
                max_tokens=query_response_token_limit,
                n=1,
                tools=tools,
            )
            response_message = chat_completion.choices[0].message
            if response_message.tool_calls:
                for tool in response_message.tool_calls:
                    if tool.type != "function":
                        continue
                    function = tool.function
                    if function.name == "search_sources":
                        arg = json.loads(function.arguments)
                        search_query = arg.get("search_query", NO_RESPONSE)
                        if search_query != NO_RESPONSE:
                            return search_query
            elif query_text := response_message.content:
                if query_text.strip() != NO_RESPONSE:
                    return query_text
            return history[-1]["user"]

        except Exception as e:
            logger.exception(f"検索内容を生成する際にエラーが発生します。: {e}")
            raise ServiceException(
                "検索内容を生成する際にエラーが発生します。", status_code=500)

    async def answerQueation(self, chat_id, chat_type, history, sources):
        system_message = """You are an assistant. Please provide helpful, accurate, and concise responses based on the conversation history and the user's last question.
        If asking a clarifying question to the user would help, ask the question.
        If the question is not in English, answer in the language used in the question."""

        messages: list[ChatCompletionMessageParam] = []
        try:
            # Loop through the chat history except the last message
            for item in history[:-1]:
                messages.append({"role": "user", "content": item["user"]})
                messages.append({"role": "assistant", "content": item["bot"]})

            response_token_limit = 2048
            new_user_content = history[-1]["user"] if not sources else history[-1]["user"] + \
                "\n\nSources:\n" + sources

            queation_messages = build_messages(
                model=GPT_4O_MODEL,
                system_prompt=system_message,
                past_messages=messages,
                new_user_content=new_user_content,
                max_tokens=get_token_limit(
                    GPT_4O_MODEL) - response_token_limit,
            )
            # Add the last user message
            messages.append({"role": "user", "content": history[-1]["user"]})
            completion = await self.openai_client.beta.chat.completions.parse(
                model=self.openai_model[GPT_4O_MODEL],
                messages=queation_messages,
                temperature=0.3,
                max_tokens=response_token_limit
            )
            answer = completion.choices[0].message.content
            # save the chat content
            chat_content = {"id": str(uuid1()),
                            "type": chat_type,
                            "chat_id": chat_id,
                            "index": len(history),
                            "question": history[-1]["user"],
                            "answer": answer}
            self.chat_cosmos.create_item(chat_content)
            return answer
        except Exception as e:
            logger.exception(f"回答を生成する際にエラーが発生します。: {e}")
            raise ServiceException(
                "回答を生成する際にエラーが発生します。", status_code=500)

    async def generateChatName(self, history, answer) -> str:
        try:
            system_message = """You are tasked with creating a brief and precise title based on the conversation. The title should be clear, directly related to the discussion, and must not exceed 20 characters."""
            messages: list[ChatCompletionMessageParam] = []
            messages.append({"role": "system", "content": system_message})
            messages.append({"role": "user", "content": history[-1]["user"]})
            messages.append({"role": "assistant", "content": answer})
            completion = await self.openai_client.beta.chat.completions.parse(
                model=self.openai_model[GPT_4O_MODEL],
                messages=messages,
                temperature=0.3,
                max_tokens=50
            )
            title = completion.choices[0].message.content
            return title
        except Exception as e:
            logger.exception(f"チャット名を生成する際にエラーが発生します。: {e}")
            raise ServiceException(
                "チャット名を生成する際にエラーが発生します。", status_code=500)
