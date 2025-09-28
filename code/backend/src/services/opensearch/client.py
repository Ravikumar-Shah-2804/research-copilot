"""
OpenSearch client for hybrid search with BM25 + embeddings
"""
import logging
from typing import Any, Dict, List, Optional, Tuple
from opensearchpy import OpenSearch
from opensearchpy.exceptions import NotFoundError
from opensearchpy.helpers import bulk

from ...config import settings
from ..circuit_breaker import circuit_breaker, CircuitBreakerConfig
from ...utils.retry import search_retry

logger = logging.getLogger(__name__)

# Circuit breaker config for OpenSearch
opensearch_circuit_config = CircuitBreakerConfig(
    failure_threshold=3,
    recovery_timeout=30.0,
    expected_exception=(Exception,),
    timeout=5.0
)


class OpenSearchService:
    """OpenSearch service for hybrid search"""

    def __init__(self, provider: str = "openrouter"):
        self.client: Optional[OpenSearch] = None
        self.host = settings.opensearch_host
        self.port = settings.opensearch_port
        self.url = settings.opensearch_url
        self.provider = provider
        from .index_config import get_index_name
        self.index_name = get_index_name(provider)

    @circuit_breaker("opensearch_connect", opensearch_circuit_config)
    async def connect(self):
        """Connect to OpenSearch"""
        try:
            self.client = OpenSearch(
                hosts=[{"host": self.host, "port": self.port}],
                http_compress=True,
                use_ssl=False,
                verify_certs=False,
                ssl_show_warn=False,
            )
            # Test connection
            info = self.client.info()
            logger.info(f"Connected to OpenSearch: {info['version']['number']}")
        except Exception as e:
            logger.error(f"Failed to connect to OpenSearch: {e}")
            raise

    def create_index(self, mapping: Optional[Dict[str, Any]] = None, settings: Optional[Dict[str, Any]] = None):
        """Create index with mapping and settings"""
        try:
            if not self.client:
                raise Exception("OpenSearch client not connected")

            if not self.client.indices.exists(index=self.index_name):
                # Use provider-specific mapping if not provided
                if mapping is None:
                    from .index_config import get_research_paper_mapping
                    mapping = get_research_paper_mapping(self.provider)

                # Use provider-specific settings if not provided
                if settings is None:
                    from .index_config import get_research_paper_settings
                    settings = get_research_paper_settings()

                body = {"mappings": mapping}
                if settings:
                    body["settings"] = settings

                self.client.indices.create(
                    index=self.index_name,
                    body=body
                )
                logger.info(f"Created index: {self.index_name} for provider: {self.provider}")
            else:
                logger.info(f"Index already exists: {self.index_name}")
        except Exception as e:
            logger.error(f"Failed to create index: {e}")
            raise

    def delete_index(self):
        """Delete index"""
        try:
            if not self.client:
                raise Exception("OpenSearch client not connected")

            if self.client.indices.exists(index=self.index_name):
                self.client.indices.delete(index=self.index_name)
                logger.info(f"Deleted index: {self.index_name}")
            else:
                logger.info(f"Index does not exist: {self.index_name}")
        except Exception as e:
            logger.error(f"Failed to delete index: {e}")
            raise

    def get_index_mapping(self) -> Dict[str, Any]:
        """Get index mapping"""
        try:
            if not self.client:
                raise Exception("OpenSearch client not connected")

            return self.client.indices.get_mapping(index=self.index_name)
        except Exception as e:
            logger.error(f"Failed to get index mapping: {e}")
            raise

    def update_index_mapping(self, mapping: Dict[str, Any]):
        """Update index mapping"""
        try:
            if not self.client:
                raise Exception("OpenSearch client not connected")

            self.client.indices.put_mapping(
                index=self.index_name,
                body=mapping
            )
            logger.info(f"Updated mapping for index: {self.index_name}")
        except Exception as e:
            logger.error(f"Failed to update index mapping: {e}")
            raise

    def index_document(self, doc_id: str, document: Dict[str, Any]):
        """Index a document"""
        try:
            if not self.client:
                raise Exception("OpenSearch client not connected")

            response = self.client.index(
                index=self.index_name,
                id=doc_id,
                body=document
            )
            return response
        except Exception as e:
            logger.error(f"Failed to index document {doc_id}: {e}")
            raise

    def bulk_index_documents(self, documents: List[Tuple[str, Dict[str, Any]]]) -> Dict[str, Any]:
        """Bulk index documents efficiently"""
        try:
            if not self.client:
                raise Exception("OpenSearch client not connected")

            actions = []
            for doc_id, document in documents:
                actions.append({
                    "_index": self.index_name,
                    "_id": doc_id,
                    "_source": document
                })

            success, failed = bulk(self.client, actions, stats_only=False, raise_on_error=False)
            logger.info(f"Bulk indexed {success} documents, {len(failed)} failed")

            return {
                "successful": success,
                "failed": len(failed),
                "failures": failed
            }
        except Exception as e:
            logger.error(f"Failed to bulk index documents: {e}")
            raise

    def search(self, query: Dict[str, Any], size: int = 10) -> Dict[str, Any]:
        """Search documents"""
        try:
            if not self.client:
                raise Exception("OpenSearch client not connected")

            response = self.client.search(
                index=self.index_name,
                body=query,
                size=size
            )
            return response
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    def bm25_search(
        self,
        query: str,
        fields: Optional[List[str]] = None,
        field_boosts: Optional[Dict[str, float]] = None,
        filters: Optional[Dict[str, Any]] = None,
        size: int = 10,
        highlight: bool = True
    ) -> Dict[str, Any]:
        """Perform BM25 keyword search with field boosting"""
        try:
            if not self.client:
                raise Exception("OpenSearch client not connected")

            # Default fields and boosts for research papers
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

            # Build query with filters
            query_body = {"query": multi_match}
            if filters:
                query_body["query"] = {
                    "bool": {
                        "must": multi_match,
                        "filter": filters
                    }
                }

            # Add highlighting
            if highlight:
                query_body["highlight"] = {
                    "fields": {field: {} for field in fields},
                    "pre_tags": ["<em>"],
                    "post_tags": ["</em>"]
                }

            query_body["size"] = size

            response = self.client.search(
                index=self.index_name,
                body=query_body
            )
            return response
        except Exception as e:
            logger.error(f"BM25 search failed: {e}")
            raise

    def vector_search(
        self,
        vector: List[float],
        vector_field: str = "embedding",
        filters: Optional[Dict[str, Any]] = None,
        size: int = 10
    ) -> Dict[str, Any]:
        """Perform vector similarity search"""
        try:
            if not self.client:
                raise Exception("OpenSearch client not connected")

            query = {
                "query": {
                    "knn": {
                        vector_field: {
                            "vector": vector,
                            "k": size
                        }
                    }
                },
                "size": size
            }

            # Add filters if provided
            if filters:
                query["query"] = {
                    "bool": {
                        "must": query["query"],
                        "filter": filters
                    }
                }

            response = self.client.search(
                index=self.index_name,
                body=query
            )
            return response
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            raise

    def reciprocal_rank_fusion(
        self,
        results1: List[Dict[str, Any]],
        results2: List[Dict[str, Any]],
        k: int = 60
    ) -> List[Dict[str, Any]]:
        """Combine results using Reciprocal Rank Fusion (RRF)"""
        # Create score mapping
        score_map = {}

        # Process first result set
        for rank, result in enumerate(results1, 1):
            doc_id = result["_id"]
            score = 1.0 / (k + rank)
            score_map[doc_id] = {
                "score": score,
                "doc": result,
                "rank1": rank,
                "rank2": None
            }

        # Process second result set
        for rank, result in enumerate(results2, 1):
            doc_id = result["_id"]
            score = 1.0 / (k + rank)
            if doc_id in score_map:
                score_map[doc_id]["score"] += score
                score_map[doc_id]["rank2"] = rank
            else:
                score_map[doc_id] = {
                    "score": score,
                    "doc": result,
                    "rank1": None,
                    "rank2": rank
                }

        # Sort by combined score
        sorted_results = sorted(
            score_map.values(),
            key=lambda x: x["score"],
            reverse=True
        )

        # Return combined results
        return [item["doc"] for item in sorted_results]

    def hybrid_search(
        self,
        text_query: str,
        vector_query: List[float],
        mode: str = "hybrid",
        text_weight: float = 0.7,
        vector_weight: float = 0.3,
        rrf_k: int = 60,
        filters: Optional[Dict[str, Any]] = None,
        size: int = 10,
        highlight: bool = True
    ) -> Dict[str, Any]:
        """Perform hybrid search with configurable modes"""
        try:
            if not self.client:
                raise Exception("OpenSearch client not connected")

            if mode == "bm25_only":
                return self.bm25_search(
                    query=text_query,
                    filters=filters,
                    size=size,
                    highlight=highlight
                )
            elif mode == "vector_only":
                return self.vector_search(
                    vector=vector_query,
                    filters=filters,
                    size=size
                )
            elif mode == "hybrid":
                # Get BM25 results
                bm25_results = self.bm25_search(
                    query=text_query,
                    filters=filters,
                    size=size * 2,  # Get more results for RRF
                    highlight=highlight
                )

                # Get vector results
                vector_results = self.vector_search(
                    vector=vector_query,
                    filters=filters,
                    size=size * 2  # Get more results for RRF
                )

                # Apply RRF
                combined_hits = self.reciprocal_rank_fusion(
                    bm25_results["hits"]["hits"],
                    vector_results["hits"]["hits"],
                    k=rrf_k
                )

                # Return formatted response
                return {
                    "took": bm25_results["took"] + vector_results["took"],
                    "timed_out": False,
                    "_shards": bm25_results["_shards"],
                    "hits": {
                        "total": {"value": len(combined_hits), "relation": "eq"},
                        "max_score": combined_hits[0]["_score"] if combined_hits else 0,
                        "hits": combined_hits[:size]
                    }
                }
            else:
                raise ValueError(f"Unknown search mode: {mode}")

        except Exception as e:
            logger.error(f"Hybrid search failed: {e}")
            raise

    def delete_document(self, doc_id: str):
        """Delete a document"""
        try:
            if not self.client:
                raise Exception("OpenSearch client not connected")

            self.client.delete(
                index=self.index_name,
                id=doc_id
            )
        except NotFoundError:
            logger.warning(f"Document {doc_id} not found")
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            raise

    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a document by ID"""
        try:
            if not self.client:
                raise Exception("OpenSearch client not connected")

            response = self.client.get(
                index=self.index_name,
                id=doc_id
            )
            return response["_source"]
        except NotFoundError:
            return None
        except Exception as e:
            logger.error(f"Failed to get document {doc_id}: {e}")
            raise

    def update_document(self, doc_id: str, document: Dict[str, Any]):
        """Update a document"""
        try:
            if not self.client:
                raise Exception("OpenSearch client not connected")

            response = self.client.update(
                index=self.index_name,
                id=doc_id,
                body={"doc": document}
            )
            return response
        except Exception as e:
            logger.error(f"Failed to update document {doc_id}: {e}")
            raise

    def get_index_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        try:
            if not self.client:
                raise Exception("OpenSearch client not connected")

            return self.client.indices.stats(index=self.index_name)
        except Exception as e:
            logger.error(f"Failed to get index stats: {e}")
            raise

    def refresh_index(self):
        """Refresh index to make recent changes searchable"""
        try:
            if not self.client:
                raise Exception("OpenSearch client not connected")

            self.client.indices.refresh(index=self.index_name)
            logger.info(f"Refreshed index: {self.index_name}")
        except Exception as e:
            logger.error(f"Failed to refresh index: {e}")
            raise

    def get_search_explain(self, doc_id: str, query: Dict[str, Any]) -> Dict[str, Any]:
        """Explain why a document matched a query"""
        try:
            if not self.client:
                raise Exception("OpenSearch client not connected")

            return self.client.explain(
                index=self.index_name,
                id=doc_id,
                body=query
            )
        except Exception as e:
            logger.error(f"Failed to explain search for doc {doc_id}: {e}")
            raise