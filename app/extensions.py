from quart import Quart, current_app
from azure.cosmos import CosmosClient
from openai import AsyncAzureOpenAI
from azure.storage.blob import BlobServiceClient, ContainerClient
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.aio import SearchIndexClient
from azure.core.credentials import AzureKeyCredential


def init_clients(app: Quart):

    # Initialize clients
    app.config['openai_client'] = initialize_openai_client(app)
    app.config['cosmos_client'] = initialize_cosmos_client(app)
    app.config['storage_client'] = initialize_storage_client(app)
    app.config['searchai_client'] = initialize_searchai_client(app)
    app.config['search_index_client'] = initialize_searchai_index_client(app)


def initialize_openai_client(app: Quart) -> AsyncAzureOpenAI:
    azure_openai_service = app.config.get("AZURE_OPENAI_SERVICE")
    if not azure_openai_service:
        raise ValueError(
            "AZURE_OPENAI_SERVICE is not set in the app configuration")

    openai_endpoint = f"https://{azure_openai_service}.openai.azure.com"
    openai_key = app.config.get("AZURE_OPENAI_KEY")
    if not openai_key:
        raise ValueError(
            "AZURE_OPENAI_KEY is not set in the app configuration")

    api_version = app.config.get(
        "AZURE_OPENAI_API_VERSION", "2024-05-01-preview")

    return AsyncAzureOpenAI(
        api_key=openai_key,
        api_version=api_version,
        azure_endpoint=openai_endpoint
    )


def initialize_cosmos_client(app: Quart) -> CosmosClient:
    cosmos_endpoint = app.config["COSMOSDB_ENDPOINT"]
    if not cosmos_endpoint:
        raise ValueError(
            "COSMOSDB_ENDPOINT is not set in the app configuration")

    cosmos_key = app.config["COSMOSDB_KEY"]
    if not cosmos_key:
        raise ValueError("COSMOSDB_KEY is not set in the app configuration")

    return CosmosClient(url=cosmos_endpoint, credential=cosmos_key)


def initialize_storage_client(app: Quart) -> BlobServiceClient:
    STORAGE_ACCOUNT = app.config.get("STORAGE_ACCOUNT")
    STORAGE_KEY = app.config.get("STORAGE_KEY")
    blob_service = BlobServiceClient(
        account_url=f"https://{STORAGE_ACCOUNT}.blob.core.windows.net", credential=STORAGE_KEY)
    return blob_service


def initialize_searchai_client(app: Quart) -> SearchClient:
    SEARCH_SERVICE = app.config.get("SEARCH_SERVICE")
    SEARCH_KEY = app.config.get("SEARCH_KEY")
    SEARCH_INDEX = app.config.get("SEARCH_INDEX")
    endpoint = f"https://{SEARCH_SERVICE}.search.windows.net/"
    return SearchClient(endpoint=endpoint,
                        index_name=SEARCH_INDEX, credential=AzureKeyCredential(SEARCH_KEY))


def initialize_searchai_index_client(app: Quart) -> SearchIndexClient:
    SEARCH_SERVICE = app.config.get("SEARCH_SERVICE")
    SEARCH_KEY = app.config.get("SEARCH_KEY")
    endpoint = f"https://{SEARCH_SERVICE}.search.windows.net/"
    return SearchIndexClient(endpoint=endpoint,
                             credential=AzureKeyCredential(SEARCH_KEY))


def get_openai_client() -> AsyncAzureOpenAI:
    client = current_app.config['openai_client']
    if client is None:
        raise RuntimeError('OpenAI Client has not been initialized.')
    return client


def get_cosmos_client() -> CosmosClient:
    client = current_app.config['cosmos_client']
    if client is None:
        raise RuntimeError('CosmosDB Client has not been initialized.')
    return client


def get_storage_client() -> BlobServiceClient:
    client = current_app.config['storage_client']
    if client is None:
        raise RuntimeError('Storage Client has not been initialized.')
    return client


def get_searchai_client() -> SearchClient:
    client = current_app.config['searchai_client']
    if client is None:
        raise RuntimeError('searchai Client has not been initialized.')
    return client


def get_searchai_index_client() -> SearchIndexClient:
    client = current_app.config['search_index_client']
    if client is None:
        raise RuntimeError('search index Client has not been initialized.')
    return client
