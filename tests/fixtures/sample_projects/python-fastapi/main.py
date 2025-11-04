from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from azure.cosmos import CosmosClient
from azure.servicebus import ServiceBusClient
from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
import os

app = FastAPI(title="Python FastAPI", version="1.0.0")

# Configuration from environment
COSMOS_ENDPOINT = os.getenv("COSMOS_ENDPOINT")
COSMOS_KEY = os.getenv("COSMOS_KEY")
COSMOS_DATABASE = os.getenv("COSMOS_DATABASE", "products-db")
SERVICEBUS_NAMESPACE = os.getenv("SERVICEBUS_NAMESPACE")
KEYVAULT_URL = os.getenv("KEYVAULT_URL")

# Initialize clients
credential = DefaultAzureCredential()
cosmos_client = CosmosClient(COSMOS_ENDPOINT, COSMOS_KEY)
database = cosmos_client.get_database_client(COSMOS_DATABASE)
container = database.get_container_client("products")

servicebus_client = ServiceBusClient(
    f"{SERVICEBUS_NAMESPACE}.servicebus.windows.net",
    credential
)

keyvault_client = SecretClient(vault_url=KEYVAULT_URL, credential=credential)


class Product(BaseModel):
    id: str
    name: str
    price: float
    category: str


@app.get("/")
def read_root():
    return {"message": "Welcome to Python FastAPI", "status": "healthy"}


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "services": {
            "cosmos": "connected",
            "servicebus": "connected",
            "keyvault": "connected"
        }
    }


@app.get("/api/products")
async def get_products():
    """Get all products from Cosmos DB"""
    try:
        items = list(container.query_items(
            query="SELECT * FROM c",
            enable_cross_partition_query=True
        ))
        return {"products": items, "count": len(items)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/products")
async def create_product(product: Product):
    """Create a new product in Cosmos DB"""
    try:
        container.upsert_item(product.dict())
        
        # Send message to Service Bus
        sender = servicebus_client.get_queue_sender(queue_name="product-events")
        message = {
            "event": "product_created",
            "product_id": product.id,
            "product_name": product.name
        }
        sender.send_messages(message)
        sender.close()
        
        return {"message": "Product created", "product": product}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/secrets/{secret_name}")
async def get_secret(secret_name: str):
    """Get a secret from Key Vault"""
    try:
        secret = keyvault_client.get_secret(secret_name)
        return {"secret_name": secret_name, "secret_value": secret.value}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
