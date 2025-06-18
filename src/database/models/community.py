# src/database/models/community.py

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from pydantic import Field, validator
from enum import Enum
import statistics
from src.database.models.base import (
    BaseDBModel, BaseRepository, TimestampMixin, 
    UserOwnershipMixin, PyObjectId
)

class StrategyCategory(str, Enum):
    """Strategy marketplace categories"""
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM = "momentum"
    SCALPING = "scalping"
    SWING_TRADING = "swing_trading"
    GRID_TRADING = "grid_trading"
    DCA = "dca"
    ARBITRAGE = "arbitrage"
    NEWS_BASED = "news_based"
    TECHNICAL_ANALYSIS = "technical_analysis"
    FUNDAMENTAL_ANALYSIS = "fundamental_analysis"
    EXPERIMENTAL = "experimental"

class StrategyComplexity(str, Enum):
    """Strategy complexity levels"""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"

class MarketplaceStatus(str, Enum):
    """Marketplace item status"""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SUSPENDED = "suspended"
    DEPRECATED = "deprecated"

class StrategyMarketplace(BaseDBModel, TimestampMixin, UserOwnershipMixin):
    """Strategy marketplace listings"""
    
    # Strategy reference
    strategy_id: PyObjectId = Field(..., description="Original strategy ID")
    strategy_config: Dict[str, Any] = Field(..., description="Strategy configuration")
    
    # Marketplace listing details
    title: str = Field(..., min_length=5, max_length=200, description="Strategy title")
    description: str = Field(..., min_length=50, max_length=2000, description="Detailed description")
    short_description: str = Field(..., max_length=300, description="Short description for listings")
    
    # Categorization
    category: StrategyCategory = Field(..., description="Strategy category")
    complexity: StrategyComplexity = Field(..., description="Complexity level")
    tags: List[str] = Field(default=[], description="Strategy tags")
    
    # Performance metrics (from backtesting)
    performance_stats: Dict[str, float] = Field(default={}, description="Performance statistics")
    verified_performance: bool = Field(default=False, description="Performance verified by system")
    
    # Pricing
    price: float = Field(default=0.0, ge=0, description="Strategy price (0 for free)")
    currency: str = Field(default="USD", description="Price currency")
    
    # Marketplace metrics
    rating: float = Field(default=0.0, ge=0, le=5, description="Average rating")
    rating_count: int = Field(default=0, description="Number of ratings")
    downloads: int = Field(default=0, description="Download count")
    views: int = Field(default=0, description="View count")
    favorites: int = Field(default=0, description="Favorite count")
    
    # Status and moderation
    status: MarketplaceStatus = Field(default=MarketplaceStatus.DRAFT, description="Listing status")
    featured: bool = Field(default=False, description="Featured strategy")
    verified_author: bool = Field(default=False, description="Author verification status")
    
    # Requirements and compatibility
    min_balance: Optional[float] = Field(None, description="Minimum recommended balance")
    supported_exchanges: List[str] = Field(default=[], description="Supported exchanges")
    supported_timeframes: List[str] = Field(default=[], description="Supported timeframes")
    supported_symbols: List[str] = Field(default=[], description="Recommended symbols")
    
    # Content
    documentation: Optional[str] = Field(None, description="Strategy documentation")
    changelog: List[Dict[str, Any]] = Field(default=[], description="Version changelog")
    screenshots: List[str] = Field(default=[], description="Screenshot URLs")
    
    # Version control
    version: str = Field(default="1.0.0", description="Strategy version")
    last_updated: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Moderation
    moderator_notes: Optional[str] = Field(None, description="Moderator review notes")
    rejection_reason: Optional[str] = Field(None, description="Rejection reason")
    
    @property
    def collection_name(self) -> str:
        return "strategy_marketplace"
    
    @validator('title')
    def validate_title(cls, v):
        return v.strip()
    
    @validator('tags')
    def validate_tags(cls, v):
        # Normalize tags
        return [tag.lower().strip() for tag in v if tag.strip()]
    
    @validator('supported_exchanges')
    def validate_exchanges(cls, v):
        return [exchange.lower() for exchange in v]
    
    def update_rating(self, new_rating: float):
        """Update average rating with new rating"""
        total_rating = self.rating * self.rating_count
        self.rating_count += 1
        self.rating = (total_rating + new_rating) / self.rating_count
    
    def increment_download(self):
        """Increment download count"""
        self.downloads += 1
    
    def increment_view(self):
        """Increment view count"""
        self.views += 1
    
    def get_conversion_rate(self) -> float:
        """Calculate download to view conversion rate"""
        if self.views == 0:
            return 0.0
        return (self.downloads / self.views) * 100
    
    def is_approved(self) -> bool:
        """Check if strategy is approved for marketplace"""
        return self.status == MarketplaceStatus.APPROVED
    
    def can_download(self) -> bool:
        """Check if strategy can be downloaded"""
        return self.status == MarketplaceStatus.APPROVED
    
    def to_listing_dict(self) -> Dict[str, Any]:
        """Convert to marketplace listing format"""
        return {
            "id": str(self.id),
            "title": self.title,
            "short_description": self.short_description,
            "category": self.category,
            "complexity": self.complexity,
            "tags": self.tags,
            "price": self.price,
            "currency": self.currency,
            "rating": round(self.rating, 2),
            "rating_count": self.rating_count,
            "downloads": self.downloads,
            "views": self.views,
            "featured": self.featured,
            "verified_author": self.verified_author,
            "version": self.version,
            "last_updated": self.last_updated,
            "created_at": self.created_at,
            "conversion_rate": self.get_conversion_rate(),
            "performance_stats": self.performance_stats,
            "min_balance": self.min_balance,
            "supported_exchanges": self.supported_exchanges
        }

class StrategyRating(BaseDBModel, TimestampMixin, UserOwnershipMixin):
    """Strategy ratings and reviews"""
    
    strategy_marketplace_id: PyObjectId = Field(..., description="Marketplace strategy ID")
    strategy_author_id: PyObjectId = Field(..., description="Strategy author ID")
    
    # Rating details
    rating: int = Field(..., ge=1, le=5, description="Rating (1-5 stars)")
    review: Optional[str] = Field(None, max_length=2000, description="Written review")
    
    # Detailed ratings
    performance_rating: Optional[int] = Field(None, ge=1, le=5, description="Performance rating")
    ease_of_use_rating: Optional[int] = Field(None, ge=1, le=5, description="Ease of use rating")
    documentation_rating: Optional[int] = Field(None, ge=1, le=5, description="Documentation rating")
    support_rating: Optional[int] = Field(None, ge=1, le=5, description="Support rating")
    
    # Purchase verification
    verified_purchase: bool = Field(default=False, description="Verified purchase/download")
    used_strategy: bool = Field(default=False, description="Actually used the strategy")
    usage_duration_days: Optional[int] = Field(None, description="How long strategy was used")
    
    # Helpful votes
    helpful_votes: int = Field(default=0, description="Helpful votes from other users")
    total_votes: int = Field(default=0, description="Total votes received")
    
    # Moderation
    flagged: bool = Field(default=False, description="Flagged for review")
    approved: bool = Field(default=True, description="Review approved status")
    moderator_notes: Optional[str] = Field(None, description="Moderator notes")
    
    @property
    def collection_name(self) -> str:
        return "strategy_ratings"
    
    def get_helpfulness_score(self) -> float:
        """Calculate helpfulness score percentage"""
        if self.total_votes == 0:
            return 0.0
        return (self.helpful_votes / self.total_votes) * 100
    
    def add_helpful_vote(self, helpful: bool = True):
        """Add a helpful vote"""
        self.total_votes += 1
        if helpful:
            self.helpful_votes += 1
    
    def get_overall_rating(self) -> float:
        """Calculate overall rating from detailed ratings"""
        ratings = []
        for field in [self.performance_rating, self.ease_of_use_rating, 
                     self.documentation_rating, self.support_rating]:
            if field is not None:
                ratings.append(field)
        
        if not ratings:
            return self.rating
        
        return statistics.mean(ratings)

class UserFollow(BaseDBModel, TimestampMixin, UserOwnershipMixin):
    """User following relationships"""
    
    following_user_id: PyObjectId = Field(..., description="User being followed")
    
    # Follow details
    follow_type: str = Field(default="user", description="Follow type: user, strategy_author")
    notifications_enabled: bool = Field(default=True, description="Receive notifications")
    
    @property
    def collection_name(self) -> str:
        return "user_follows"

class StrategyFavorite(BaseDBModel, TimestampMixin, UserOwnershipMixin):
    """User strategy favorites"""
    
    strategy_marketplace_id: PyObjectId = Field(..., description="Marketplace strategy ID")
    
    # Favorite details
    notes: Optional[str] = Field(None, max_length=500, description="Personal notes")
    tags: List[str] = Field(default=[], description="Personal tags")
    
    @property
    def collection_name(self) -> str:
        return "strategy_favorites"

class StrategyDownload(BaseDBModel, TimestampMixin, UserOwnershipMixin):
    """Strategy download tracking"""
    
    strategy_marketplace_id: PyObjectId = Field(..., description="Marketplace strategy ID")
    strategy_author_id: PyObjectId = Field(..., description="Strategy author ID")
    
    # Download details
    download_type: str = Field(default="free", description="free, paid, trial")
    price_paid: float = Field(default=0.0, description="Price paid for strategy")
    transaction_id: Optional[str] = Field(None, description="Payment transaction ID")
    
    # Usage tracking
    imported_to_account: bool = Field(default=False, description="Imported to user account")
    first_used: Optional[datetime] = Field(None, description="First time strategy was used")
    last_used: Optional[datetime] = Field(None, description="Last time strategy was used")
    usage_count: int = Field(default=0, description="Number of times used")
    
    @property
    def collection_name(self) -> str:
        return "strategy_downloads"
    
    def mark_as_used(self):
        """Mark strategy as used"""
        now = datetime.now(timezone.utc)
        if not self.first_used:
            self.first_used = now
        self.last_used = now
        self.usage_count += 1

class StrategyMarketplaceRepository(BaseRepository[StrategyMarketplace]):
    """Repository for StrategyMarketplace operations"""
    
    def __init__(self):
        super().__init__(StrategyMarketplace)
    
    async def get_approved_strategies(self, category: StrategyCategory = None,
                                    complexity: StrategyComplexity = None,
                                    tags: List[str] = None,
                                    min_rating: float = 0.0,
                                    skip: int = 0, limit: int = 20) -> List[StrategyMarketplace]:
        """Get approved marketplace strategies"""
        filter_dict = {"status": MarketplaceStatus.APPROVED}
        
        if category:
            filter_dict["category"] = category
        
        if complexity:
            filter_dict["complexity"] = complexity
        
        if tags:
            filter_dict["tags"] = {"$in": tags}
        
        if min_rating > 0:
            filter_dict["rating"] = {"$gte": min_rating}
        
        return await self.get_many(
            filter_dict=filter_dict,
            skip=skip,
            limit=limit,
            sort=[("featured", -1), ("rating", -1), ("downloads", -1)]
        )
    
    async def get_featured_strategies(self, limit: int = 10) -> List[StrategyMarketplace]:
        """Get featured strategies"""
        return await self.get_many(
            filter_dict={"status": MarketplaceStatus.APPROVED, "featured": True},
            limit=limit,
            sort=[("rating", -1), ("downloads", -1)]
        )
    
    async def get_user_strategies(self, user_id: str, status: MarketplaceStatus = None) -> List[StrategyMarketplace]:
        """Get user's marketplace strategies"""
        filter_dict = {"user_id": PyObjectId(user_id)}
        if status:
            filter_dict["status"] = status
        
        return await self.get_many(filter_dict, sort=[("created_at", -1)])
    
    async def publish_strategy(self, user_id: str, strategy_id: str, title: str,
                             description: str, category: StrategyCategory,
                             strategy_config: Dict[str, Any], **kwargs) -> StrategyMarketplace:
        """Publish strategy to marketplace"""
        marketplace_data = {
            "user_id": PyObjectId(user_id),
            "strategy_id": PyObjectId(strategy_id),
            "title": title,
            "description": description,
            "category": category,
            "strategy_config": strategy_config,
            "status": MarketplaceStatus.PENDING_REVIEW,
            **kwargs
        }
        
        return await self.create(marketplace_data)
    
    async def update_rating(self, strategy_id: str, new_rating: float) -> Optional[StrategyMarketplace]:
        """Update strategy rating"""
        strategy = await self.get_by_id(strategy_id)
        if not strategy:
            return None
        
        # Calculate new average rating
        total_rating = strategy.rating * strategy.rating_count
        new_rating_count = strategy.rating_count + 1
        new_avg_rating = (total_rating + new_rating) / new_rating_count
        
        update_data = {
            "rating": new_avg_rating,
            "rating_count": new_rating_count
        }
        
        return await self.update(strategy_id, update_data)
    
    async def increment_downloads(self, strategy_id: str) -> bool:
        """Increment download count"""
        strategy = await self.get_by_id(strategy_id)
        if not strategy:
            return False
        
        result = await self.update(strategy_id, {"downloads": strategy.downloads + 1})
        return result is not None
    
    async def increment_views(self, strategy_id: str) -> bool:
        """Increment view count"""
        strategy = await self.get_by_id(strategy_id)
        if not strategy:
            return False
        
        result = await self.update(strategy_id, {"views": strategy.views + 1})
        return result is not None
    
    async def search_strategies(self, query: str, skip: int = 0, limit: int = 20) -> List[StrategyMarketplace]:
        """Search strategies in marketplace"""
        filter_dict = {
            "status": MarketplaceStatus.APPROVED,
            "$or": [
                {"title": {"$regex": query, "$options": "i"}},
                {"description": {"$regex": query, "$options": "i"}},
                {"tags": {"$regex": query, "$options": "i"}}
            ]
        }
        
        return await self.get_many(filter_dict, skip=skip, limit=limit, sort=[("rating", -1)])
    
    async def get_marketplace_statistics(self) -> Dict[str, Any]:
        """Get marketplace statistics"""
        collection = await self.get_collection()
        
        # Total strategies by status
        status_pipeline = [
            {"$group": {"_id": "$status", "count": {"$sum": 1}}}
        ]
        status_counts = {doc["_id"]: doc["count"] 
                        for doc in await collection.aggregate(status_pipeline).to_list(length=10)}
        
        # Category distribution
        category_pipeline = [
            {"$match": {"status": "approved"}},
            {"$group": {"_id": "$category", "count": {"$sum": 1}}}
        ]
        category_counts = {doc["_id"]: doc["count"] 
                          for doc in await collection.aggregate(category_pipeline).to_list(length=20)}
        
        # Top strategies
        top_strategies = await self.get_many(
            filter_dict={"status": MarketplaceStatus.APPROVED},
            limit=5,
            sort=[("downloads", -1)]
        )
        
        return {
            "total_strategies": sum(status_counts.values()),
            "approved_strategies": status_counts.get("approved", 0),
            "pending_review": status_counts.get("pending_review", 0),
            "category_distribution": category_counts,
            "top_strategies": [s.to_listing_dict() for s in top_strategies],
            "total_downloads": sum(s.downloads for s in top_strategies)
        }

class StrategyRatingRepository(BaseRepository[StrategyRating]):
    """Repository for StrategyRating operations"""
    
    def __init__(self):
        super().__init__(StrategyRating)
    
    async def get_strategy_ratings(self, strategy_marketplace_id: str,
                                 skip: int = 0, limit: int = 20) -> List[StrategyRating]:
        """Get ratings for strategy"""
        return await self.get_many(
            filter_dict={
                "strategy_marketplace_id": PyObjectId(strategy_marketplace_id),
                "approved": True
            },
            skip=skip,
            limit=limit,
            sort=[("helpful_votes", -1), ("created_at", -1)]
        )
    
    async def get_user_rating(self, user_id: str, strategy_marketplace_id: str) -> Optional[StrategyRating]:
        """Get user's rating for strategy"""
        return await self.get_one({
            "user_id": PyObjectId(user_id),
            "strategy_marketplace_id": PyObjectId(strategy_marketplace_id)
        })
    
    async def create_rating(self, user_id: str, strategy_marketplace_id: str,
                          strategy_author_id: str, rating: int, review: str = None,
                          **kwargs) -> StrategyRating:
        """Create strategy rating"""
        # Check if user already rated this strategy
        existing = await self.get_user_rating(user_id, strategy_marketplace_id)
        if existing:
            raise ValueError("User already rated this strategy")
        
        rating_data = {
            "user_id": PyObjectId(user_id),
            "strategy_marketplace_id": PyObjectId(strategy_marketplace_id),
            "strategy_author_id": PyObjectId(strategy_author_id),
            "rating": rating,
            "review": review,
            **kwargs
        }
        
        return await self.create(rating_data)
    
    async def add_helpful_vote(self, rating_id: str, helpful: bool = True) -> bool:
        """Add helpful vote to rating"""
        rating = await self.get_by_id(rating_id)
        if not rating:
            return False
        
        update_data = {
            "total_votes": rating.total_votes + 1
        }
        
        if helpful:
            update_data["helpful_votes"] = rating.helpful_votes + 1
        
        result = await self.update(rating_id, update_data)
        return result is not None

# Repository instances
strategy_marketplace_repository = StrategyMarketplaceRepository()
strategy_rating_repository = StrategyRatingRepository()