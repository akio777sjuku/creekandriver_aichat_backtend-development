from datetime import datetime
from quart import (Blueprint, jsonify, request, g)
from azure.search.documents.models import VectorQuery
from app.services.file_service import FileService
from app.services.chat_service import ChatService
from app.services.openai_service import OpenaiService
from app.services.searchai_service import SearchManager
from app.utils.decorators import token_required
from app.utils.log_utils import get_logger
from app.utils.commom import extract_urls
from app.exceptions.service_exception import ServiceException

answer_bp = Blueprint("answer", __name__)
logger = get_logger("aoai_backend")


@answer_bp.route("", methods=["POST"])
@token_required
async def makeAnswer():
    if not request.is_json:
        return jsonify({"error": "request must be json"}), 415
    request_json = await request.get_json()
    email = g.get('email')
    try:
        chat_service = ChatService()
        openai_service = OpenaiService()
        file_service = FileService()
        search_manager = SearchManager()
        chat_id = request_json["chat_id"]
        chat_type = request_json["chat_type"]
        history = request_json["history"]
        answer: str = ""
        if chat_type == "gpt":
            # check URL exist
            urls = extract_urls(history[-1]["user"])
            if (len(urls) > 0):
                # save URL content
                for url in urls:
                    file_url = await file_service.saveUrl(url, chat_id, email)
                    file_sections = await file_service.parse_url(file_url)
                    if file_sections:
                        # save file to Azure Search AI
                        await search_manager.update_content(file_sections)

            # check file exist
            files = await file_service.getFilesByChatId(chat_id)
            if len(files) > 0:
                # STEP 1: Generate an optimized keyword search query based on the chat history and the last question
                query_text = await openai_service.generateSearchQuery(history)
                # STEP 2: Retrieve relevant documents from the search index with the GPT optimized query
                file_ids = [file.id for file in files]
                filter = search_manager.build_filter(chat_type, file_ids)
                vectors: list[VectorQuery] = []
                vectors.append(await openai_service.compute_text_embedding(query_text))
                results = await search_manager.search(3, query_text, filter, vectors)
                sources_content = search_manager.get_sources_content(
                    results, True)
                sources = "\n".join(sources_content)
                # STEP 3: Generate a contextual and content specific answer using the search results and chat history
                answer = await openai_service.answerQueation(
                    chat_id, chat_type, history, sources)
            else:
                answer = await openai_service.answerQueation(chat_id, chat_type, history, "")
        elif chat_type == "retrieve":
            # STEP 1: Generate an optimized keyword search query based on the chat history and the last question
            query_text = await openai_service.generateSearchQuery(history)
            # STEP 2: Retrieve relevant documents from the search index with the GPT optimized query
            filter = search_manager.build_filter(chat_type, [])
            vectors: list[VectorQuery] = []
            vectors.append(await openai_service.compute_text_embedding(query_text))
            results = await search_manager.search(3, query_text, filter, vectors)
            sources_content = search_manager.get_sources_content(
                results, True)
            sources = "\n".join(sources_content)
            # STEP 3: Generate a contextual and content specific answer using the search results and chat history
            answer = await openai_service.answerQueation(
                chat_id, chat_type, history, sources)

        # チャット更新
        chat_update_data = {
            "updated_by": email,
            "updated_at": datetime.now()}
        if len(history) == 1:
            chat_update_data["name"] = await openai_service.generateChatName(history, answer)
        await chat_service.updateChat(chat_id, chat_update_data)
        return jsonify({"answer": answer}), 200
    except ServiceException as se:
        return jsonify({"message": str(se)}), se.status_code
    except Exception as e:
        logger.exception(f"回答を生成する際に、エラーが発生します。{e}")
        return jsonify({"message": "回答を生成する際に、エラーが発生します"}), 500
