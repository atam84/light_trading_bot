# src/database/models/base.py

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Type, TypeVar, Generic
from bson import ObjectId
from pydantic import BaseModel, Field, validator
from motor.motor_asyncio import AsyncIOMotorDatabase, AsyncIOMotorCollection
from src.database.connection import get_database
from src.utils.logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T', bound='BaseDBModel')

class PyObjectId(ObjectId):
    """Custom ObjectId type for Pydantic"""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, v):
        if not ObjectId.is_valid(v):
            raise ValueError('Invalid ObjectId')
        return ObjectId(v)
    
    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(type='string')

class BaseDBModel(BaseModel, ABC):
    """Base model class for all database documents"""
    
    id: PyObjectId = Field(default_factory=PyObjectId, alias="_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None
    
    class Config:
        allow_population_by_field_name = True
        arbitrary_types_allowed = True
        json_encoders = {ObjectId: str}
        use_enum_values = True
    
    @property
    @abstractmethod
    def collection_name(self) -> str:
        """Return the MongoDB collection name"""
        pass
    
    def dict(self, **kwargs) -> Dict[str, Any]:
        """Convert to dictionary, excluding None values by default"""
        kwargs.setdefault('exclude_none', True)
        kwargs.setdefault('by_alias', True)
        return super().dict(**kwargs)
    
    def mongo_dict(self) -> Dict[str, Any]:
        """Convert to dictionary suitable for MongoDB insertion"""
        data = self.dict(by_alias=True, exclude={'id'})
        if hasattr(self, 'id') and self.id:
            data['_id'] = self.id
        return data
    
    @classmethod
    async def get_collection(cls) -> AsyncIOMotorCollection:
        """Get the MongoDB collection for this model"""
        db = await get_database()
        return db[cls.collection_name]

class BaseRepository(Generic[T]):
    """Base repository class for database operations"""
    
    def __init__(self, model_class: Type[T]):
        self.model_class = model_class
        self._collection = None
    
    async def get_collection(self) -> AsyncIOMotorCollection:
        """Get the MongoDB collection"""
        if not self._collection:
            self._collection = await self.model_class.get_collection()
        return self._collection
    
    async def create(self, data: Dict[str, Any] or T) -> T:
        """Create a new document"""
        try:
            collection = await self.get_collection()
            
            if isinstance(data, dict):
                # Add timestamps
                now = datetime.now(timezone.utc)
                data['created_at'] = now
                data['updated_at'] = now
                
                result = await collection.insert_one(data)
                data['_id'] = result.inserted_id
                return self.model_class(**data)
            else:
                # Handle model instance
                data.updated_at = datetime.now(timezone.utc)
                doc_data = data.mongo_dict()
                result = await collection.insert_one(doc_data)
                data.id = result.inserted_id
                return data
                
        except Exception as e:
            logger.error(f"Error creating {self.model_class.__name__}: {e}")
            raise
    
    async def get_by_id(self, doc_id: str or ObjectId) -> Optional[T]:
        """Get document by ID"""
        try:
            collection = await self.get_collection()
            if isinstance(doc_id, str):
                doc_id = ObjectId(doc_id)
            
            doc = await collection.find_one({"_id": doc_id})
            return self.model_class(**doc) if doc else None
            
        except Exception as e:
            logger.error(f"Error getting {self.model_class.__name__} by ID: {e}")
            return None
    
    async def get_one(self, filter_dict: Dict[str, Any]) -> Optional[T]:
        """Get one document by filter"""
        try:
            collection = await self.get_collection()
            doc = await collection.find_one(filter_dict)
            return self.model_class(**doc) if doc else None
            
        except Exception as e:
            logger.error(f"Error getting {self.model_class.__name__}: {e}")
            return None
    
    async def get_many(self, 
                      filter_dict: Dict[str, Any] = None,
                      skip: int = 0,
                      limit: int = 100,
                      sort: List[tuple] = None) -> List[T]:
        """Get multiple documents"""
        try:
            collection = await self.get_collection()
            filter_dict = filter_dict or {}
            
            cursor = collection.find(filter_dict)
            
            if sort:
                cursor = cursor.sort(sort)
            
            cursor = cursor.skip(skip).limit(limit)
            
            docs = await cursor.to_list(length=limit)
            return [self.model_class(**doc) for doc in docs]
            
        except Exception as e:
            logger.error(f"Error getting {self.model_class.__name__} list: {e}")
            return []
    
    async def update(self, doc_id: str or ObjectId, update_data: Dict[str, Any]) -> Optional[T]:
        """Update document by ID"""
        try:
            collection = await self.get_collection()
            if isinstance(doc_id, str):
                doc_id = ObjectId(doc_id)
            
            # Add updated timestamp
            update_data['updated_at'] = datetime.now(timezone.utc)
            
            result = await collection.find_one_and_update(
                {"_id": doc_id},
                {"$set": update_data},
                return_document=True
            )
            
            return self.model_class(**result) if result else None
            
        except Exception as e:
            logger.error(f"Error updating {self.model_class.__name__}: {e}")
            return None
    
    async def delete(self, doc_id: str or ObjectId) -> bool:
        """Delete document by ID"""
        try:
            collection = await self.get_collection()
            if isinstance(doc_id, str):
                doc_id = ObjectId(doc_id)
            
            result = await collection.delete_one({"_id": doc_id})
            return result.deleted_count > 0
            
        except Exception as e:
            logger.error(f"Error deleting {self.model_class.__name__}: {e}")
            return False
    
    async def count(self, filter_dict: Dict[str, Any] = None) -> int:
        """Count documents"""
        try:
            collection = await self.get_collection()
            filter_dict = filter_dict or {}
            return await collection.count_documents(filter_dict)
            
        except Exception as e:
            logger.error(f"Error counting {self.model_class.__name__}: {e}")
            return 0
    
    async def exists(self, filter_dict: Dict[str, Any]) -> bool:
        """Check if document exists"""
        count = await self.count(filter_dict)
        return count > 0

class TimestampMixin(BaseModel):
    """Mixin for timestamp fields"""
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None

class UserOwnershipMixin(BaseModel):
    """Mixin for user ownership"""
    user_id: PyObjectId = Field(..., description="Owner user ID")

class ActiveMixin(BaseModel):
    """Mixin for active/inactive status"""
    active: bool = Field(default=True, description="Whether the item is active")

class EncryptionMixin:
    """Mixin for encryption utilities"""
    
    @staticmethod
    def encrypt_value(value: str, key: str = None) -> str:
        """Encrypt a value using Fernet"""
        from cryptography.fernet import Fernet
        import os
        
        if not key:
            key = os.getenv('ENCRYPTION_KEY')
        
        if not key:
            raise ValueError("Encryption key not provided")
        
        cipher = Fernet(key.encode() if isinstance(key, str) else key)
        return cipher.encrypt(value.encode()).decode()
    
    @staticmethod
    def decrypt_value(encrypted_value: str, key: str = None) -> str:
        """Decrypt a value using Fernet"""
        from cryptography.fernet import Fernet
        import os
        
        if not key:
            key = os.getenv('ENCRYPTION_KEY')
        
        if not key:
            raise ValueError("Encryption key not provided")
        
        cipher = Fernet(key.encode() if isinstance(key, str) else key)
        return cipher.decrypt(encrypted_value.encode()).decode()