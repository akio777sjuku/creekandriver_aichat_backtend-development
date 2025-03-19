import os
from quart import Quart
from quart_cors import cors
from app.api import config_blueprint
from app.config import config
from app.extensions import init_clients
from app.database import init_db, create_tables
from dotenv import load_dotenv

load_dotenv()


def create_app():
    config_name = os.getenv("ENVIRONMENT", "development")

    app = Quart(__name__)

    # config setting
    app.config.from_object(config.get(config_name))

    # CORS setting
    app = cors(app, allow_origin=app.config["FRONTEND_DOMAIN"])

    # extension setting
    init_clients(app)

    @app.before_serving
    async def startup():
        await init_db(app)
        await create_tables(app)

    # blueprint setting
    config_blueprint(app)

    return app
