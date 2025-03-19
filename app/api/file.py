from quart import (Blueprint, send_file, jsonify, request, g)
from app.services.file_service import FileService
from app.services.searchai_service import SearchManager
from app.utils.decorators import token_required
from app.utils.log_utils import get_logger
from app.exceptions.service_exception import ServiceException


file_bp = Blueprint("file", __name__)
logger = get_logger("aoai_backend")


@file_bp.route("", methods=["POST"])
@token_required
async def saveFiles():
    try:
        request_data = await request.form
        request_files = await request.files
        email = g.get('email')
        chat_id = request_data["chat_id"]
        chat_type = request_data["chat_type"]
        category = request_data["category"]
        # ファイルが存在する時。
        if len(request_files) > 0:
            # save file to Mysql and Storage
            file_service = FileService()
            files = await file_service.saveFiles(request_files, chat_id,
                                                 chat_type, category, email)
            # save file to Azure Search AI
            search_manager = SearchManager()
            for file in files:
                sections = await file_service.parse_file(file, category)
                if sections:
                    await search_manager.update_content(sections)
        return "", 200
    except ServiceException as se:
        return jsonify({"message": str(se)}), se.status_code
    except Exception as e:
        logger.exception(f"ファイルを保存する際に、エラーが発生します。: {str(e)}")
        return jsonify({"message": "予想以外のエラーが発生します。"}), 500


@file_bp.route("", methods=["GET"])
@token_required
async def getFiles():
    try:
        db_file = await FileService.getFiles()
        res = [file.json for file in db_file]
        return res, 200
    except ServiceException as se:
        return jsonify({"message": str(se)}), se.status_code
    except Exception as e:
        logger.exception(f"ファイルを保存する際に、エラーが発生します。: {str(e)}")
        return jsonify({"message": "予想以外のエラーが発生します。"}), 500


@file_bp.route("<string:file_id>", methods=["DELETE"])
@token_required
async def deleteFile(file_id: str):
    try:
        file_service = FileService()
        search_manager = SearchManager()
        # delete file in DB
        file = await file_service.deleteDBFile(file_id)
        # delete file in storage
        await file_service.deleteFile(file)
        # delete search file in searchAI
        await search_manager.remove_content(file.id, file.chat_type)

        return "", 200
    except ServiceException as se:
        return jsonify({"message": str(se)}), se.status_code
    except Exception as e:
        logger.exception(f"APIチャット削除にエラーが発生します。: {e}")
        return jsonify({"message": "予想以外のエラーが発生します。"}), 500


@file_bp.route("<string:file_id>", methods=["GET"])
@token_required
async def getFile(file_id: str):
    try:
        file_name = request.args.get('file_name')
        file_service = FileService()
        file_content = file_service.read_file_from_storage(file_id)
        # Assuming the content type and filename are known or can be inferred
        return await send_file(
            file_content,
            # Set appropriate MIME type based on the file type
            mimetype='application/octet-stream',
            as_attachment=True,  # Forces download on the frontend
            # Sets the downloaded filename, customize if needed
            attachment_filename=f"{file_name}"
        )
    except ServiceException as se:
        return jsonify({"message": str(se)}), se.status_code
    except Exception as e:
        logger.exception(f"APIチャット削除にエラーが発生します。: {e}")
        return jsonify({"message": "予想以外のエラーが発生します。"}), 500
