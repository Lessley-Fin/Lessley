import logging
import motor.motor_asyncio
from beanie import init_beanie

from config.settings import settings
from models.db.club import Club
from models.db.store import Store
from models.db.deal import Deal
from models.db.mcc import MccCode

logger = logging.getLogger(__name__)

client: motor.motor_asyncio.AsyncIOMotorClient | None = None


async def init_db():
    """
    Initializes the database connection and Beanie ODM.
    """
    global client
    logger.info("Initializing database connection...")
    try:
        client_kwargs = {}
        if settings.MONGO_USER and settings.MONGO_PASSWORD:
            client_kwargs["username"] = settings.MONGO_USER
            client_kwargs["password"] = settings.MONGO_PASSWORD
            if settings.MONGO_AUTH_SOURCE:
                client_kwargs["authSource"] = settings.MONGO_AUTH_SOURCE

        client = motor.motor_asyncio.AsyncIOMotorClient(
            settings.MONGO_CONNECTION_STRING,
            **client_kwargs
        )

        # Ping the server to check the connection
        await client.admin.command("ping")
        logger.info("Successfully connected to MongoDB.")

        await init_beanie(
            database=client.lessley, document_models=[Club, Store, Deal, MccCode]
        )
        logger.info("Beanie ODM initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB or initialize Beanie: {e}", exc_info=True)
        raise


async def close_db():
    """Closes the database connection."""
    global client
    if client:
        client.close()
        logger.info("MongoDB connection closed.")
