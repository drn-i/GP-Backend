from pymongo import MongoClient
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class MongoDBClient:
    _client = None
    _db = None

    @classmethod
    def get_db(cls):
        """Returns a shared MongoDB database instance."""
        if cls._client is None:
            try:
                # Initialize the connection
                cls._client = MongoClient(settings.MONGO_URI)
                cls._db = cls._client[settings.MONGO_DB_NAME]
                logger.info("Successfully connected to MongoDB.")
            except Exception as e:
                logger.error(f"CRITICAL: Failed to connect to MongoDB: {e}")
        return cls._db

# Export this function so your views can easily call get_mongo_db()
get_mongo_db = MongoDBClient.get_db