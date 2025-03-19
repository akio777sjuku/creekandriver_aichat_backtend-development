from quart import Quart, Blueprint
from app.api.auth import auth_bp
from app.api.chat import chat_bp
from app.api.answer import answer_bp
from app.api.file import file_bp
from app.api.recruitment import recruitment_bp


def config_blueprint(app: Quart):
    api_bp = Blueprint('api', __name__, url_prefix='/api')
    api_bp.register_blueprint(auth_bp, url_prefix="/auth")
    api_bp.register_blueprint(chat_bp, url_prefix="/chats")
    api_bp.register_blueprint(answer_bp, url_prefix="/answers")
    api_bp.register_blueprint(file_bp, url_prefix="/files")
    api_bp.register_blueprint(recruitment_bp, url_prefix="/recruitments")
    app.register_blueprint(api_bp)
