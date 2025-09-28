"""
Query Builder for OpenSearch

Builds complex search queries for BM25, vector, and hybrid search.
"""

from typing import Dict, Any, List, Optional


class QueryBuilder:
    """Builds OpenSearch queries for different search modes."""

    def __init__(self):
        """Initialize query builder."""
        pass

    def build_bm25_query(
        self,
        query: str,
        fields: Optional[List[str]] = None,
        field_boosts: Optional[Dict[str, float]] = None,
        top_k: int = 10,
        highlight: bool = True
    ) -> Dict[str, Any]:
        """Build BM25 keyword search query."""
        if not fields:
            fields = ["title", "abstract", "content", "authors"]
        if not field_boosts:
            field_boosts = {
                "title": 3.0,
                "abstract": 2.0,
                "content": 1.0,
                "authors": 1.5
            }

        # Build multi-match query with field boosts
        multi_match = {
            "multi_match": {
                "query": query,
                "fields": [f"{field}^{boost}" for field, boost in field_boosts.items()],
                "type": "best_fields",
                "tie_breaker": 0.3
            }
        }

        query_body = {
            "query": multi_match,
            "size": top_k
        }

        # Add highlighting
        if highlight:
            query_body["highlight"] = {
                "fields": {field: {} for field in fields},
                "pre_tags": ["<em>"],
                "post_tags": ["</em>"]
            }

        return query_body

    def build_vector_query(
        self,
        vector: List[float],
        vector_field: str = "embedding",
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build vector similarity search query."""
        query = {
            "query": {
                "knn": {
                    vector_field: {
                        "vector": vector,
                        "k": top_k
                    }
                }
            },
            "size": top_k
        }

        # Apply filters if provided
        if filters:
            query = self.apply_filters(query, filters)

        return query

    def build_hybrid_query(
        self,
        text_query: str,
        vector: List[float],
        text_weight: float = 0.7,
        vector_weight: float = 0.3,
        rrf_k: int = 60,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Build hybrid search query combining BM25 and vector search."""
        # For now, return a simplified hybrid query
        # In practice, this would combine BM25 and vector queries
        # The actual fusion happens in the service layer

        bm25_query = self.build_bm25_query(text_query, top_k=top_k * 2)
        vector_query = self.build_vector_query(vector, top_k=top_k * 2)

        # Return BM25 query as primary, vector fusion handled separately
        query = bm25_query

        # Apply filters if provided
        if filters:
            query = self.apply_filters(query, filters)

        return query

    def apply_filters(self, query: Dict[str, Any], filters: Dict[str, Any]) -> Dict[str, Any]:
        """Apply filters to an existing query."""
        if not filters:
            return query

        # Extract existing query
        existing_query = query.get("query", {})

        # Build filter conditions
        filter_conditions = []

        if "categories" in filters:
            categories = filters["categories"]
            if isinstance(categories, list):
                filter_conditions.append({"terms": {"categories": categories}})
            else:
                filter_conditions.append({"term": {"categories": categories}})

        if "date_from" in filters and "date_to" in filters:
            filter_conditions.append({
                "range": {
                    "published_date": {
                        "gte": filters["date_from"],
                        "lte": filters["date_to"]
                    }
                }
            })
        elif "date_from" in filters:
            filter_conditions.append({
                "range": {
                    "published_date": {
                        "gte": filters["date_from"]
                    }
                }
            })
        elif "date_to" in filters:
            filter_conditions.append({
                "range": {
                    "published_date": {
                        "lte": filters["date_to"]
                    }
                }
            })

        if "authors" in filters:
            authors = filters["authors"]
            if isinstance(authors, list):
                filter_conditions.append({"terms": {"authors": authors}})
            else:
                filter_conditions.append({"term": {"authors": authors}})

        # Combine with existing query
        if filter_conditions:
            if len(filter_conditions) == 1:
                combined_filter = filter_conditions[0]
            else:
                combined_filter = {"bool": {"must": filter_conditions}}

            if "bool" in existing_query:
                # Existing query already has bool structure
                existing_query["bool"]["filter"] = combined_filter
            else:
                # Wrap in bool query with filter
                query["query"] = {
                    "bool": {
                        "must": existing_query,
                        "filter": combined_filter
                    }
                }

        return query

    def build_suggestion_query(self, query: str, field: str = "title", size: int = 10) -> Dict[str, Any]:
        """Build completion suggester query."""
        return {
            "suggest": {
                f"{field}-suggest": {
                    "text": query,
                    "completion": {
                        "field": f"{field}",
                        "size": size,
                        "skip_duplicates": True
                    }
                }
            },
            "size": 0  # Don't return hits, only suggestions
        }