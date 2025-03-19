from quart import (Blueprint, jsonify, request, g)
from app.services.chat_service import ChatService
from app.services.searchai_service import SearchManager
from app.services.file_service import FileService
from app.utils.decorators import token_required
from app.utils.log_utils import get_logger
from app.exceptions.service_exception import ServiceException


chat_bp = Blueprint("chat", __name__)
logger = get_logger("aoai_backend")


@chat_bp.route("", methods=["POST"])
@token_required
async def createChat():
    if not request.is_json:
        return jsonify({"message": "リクエストはJSON形式でなければなりません。"}), 415
    try:
        request_json = await request.get_json()
        email = g.get('email')

        chat_type = request_json["chat_type"]
        openai_model = request_json["openai_model"]
        if (not chat_type or not openai_model):
            return jsonify({"message": "パラメーターが間違っています。"}), 409
        res = await ChatService.saveChat(chat_type, openai_model, email)
        return res, 200
    except ServiceException as se:
        return jsonify({"message": str(se)}), se.status_code
    except Exception as e:
        logger.exception(f"APIチャット作成にエラーが発生します。: {e}")
        return jsonify({"message": "予想以外のエラーが発生します。"}), 500


@chat_bp.route("", methods=["GET"])
@token_required
async def getAllChats():
    try:
        email = g.get('email')
        res = await ChatService.getAllChats(email)
        return res, 200
    except ServiceException as se:
        return jsonify({"message": str(se)}), se.status_code
    except Exception as e:
        logger.exception(f"APIチャット取得にエラーが発生します。: {e}")
        return jsonify({"message": "予想以外のエラーが発生します。"}), 500


@chat_bp.route("<string:chat_id>", methods=["PUT"])
@token_required
async def updateChat(chat_id: str):
    if not request.is_json:
        return jsonify({"message": "リクエストはJSON形式でなければなりません。"}), 415
    request_json = await request.get_json()
    try:
        email = g.get('email')
        request_json["updated_by"] = email
        chat = await ChatService.updateChat(chat_id, request_json)
        return chat, 200
    except ServiceException as se:
        return jsonify({"message": str(se)}), se.status_code
    except Exception as e:
        logger.exception(f"APIチャット更新にエラーが発生します。: {e}")
        return jsonify({"message": "予想以外のエラーが発生します。"}), 500


@chat_bp.route("<string:chat_id>", methods=["DELETE"])
@token_required
async def deleteChat(chat_id: str):
    try:
        chat_type = request.args.get('chat_type')
        file_service = FileService()
        chat_service = ChatService()
        search_manager = SearchManager()
        files = await file_service.getFilesByChatId(chat_id)
        if len(files) > 0:
            for file in files:
                # delete file in storage
                await file_service.deleteFile(file)
                # delete search file in searchAI
                await search_manager.remove_content(file.id, chat_type)

        # delete chat and file data in DB delete chat content data in cosmosDB
        await chat_service.deleteChat(chat_id, chat_type)
        return "", 200
    except ServiceException as se:
        return jsonify({"message": str(se)}), se.status_code
    except Exception as e:
        logger.exception(f"APIチャット削除にエラーが発生します。: {e}")
        return jsonify({"message": "予想以外のエラーが発生します。"}), 500


@chat_bp.route("content/<string:chat_id>", methods=["GET"])
@token_required
async def getChatContents(chat_id: str):
    try:
        chat_service = ChatService()
        chat_type = request.args.get('chat_type')
        res = await chat_service.getChatContents(chat_id, chat_type)
        return jsonify(res), 200
    except ServiceException as se:
        return jsonify({"message": str(se)}), se.status_code
    except Exception as e:
        logger.exception(f"APIチャット内容取得にエラーが発生します。: {e}")
        return jsonify({"message": "予想以外のエラーが発生します。"}), 500
