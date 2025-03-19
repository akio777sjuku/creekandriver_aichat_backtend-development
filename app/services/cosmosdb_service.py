from quart import current_app
from uuid import uuid1
from datetime import datetime
from azure.cosmos import PartitionKey
from app.models.chatinfo import ChatInfo
from app.models.chatcontent import ChatContent
from app.models.fileinfo import FileInfo, Attributes
from app.models.recruitment_bk import RecruitmentInfo, Recruitment
from app.constants import (DB_TYPE_CHAT, DB_TYPE_CONTENT, DB_TYPE_RECRUITMENT, DB_TYPE_USER_INFO,
                           DB_TYPE_LOGIN_HISTORY, DB_TYPE_FILE_INFO, DB_TYPE_FOLDER_INFO)
from app.extensions import get_cosmos_client

CONTAINER_CHAT_DATA = "chat-data"
CONTAINER_COMMON_DATA = "common-data"


class CosmosdbService():
    def __init__(self):
        database = get_cosmos_client().create_database_if_not_exists(
            id=current_app.config["COSMOSDB_DATABASE"])
        self.chat_data_container = database.create_container_if_not_exists(id=CONTAINER_CHAT_DATA,
                                                                           partition_key=PartitionKey(path="/type"))
        self.common_data_container = database.create_container_if_not_exists(id=CONTAINER_COMMON_DATA,
                                                                             partition_key=PartitionKey(path="/type"))

    # chat-data
    def create_chat(self, user_name, chat_name, chat_type):
        chat_info = ChatInfo(
            id=str(uuid1()), type=DB_TYPE_CHAT, chat_name=chat_name, chat_type=chat_type, openai_model="", created_user=user_name)
        self.chat_data_container.create_item(chat_info.json)
        return chat_info

    def add_chat_content(self, chat_id, index, chat_type, question, answer):
        if chat_type == "qa":
            chatContent = ChatContent(id=str(uuid1()), type=DB_TYPE_CONTENT, chat_id=chat_id, index=index, question=question,
                                      answer=answer["answer"], data_points=answer["data_points"], thoughts=answer["thoughts"])
        else:
            chatContent = ChatContent(id=str(uuid1()), type=DB_TYPE_CONTENT, chat_id=chat_id, index=index, question=question,
                                      answer=answer["answer"], data_points=[], thoughts="")

        self.chat_data_container.create_item(chatContent.json)
        return chatContent.id

    def delete_chat_and_content(self, chat_id):
        self.chat_data_container.delete_item(
            item=chat_id, partition_key=DB_TYPE_CHAT)
        results = self.get_chat_content(chat_id)
        for item in list(results):
            self.chat_data_container.delete_item(
                item=item, partition_key=DB_TYPE_CONTENT)

    def update_chat_name(self, chat_id, chat_name):
        item = self.chat_data_container.read_item(
            item=chat_id, partition_key=DB_TYPE_CHAT)
        item["chat_name"] = chat_name
        self.chat_data_container.replace_item(item=item, body=item)

    def update_chat(self, chat_id, chat_name, openai_model):
        item = self.chat_data_container.read_item(
            item=chat_id, partition_key=DB_TYPE_CHAT)
        item["chat_name"] = chat_name
        item["openai_model"] = openai_model
        self.chat_data_container.replace_item(item=item, body=item)

    def get_chat(self, chat_id):
        item = self.chat_data_container.read_item(
            item=chat_id, partition_key=DB_TYPE_CHAT)
        return item

    def get_chat_list(self, user_name, chat_type):
        QUERY = "SELECT * FROM c WHERE c.type=@type AND c.chat_type=@chat_type AND c.created_user=@user_name ORDER BY c.create_date DESC"
        params = [dict(name="@type", value=DB_TYPE_CHAT),
                  dict(name="@user_name", value=user_name),
                  dict(name="@chat_type", value=chat_type)]
        results = self.chat_data_container.query_items(
            query=QUERY, parameters=params, enable_cross_partition_query=True
        )
        items = [item for item in results]
        return items

    def get_chat_content(self, chat_id):
        QUERY = "SELECT * FROM c WHERE c.type=@type AND c.chat_id=@chat_id ORDER BY c.index"
        params = [dict(name="@type", value=DB_TYPE_CONTENT),
                  dict(name="@chat_id", value=chat_id)]
        results = self.chat_data_container.query_items(
            query=QUERY, parameters=params, enable_cross_partition_query=True
        )
        items = [item for item in results]
        return items

    # file-info
    def insert_file_info(self, file_data):
        attributes = Attributes(
            tag=file_data["tag"], source=file_data["source"], size=file_data["size"])
        file_info = FileInfo(id=file_data["file_id"],
                             type=DB_TYPE_FILE_INFO,
                             file_name=file_data["file_name"],
                             file_status="エンベディング処理中",
                             folder_id=file_data["folder_id"],
                             attributes=attributes,
                             created_user=file_data["created_user"],
                             created_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.common_data_container.create_item(file_info.json)

    def update_file_status(self, file_id, file_status):
        item = self.common_data_container.read_item(
            item=file_id, partition_key=DB_TYPE_FILE_INFO)
        item["file_status"] = file_status
        self.common_data_container.replace_item(item=item, body=item)

    def delete_file_info(self, id):
        self.common_data_container.delete_item(
            item=id, partition_key=DB_TYPE_FILE_INFO)

    def get_file_infos(self, file_name="", folder_id="", tag="", created_user=""):
        QUERY = "SELECT * FROM c WHERE c.type=@type "
        params = [dict(name="@type", value=DB_TYPE_FILE_INFO)]
        if len(file_name) != 0:
            QUERY += "AND c.file_name=@file_name "
            params.append(dict(name="@file_name", value=file_name))
        if len(folder_id) != 0:
            QUERY += "AND c.folder_id=@folder_id "
            params.append(dict(name="@folder_id", value=folder_id.strip()))
        if len(tag) != 0:
            QUERY += "AND c.attributes.tag=@tag "
            params.append(dict(name="@tag", value=tag))
        if len(created_user) != 0:
            QUERY += "AND c.created_user=@created_user "
            params.append(dict(name="@created_user", value=created_user))
        QUERY += " ORDER BY c.create_date DESC"

        results = self.common_data_container.query_items(
            query=QUERY, parameters=params, enable_cross_partition_query=True
        )
        items = [item for item in results]
        return items

    # login-history
    def insert_user_login_info(self, login_info_json):
        login_info_json["id"] = str(uuid1())
        login_info_json["type"] = DB_TYPE_LOGIN_HISTORY
        login_info_json["login_time"] = datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S")
        self.common_data_container.create_item(login_info_json)

    def get_user_login_info(self, user_id):
        QUERY = "SELECT * FROM c where c.type=@type ORDER BY c.login_time DESC"
        params = [dict(name="@type", value=DB_TYPE_LOGIN_HISTORY)]
        results = self.common_data_container.query_items(
            query=QUERY, parameters=params, enable_cross_partition_query=True
        )
        items = [item for item in results]
        return items

    # folder-info
    def insert_folder(self, folder_name, user_name):
        folder_id = str(uuid1())
        folder_info = {
            "id": folder_id,
            "type": DB_TYPE_FOLDER_INFO,
            "folder_name": folder_name,
            "created_user": user_name,
            "created_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.common_data_container.create_item(folder_info)
        return {"key": folder_id, "value": folder_name}

    def get_folders(self):
        QUERY = "SELECT * FROM c where c.type=@type ORDER BY c.created_date DESC"
        params = [dict(name="@type", value=DB_TYPE_FOLDER_INFO)]
        results = self.common_data_container.query_items(
            query=QUERY, parameters=params, enable_cross_partition_query=True
        )
        items = [{"key": item["id"], "value": item["folder_name"]}
                 for item in results]
        return items

    # user-info
    def get_user_info(self, user_id=""):
        if user_id == "":
            QUERY = "SELECT * FROM c where c.type=@type ORDER BY c.created_date DESC"
            params = [dict(name="@type", value=DB_TYPE_USER_INFO)]
        else:
            QUERY = "SELECT * FROM c where c.type=@type AND c.user_id=@user_id ORDER BY c.created_date DESC"
            params = [dict(name="@type", value=DB_TYPE_USER_INFO),
                      dict(name="@user_id", value=user_id)]
        results = self.common_data_container.query_items(
            query=QUERY, parameters=params, enable_cross_partition_query=True
        )
        items = [item for item in results]
        return items

    def create_user_info(self, data):
        user_info_id = str(uuid1())
        user_info = {
            "id": user_info_id,
            "type": DB_TYPE_USER_INFO,
            "user_id": data["user_id"],
            "authentication": {
                "admin": data["admin"],
                "openai_model": data["openai_model"],
                "file_upload": data["file_upload"]
            },
            "created_user": data["created_user"],
            "created_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.common_data_container.create_item(user_info)
        return user_info_id

    def delete_user_info(self, user_info_id):
        self.common_data_container.delete_item(
            item=user_info_id, partition_key=DB_TYPE_USER_INFO)

    def update_user_info(self, data):
        item = self.common_data_container.read_item(
            item=data["id"], partition_key=DB_TYPE_USER_INFO)
        item["authentication"] = {"admin": data["admin"],
                                  "openai_model": data["openai_model"],
                                  "file_upload": data["file_upload"]}
        self.common_data_container.replace_item(item=item, body=item)

    # recruitment
    def create_recruitment(self, recruitment: Recruitment, catch_copy: str, recruit_equirements: str, openai_model: str, created_user: str) -> RecruitmentInfo:
        recruitmentInfo = RecruitmentInfo(
            id=str(uuid1()), type=DB_TYPE_RECRUITMENT, recruitment=recruitment,
            catch_copy=catch_copy, recruit_equirements=recruit_equirements,
            openai_model=openai_model, created_user=created_user)
        self.chat_data_container.create_item(recruitmentInfo.json)
        return recruitmentInfo
