from datetime import datetime
from quart import (Blueprint, current_app, jsonify, g)
from sqlalchemy.future import select
from sqlalchemy import desc

from app.utils.decorators import token_required
from app.models import loginhistory as loginhistory_models
from app.database import get_db_session
from app.utils.log_utils import get_logger

auth_bp = Blueprint("auth", __name__)
logger = get_logger("aoai_backend")


@auth_bp.route("/setup", methods=["GET"])
async def setup():
    res = {
        "auth": {
            "clientId": current_app.config.get("MSAL_CLIENT_ID"),
            "authority": current_app.config.get("MSAL_AUTHORITY"),
            "redirectUri": current_app.config.get("MSAL_REDIRECT_PATH"),
            "postLogoutRedirectUri": "/",
            "navigateToLoginRequestUrl": False,
        },
        "cache": {
            "cacheLocation": "sessionStorage",
            "storeAuthStateInCookie": False,
        },
        # "loginRequest": {
        #     "scopes": [".default"],
        # },
        # "tokenRequest": {
        #     "scopes": [f"api://{current_app.config.get("MSAL_CLIENT_ID")}/backend"],
        # },
    }
    return jsonify(res), 200


@auth_bp.route("/history", methods=["POST"])
@token_required
async def saveLoginHistory():
    try:
        user_name = g.get('username')
        email = g.get('email')
        async with get_db_session() as session:
            history = loginhistory_models.LoginHistory(
                user_id=email, user_name=user_name,
                login_time=datetime.now(), created_by=email, updated_by=email)
            session.add(history)
            await session.commit()
        return "", 200
    except Exception as e:
        logger.exception(f"ログイン履歴登録する際ににエラーが発生します。: {e}")
        return jsonify({"message": "予想以外のエラーが発生します。"}), 500


@auth_bp.route("/history", methods=["GET"])
@token_required
async def getLoginHistory():
    try:
        async with get_db_session() as session:
            stmt = select(loginhistory_models.LoginHistory).order_by(desc(
                loginhistory_models.LoginHistory.created_at))
            result = await session.execute(stmt)
            history_res = result.scalars().all()
            res = [history.json for history in history_res]

        return res
    except Exception as e:
        logger.exception(f"ログイン履歴登録する際ににエラーが発生します。: {e}")
        return jsonify({"message": "予想以外のエラーが発生します。"}), 500
