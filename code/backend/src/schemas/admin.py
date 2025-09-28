"""
Admin schemas
"""
from pydantic import BaseModel
from typing import Dict, Any


class SystemStats(BaseModel):
    """System statistics"""
    total_users: int
    total_papers: int
    total_searches: int
    cache_hit_rate: float
    average_response_time: float
    system_uptime: float


class UserStats(BaseModel):
    """User statistics"""
    active_users: int
    new_users_today: int
    top_search_queries: Dict[str, int]
    user_activity_trends: Dict[str, Any]


class SearchStats(BaseModel):
    """Search statistics"""
    total_queries: int
    average_query_time: float
    popular_categories: Dict[str, int]
    search_success_rate: float
    index_size: int