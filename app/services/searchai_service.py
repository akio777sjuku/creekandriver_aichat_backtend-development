import os
import re
import asyncio
import base64
from dataclasses import dataclass
from quart import current_app
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    HnswParameters,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)
from azure.search.documents.models import (
    QueryCaptionResult,
    QueryType,
    VectorQuery,
)
from typing import Any, List, Optional, cast
from typing import List, Optional

from app.models.file import File
from app.services.textsplitter import SplitPage
from app.services.openai_service import OpenaiService
from app.extensions import get_searchai_client, get_searchai_index_client
from app.utils.log_utils import get_logger
from app.utils.commom import nonewlines
logger = get_logger("aoai_backend")


class Section:
    """
    A section of a page that is stored in a search service. These sections are used as context by Azure OpenAI service
    """

    def __init__(self, split_page: SplitPage, content: File, category: Optional[str] = None):
        self.split_page = split_page
        self.content = content
        self.category = category

    def filename_to_id(self):
        filename_ascii = re.sub("[^0-9a-zA-Z_-]", "_", self.content.name)
        filename_hash = base64.b16encode(
            self.content.name.encode("utf-8")).decode("ascii")
        return f"file-{filename_ascii}-{filename_hash}"


@dataclass
class Document:
    id: Optional[str]
    content: Optional[str]
    embedding: Optional[List[float]]
    file_id: Optional[str]
    chat_type: Optional[str]
    category: Optional[str]
    sourcepage: Optional[str]
    sourcefile: Optional[str]
    storageUrl: Optional[str]
    captions: List[QueryCaptionResult]
    score: Optional[float] = None
    reranker_score: Optional[float] = None

    def serialize_for_results(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "embedding": Document.trim_embedding(self.embedding),
            "category": self.category,
            "sourcepage": self.sourcepage,
            "sourcefile": self.sourcefile,
            "captions": (
                [
                    {
                        "additional_properties": caption.additional_properties,
                        "text": caption.text,
                        "highlights": caption.highlights,
                    }
                    for caption in self.captions
                ]
                if self.captions
                else []
            ),
            "score": self.score,
            "reranker_score": self.reranker_score,
        }

    @classmethod
    def trim_embedding(cls, embedding: Optional[List[float]]) -> Optional[str]:
        """Returns a trimmed list of floats from the vector embedding."""
        if embedding:
            if len(embedding) > 2:
                # Format the embedding list to show the first 2 items followed by the count of the remaining items."""
                return f"[{embedding[0]}, {embedding[1]} ...+{len(embedding) - 2} more]"
            else:
                return str(embedding)

        return None


class SearchManager:
    def __init__(self):
        self.search_index_client = get_searchai_index_client()
        self.search_client = get_searchai_client()
        self.search_index_name = current_app.config.get("SEARCH_INDEX")
        self.openai_service = OpenaiService()

    def __sourcepage_from_file_page(cls, filename, page=0) -> str:
        if os.path.splitext(filename)[1].lower() == ".pdf":
            return f"{os.path.basename(filename)}#page={page+1}"
        else:
            return os.path.basename(filename)

    async def create_index(self):
        logger.info("Ensuring search index %s exists", self.search_index_name)

        fields = [
            SimpleField(name="id", type="Edm.String", key=True),
            SearchableField(
                name="content",
                type="Edm.String",
                analyzer_name="en.microsoft",
            ),
            SearchField(
                name="embedding",
                type=SearchFieldDataType.Collection(
                    SearchFieldDataType.Single),
                hidden=False,
                searchable=True,
                filterable=False,
                sortable=False,
                facetable=False,
                vector_search_dimensions=1536,
                vector_search_profile_name="default",
            ),
            SimpleField(
                name="file_id",
                type="Edm.String",
                filterable=True,
                facetable=True,
            ),
            SimpleField(
                name="chat_type",
                type="Edm.String",
                filterable=True,
            ),
            SimpleField(
                name="sourcepage",
                type="Edm.String",
                filterable=True,
                facetable=True,
            ),
            SimpleField(
                name="sourcefile",
                type="Edm.String",
                filterable=True,
                facetable=True,
            ),
            SimpleField(
                name="storageUrl",
                type="Edm.String",
                filterable=True,
                facetable=False,
            ),

            SimpleField(
                name="category",
                type="Edm.String",
                filterable=True,
                facetable=True),
        ]

        index = SearchIndex(
            name=self.search_index_name,
            fields=fields,
            semantic_search=SemanticSearch(
                configurations=[
                    SemanticConfiguration(
                        name="default",
                        prioritized_fields=SemanticPrioritizedFields(
                            title_field=None, content_fields=[SemanticField(field_name="content")]
                        ),
                    )
                ]
            ),
            vector_search=VectorSearch(
                algorithms=[
                    HnswAlgorithmConfiguration(
                        name="hnsw_config",
                        parameters=HnswParameters(metric="cosine"),
                    )
                ],
                profiles=[
                    VectorSearchProfile(
                        name="default",
                        algorithm_configuration_name="hnsw_config",
                    ),
                ]
            )
        )
        if self.search_index_name not in [name async for name in self.search_index_client.list_index_names()]:
            logger.info("Creating %s search index", self.search_index_name)
            await self.search_index_client.create_index(index)

    async def update_content(self, sections: List[Section]):
        await self.create_index()

        MAX_BATCH_SIZE = 1000
        section_batches = [sections[i: i + MAX_BATCH_SIZE]
                           for i in range(0, len(sections), MAX_BATCH_SIZE)]

        for batch_index, batch in enumerate(section_batches):
            documents = [
                {
                    "id": f"{section.filename_to_id()}-page-{section_index + batch_index * MAX_BATCH_SIZE}",
                    "content": section.split_page.text,
                    "category": section.category,
                    "sourcepage": (
                        self.__sourcepage_from_file_page(
                            filename=section.content.name,
                            page=section.split_page.page_num,
                        )
                    ),
                    "sourcefile": section.content.name,
                    "storageUrl": section.content.file_url,
                    "file_id": section.content.id,
                    "chat_type": section.content.chat_type,

                }
                for section_index, section in enumerate(batch)
            ]

            embeddings = await self.openai_service.create_embedding_batch(texts=[section.split_page.text for section in batch])
            for i, document in enumerate(documents):
                document["embedding"] = embeddings[i]

            await self.search_client.upload_documents(documents)

    async def remove_content(self, file_id: str, chat_type: str):
        while True:
            filter = f"file_id eq '{file_id}' and chat_type eq '{chat_type}'"
            max_results = 1000
            result = await self.search_client.search(
                search_text="", filter=filter, top=max_results, include_total_count=True
            )
            result_count = await result.get_count()
            if result_count == 0:
                break
            documents_to_remove = []
            async for document in result:
                documents_to_remove.append({"id": document["id"]})
            removed_docs = await self.search_client.delete_documents(documents_to_remove)
            logger.info("Removed %d sections from index", len(removed_docs))
            # It can take a few seconds for search results to reflect changes, so wait a bit
            await asyncio.sleep(2)

    async def search(
        self,
        top: int,
        query_text: Optional[str],
        filter: Optional[str],
        vectors: List[VectorQuery],
        use_semantic_ranker: bool = True,
        minimum_search_score: Optional[float] = 0.0,
        minimum_reranker_score: Optional[float] = 0.0,
    ) -> List[Document]:
        search_text = query_text
        search_vectors = vectors
        if use_semantic_ranker:
            results = await self.search_client.search(
                search_text=search_text,
                filter=filter,
                top=top,
                query_caption="extractive|highlight-false",
                vector_queries=search_vectors,
                query_type=QueryType.SEMANTIC,
                semantic_configuration_name="default",
                semantic_query=query_text,
            )
        else:
            results = await self.search_client.search(
                search_text=search_text,
                filter=filter,
                top=top,
                vector_queries=search_vectors,
            )

        documents: List[Document] = []
        async for page in results.by_page():
            async for document in page:
                documents.append(
                    Document(
                        id=document.get("id"),
                        content=document.get("content"),
                        embedding=document.get("embedding"),
                        file_id=document.get("file_id"),
                        chat_type=document.get("chat_type"),
                        category=document.get("category"),
                        sourcepage=document.get("sourcepage"),
                        sourcefile=document.get("sourcefile"),
                        storageUrl=document.get("storageUrl"),
                        captions=cast(List[QueryCaptionResult],
                                      document.get("@search.captions")),
                        score=document.get("@search.score"),
                        reranker_score=document.get("@search.reranker_score"),
                    )
                )

            qualified_documents = [
                doc
                for doc in documents
                if (
                    (doc.score or 0) >= (minimum_search_score or 0)
                    and (doc.reranker_score or 0) >= (minimum_reranker_score or 0)
                )
            ]

        return qualified_documents

    def build_filter(self, chat_type: str, file_ids: List[str]) -> Optional[str]:
        filters = []
        if file_ids:
            file_ids_str = ','.join(file_ids)
            search_query = f"search.in(file_id, '{file_ids_str}')"
            filters.append(search_query)
        if chat_type:
            filters.append("chat_type eq '{}'".format(chat_type))
        return None if len(filters) == 0 else " and ".join(filters)

    def get_sources_content(
        self, results: List[Document], use_semantic_captions: bool
    ) -> list[str]:
        if use_semantic_captions:
            return [
                doc.sourcepage + ": " +
                nonewlines(" . ".join([cast(str, c.text)
                           for c in (doc.captions or [])]))
                for doc in results
            ]
        else:
            return [
                doc.sourcepage + ": " + nonewlines(doc.content or "")for doc in results
            ]
