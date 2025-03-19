import os
import re
from io import BytesIO
from uuid import uuid1
from quart import current_app
from sqlalchemy import desc, not_, and_
from sqlalchemy.future import select
from typing import List, Optional
from werkzeug.datastructures import MultiDict, FileStorage
from azure.storage.blob import BlobClient
from azure.core.credentials import AzureKeyCredential
from langchain_community.document_loaders import WebBaseLoader
from app.extensions import get_storage_client
from app.database import get_db_session, db_transaction
from app.models import file as file_models
from app.services.parser.fileprocessor import FileProcessor
from app.services.parser.parser import Parser
from app.services.parser.pdfparser import DocumentAnalysisParser, LocalPdfParser
from app.services.parser.htmlparser import LocalHTMLParser
from app.services.parser.jsonparser import JsonParser
from app.services.parser.textparser import TextParser
from app.services.textsplitter import SentenceTextSplitter, SimpleTextSplitter
from app.services.searchai_service import Section
from app.utils.log_utils import get_logger
from app.exceptions.service_exception import ServiceException


logger = get_logger("aoai_backend")


class FileService():
    def __init__(self):
        self.storage_client = get_storage_client()
        self.storage_container_client = get_storage_client(
        ).get_container_client(current_app.config.get("STORAGE_CONTAINER"))
        self.file_processors: dict[str,
                                   FileProcessor] = self.__setup_file_processors()

    def __setup_file_processors(
        local_pdf_parser: bool = False,
        local_html_parser: bool = False,
        search_images: bool = False,
    ):
        html_parser: Parser
        pdf_parser: Parser
        doc_int_parser: DocumentAnalysisParser

        document_intelligence_service = current_app.config["DOCUMENTINTELLIGENCE_SERVICE"]
        document_intelligence_key = current_app.config["DOCUMENTINTELLIGENCE_KEY"]
        documentintelligence_creds = AzureKeyCredential(
            document_intelligence_key)
        doc_int_parser = DocumentAnalysisParser(
            endpoint=document_intelligence_service,
            credential=documentintelligence_creds,
        )
        if local_pdf_parser or document_intelligence_service is None:
            pdf_parser = LocalPdfParser()
        else:
            pdf_parser = doc_int_parser
        if local_html_parser or document_intelligence_service is None:
            html_parser = LocalHTMLParser()
        else:
            html_parser = doc_int_parser
        sentence_text_splitter = SentenceTextSplitter(
            has_image_embeddings=search_images)
        return {
            ".pdf": FileProcessor(pdf_parser, sentence_text_splitter),
            ".html": FileProcessor(html_parser, sentence_text_splitter),
            ".json": FileProcessor(JsonParser(), SimpleTextSplitter()),
            ".docx": FileProcessor(doc_int_parser, sentence_text_splitter),
            ".pptx": FileProcessor(doc_int_parser, sentence_text_splitter),
            ".xlsx": FileProcessor(doc_int_parser, sentence_text_splitter),
            ".png": FileProcessor(doc_int_parser, sentence_text_splitter),
            ".jpg": FileProcessor(doc_int_parser, sentence_text_splitter),
            ".jpeg": FileProcessor(doc_int_parser, sentence_text_splitter),
            ".tiff": FileProcessor(doc_int_parser, sentence_text_splitter),
            ".bmp": FileProcessor(doc_int_parser, sentence_text_splitter),
            ".heic": FileProcessor(doc_int_parser, sentence_text_splitter),
            ".md": FileProcessor(TextParser(), sentence_text_splitter),
            ".txt": FileProcessor(TextParser(), sentence_text_splitter),
        }

    def read_file_from_storage(self, file_id: str) -> BytesIO:
        try:
            blob_client = self.storage_client.get_blob_client(
                container=current_app.config.get("STORAGE_CONTAINER"), blob=file_id)
            downloader = blob_client.download_blob(max_concurrency=1)
            file_content = downloader.readall()
            return BytesIO(file_content)
        except Exception as e:
            logger.error(f"ファイルを読み込む時にエラーが発生します。 {file_id}: {str(e)}")
            raise ServiceException("ファイルを読み込む時にエラーが発生します。", status_code=500)

    async def saveFiles(self, files: MultiDict[str, FileStorage], chat_id: str, chat_type: str, category: str, email: str) -> List[file_models.File]:
        files_res: List[file_models.File] = []
        try:
            async with get_db_session() as session:
                for index in files:
                    file: FileStorage = files[index]
                    file_id = str(uuid1())
                    file_name = file.filename
                    # content_type = file.content_type
                    file_content: bytes = file.read()
                    file_size_mb: float = len(file_content) / (1024 * 1024)

                    # save to storage
                    uploaded_blob: BlobClient = self.storage_container_client.upload_blob(
                        file_id,
                        file_content,
                        overwrite=True
                    )
                    file_url = uploaded_blob.url
                    # save to mysql
                    new_file_record = file_models.File(
                        id=file_id,
                        name=file_name,
                        chat_id=chat_id,
                        chat_type=chat_type,
                        file_url=file_url,
                        file_size_mb=file_size_mb,
                        category=category,
                        created_by=email,
                        updated_by=email
                    )
                    session.add(new_file_record)
                    await session.commit()
                    await session.refresh(new_file_record)
                    files_res.append(new_file_record)

            return files_res
        except Exception as e:
            logger.exception(
                f"ファイルをアップロードする際に、エラーが発生します。 {file_name}: {str(e)}")
            raise ServiceException("ファイルを読み込む時にエラーが発生します。", status_code=500)

    async def saveUrl(self, url: str, chat_id: str, email: str) -> file_models.File:
        try:
            async with get_db_session() as session:
                # save to mysql
                new_file_record = file_models.File(
                    id=str(uuid1()),
                    name=url,
                    chat_id=chat_id,
                    chat_type="gpt",
                    file_url=url,
                    file_size_mb=0,
                    category="gpt_url",
                    created_by=email,
                    updated_by=email
                )
                session.add(new_file_record)
                await session.commit()
                await session.refresh(new_file_record)
                return new_file_record
        except Exception as e:
            logger.exception(
                f"URL内容を保存する際に、エラーが発生します。 {url}: {str(e)}")
            raise ServiceException("URL内容を保存する際に、エラーが発生します。", status_code=500)

    async def parse_file(
        self,
        file: file_models.File,
        category: Optional[str] = None,
    ) -> List[Section]:
        key = os.path.splitext(file.name)[1]
        processor = self.file_processors.get(key)
        if processor is None:
            raise ServiceException(
                "ファイル形式またはファイル拡張子が正しくありません。", status_code=500)
        logger.info("Ingesting '%s'", file.name)
        file_content = self.read_file_from_storage(file.id)
        pages = [page async for page in processor.parser.parse(content=file_content)]
        logger.info("Splitting '%s' into sections", file.name)
        sections = [
            Section(split_page, content=file, category=category) for split_page in processor.splitter.split_pages(pages)
        ]
        return sections

    async def parse_url(self, file: file_models.File,):
        loader = WebBaseLoader(file.file_url)
        loader.requests_kwargs = {'verify': False}
        docs = loader.load()
        cleaned_data = re.sub(r'\n+', "\n", docs[0].page_content)
        cleaned_data = re.sub(r'\t+', '\t', cleaned_data)
        processor = self.file_processors.get(".txt")
        logger.info("Ingesting '%s'", file.name)
        pages = [page async for page in processor.parser.parse(content=BytesIO(cleaned_data.encode()))]
        logger.info("Splitting '%s' into sections", file.name)
        sections = [
            Section(split_page, content=file, category="") for split_page in processor.splitter.split_pages(pages)
        ]
        return sections

    async def deleteFile(self, file: file_models.File):
        try:
            if file.chat_type == "gpt" and file.category == "gpt_url":
                return
            blob_client = self.storage_container_client.get_blob_client(
                file.id)
            blob_client.delete_blob()
        except Exception as e:
            logger.exception(f"AzureStorageにファイルを削除する際に、エラーが発生します。: {str(e)}")
            raise ServiceException("ファイルを削除する際に、エラーが発生します。", status_code=500)

    @classmethod
    async def getFilesByChatId(self, chat_id) -> List[file_models.File]:
        files_res: List[file_models.File] = []
        try:
            async with get_db_session() as session:
                stmt = select(file_models.File).where(
                    file_models.File.chat_id == chat_id)
                result = await session.execute(stmt)
                files_res = result.scalars().all()
            return files_res
        except Exception as e:
            logger.exception(f"ファイルを取得する際に、エラーが発生します。: {str(e)}")
            raise ServiceException("ファイルを取得する際に、エラーが発生します。", status_code=500)

    @classmethod
    async def getFiles(self) -> List[file_models.File]:
        files_res: List[file_models.File] = []
        try:
            async with get_db_session() as session:
                stmt = select(file_models.File).where(
                    not_(and_(
                        file_models.File.chat_type == 'gpt',
                        file_models.File.category == 'gpt_url'
                    ))).order_by(desc(
                        file_models.File.created_at))
                result = await session.execute(stmt)
                files_res = result.scalars().all()
            return files_res
        except Exception as e:
            logger.exception(f"ファイルを取得する際に、エラーが発生します。: {str(e)}")
            raise ServiceException("ファイルを取得する際に、エラーが発生します。", status_code=500)

    @classmethod
    async def deleteDBFile(self, file_id: str) -> file_models.File:
        async with db_transaction() as session:
            file_stmt = select(file_models.File).where(
                file_models.File.id == file_id)
            file_result = await session.execute(file_stmt)
            file = file_result.scalars().first()
            await session.delete(file)
            return file

    @classmethod
    def sourcepage_from_file_page(cls, filename, page=0) -> str:
        if os.path.splitext(filename)[1].lower() == ".pdf":
            return f"{os.path.basename(filename)}#page={page+1}"
        else:
            return os.path.basename(filename)
