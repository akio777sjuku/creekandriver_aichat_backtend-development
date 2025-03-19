from uuid import uuid1
from quart import current_app
from azure.cosmos import PartitionKey
from sqlalchemy import desc
from sqlalchemy.future import select
from app.extensions import get_cosmos_client
from app.database import get_db_session, db_transaction
from app.models import chat as chat_models, file as file_models
from app.constants import CHAT_CONTAINER
from app.utils.log_utils import get_logger
from app.exceptions.service_exception import ServiceException

logger = get_logger("aoai_backend")


class ChatService():
    def __init__(self):
        cosmos_db = get_cosmos_client().create_database_if_not_exists(
            id=current_app.config["COSMOSDB_DATABASE"])
        self.chat_cosmos = cosmos_db.create_container_if_not_exists(id=CHAT_CONTAINER,
                                                                    partition_key=PartitionKey(path="/type"))

    @classmethod
    async def saveChat(self, chat_type, openai_model, email):
        chat_id = str(uuid1())
        db_chat = chat_models.Chat(id=chat_id, type=chat_type, name="新規チャット",
                                   openai_model=openai_model, created_by=email, updated_by=email)
        try:
            async with get_db_session() as session:
                session.add(db_chat)
                await session.commit()
                await session.refresh(db_chat)
                return db_chat.json
        except Exception as e:
            logger.exception(f"新しいチャットをデータベースに挿入する際にエラーが発生します。: {e}")
            raise ServiceException("新規チャットする際にエラーが発生します。", status_code=500)

    @classmethod
    async def getAllChats(self, email):
        try:
            async with get_db_session() as session:
                stmt = select(chat_models.Chat).where(
                    chat_models.Chat.created_by == email).order_by(desc(
                        chat_models.Chat.updated_at))
                result = await session.execute(stmt)
                db_file = result.scalars().all()
                res = {"gpt": [], "retrieve": []}
                for chat in db_file:
                    if chat.type == "gpt":
                        res["gpt"].append(chat.json)
                    if chat.type == "retrieve":
                        res["retrieve"].append(chat.json)
                return res
        except Exception as e:
            logger.exception(f"チャットを取得する際にエラーが発生します。: {e}")
            raise ServiceException("チャットを取得する際にエラーが発生します。", status_code=500)

    @classmethod
    async def updateChat(self, chat_id, update_data: dict[str, any]):
        try:
            async with get_db_session() as session:
                stmt = select(chat_models.Chat).where(
                    chat_models.Chat.id == chat_id)
                result = await session.execute(stmt)
                chat = result.scalars().first()

                if not chat:
                    raise ServiceException("チャットを見つかりません。", status_code=404)

                for key, value in update_data.items():
                    if hasattr(chat, key):
                        setattr(chat, key, value)
                await session.commit()
                await session.refresh(chat)
                return chat.json
        except ServiceException:
            raise
        except Exception as e:
            logger.exception(f"チャットを更新する際にエラーが発生します。: {e}")
            raise ServiceException("チャット更新する際にエラーが発生します。", status_code=500)

    async def deleteChat(self, chat_id, chat_type):
        try:
            async with db_transaction() as session:
                stmt = select(chat_models.Chat).where(
                    chat_models.Chat.id == chat_id)
                result = await session.execute(stmt)
                chat = result.scalars().first()
                if chat:
                    file_stmt = select(file_models.File).where(
                        file_models.File.chat_id == chat_id)
                    file_result = await session.execute(file_stmt)
                    files = file_result.scalars().all()
                    for file in files:
                        await session.delete(file)
                    await session.delete(chat)
            # delete chat content
            results = await self.getChatContents(chat_id, chat_type)
            for item in list(results):
                self.chat_cosmos.delete_item(
                    item=item, partition_key=chat_type)
        except Exception as e:
            logger.exception(f"チャットを削除する際にエラーが発生します。: {e}")
            raise ServiceException("チャットを削除する際にエラーが発生します。", status_code=500)

    async def getChatContents(self, chat_id, chat_type):
        QUERY = "SELECT * FROM c WHERE c.type=@type AND c.chat_id=@chat_id ORDER BY c.index"
        try:

            params = [dict(name="@type", value=chat_type),
                    dict(name="@chat_id", value=chat_id)]
            results = self.chat_cosmos.query_items(
                query=QUERY, parameters=params, enable_cross_partition_query=True
            )
            items = [item for item in results]
            return items
        except Exception as e:
            logger.exception(f"チャット内容を取得する際にエラーが発生します。: {e}")
            raise ServiceException("チャット内容を取得する際にエラーが発生します。", status_code=500)
