import os
from dotenv import load_dotenv

load_dotenv()


class Config():
    MAX_CONTENT_LENGTH = 100 * 1000 * 1000

    # secret key
    SECRET_KEY = os.getenv('SECRET_KEY')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')

    # mysql
    DATABASE_URI = os.getenv(
        'DATABASE_URL', 'mysql+aiomysql://user:password@localhost/aichat')

    # MSAL
    MSAL_TENANT_ID = os.getenv('MSAL_TENANT_ID')
    MSAL_CLIENT_ID = os.getenv('MSAL_CLIENT_ID')
    MSAL_AUTHORITY = os.getenv('MSAL_AUTHORITY')
    MSAL_REDIRECT_PATH = os.getenv('MSAL_REDIRECT_PATH')

    # Azure openAI
    AZURE_OPENAI_SERVICE = os.getenv("AZURE_OPENAI_SERVICE")
    AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION")
    AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
    OPENAI_MODEL = {
        "gpt-4o": os.getenv("AZURE_OPENAI_GPT4O"),
        "text-embedding-ada-002": os.getenv("AZURE_OPENAI_EMBEDING")
    }

    # CosmosDB
    COSMOSDB_ENDPOINT = os.getenv("AZURE_COSMOSDB_URI")
    COSMOSDB_KEY = os.getenv("AZURE_COSMOSDB_KEY")
    COSMOSDB_DATABASE = os.getenv("AZURE_COSMOSDB_DATABASE")

    # storage
    STORAGE_ACCOUNT = os.getenv("AZURE_STORAGE_ACCOUNT")
    STORAGE_CONTAINER = os.getenv("AZURE_STORAGE_CONTAINER")
    STORAGE_KEY = os.getenv("AZURE_STORAGE_KEY")

    # search ai
    SEARCH_SERVICE = os.getenv("AZURE_SEARCH_SERVICE")
    SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
    SEARCH_INDEX = os.getenv("AZURE_SEARCH_INDEX")

    # Document Intelligence
    DOCUMENTINTELLIGENCE_SERVICE = os.getenv(
        "AZURE_DOCUMENTINTELLIGENCE_SERVICE")
    DOCUMENTINTELLIGENCE_KEY = os.getenv("AZURE_DOCUMENTINTELLIGENCE_KEY")

    # Connon
    FRONTEND_DOMAIN = os.getenv("FRONTEND_DOMAIN")


# development
class DevelopmentConfig(Config):
    DEBUG = True
    HOST = "localhost"
    PORT = 50505


# staging
class StagingConfig(Config):
    DEBUG = True


# production
class ProductionConfig(Config):
    DEBUG = False
    TESTING = False


# config dict
config = {
    "development": DevelopmentConfig,
    "staging": StagingConfig,
    "production": ProductionConfig,
}
