"""
OpenSearch index configuration for research papers
"""
from typing import Dict, Any, Literal


# Provider-specific embedding dimensions
EMBEDDING_DIMENSIONS = {
    "openrouter": 1536,
    "gemini": 768
}


def get_index_name(provider: str = "openrouter") -> str:
    """Get index name for a specific embedding provider"""
    return f"research_papers_{provider}"


def get_research_paper_mapping(provider: str = "openrouter") -> Dict[str, Any]:
    """Get mapping for research papers index based on embedding provider"""
    embedding_dimension = EMBEDDING_DIMENSIONS.get(provider, 1536)
    """Get mapping for research papers index"""
    return {
        "properties": {
            # Basic metadata
            "paper_id": {
                "type": "keyword",
                "index": True
            },
            "title": {
                "type": "text",
                "analyzer": "standard",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256
                    }
                }
            },
            "abstract": {
                "type": "text",
                "analyzer": "standard",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 1000
                    }
                }
            },
            "authors": {
                "type": "keyword",
                "fields": {
                    "text": {
                        "type": "text",
                        "analyzer": "standard"
                    }
                }
            },
            "published_date": {
                "type": "date",
                "format": "yyyy-MM-dd||yyyy-MM-dd'T'HH:mm:ss||epoch_millis"
            },
            "categories": {
                "type": "keyword"
            },
            "journal_ref": {
                "type": "text",
                "analyzer": "standard"
            },
            "doi": {
                "type": "keyword"
            },

            # Content fields
            "content": {
                "type": "text",
                "analyzer": "standard",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 10000
                    }
                }
            },

            # Chunked content for better retrieval
            "chunks": {
                "type": "nested",
                "properties": {
                    "chunk_id": {
                        "type": "keyword"
                    },
                    "content": {
                        "type": "text",
                        "analyzer": "standard"
                    },
                    "page_number": {
                        "type": "integer"
                    },
                    "section": {
                        "type": "keyword"
                    },
                    "embedding": {
                        "type": "knn_vector",
                        "dimension": embedding_dimension,
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib",
                            "parameters": {
                                "ef_construction": 128,
                                "m": 24
                            }
                        }
                    }
                }
            },

            # Document-level embedding
            "embedding": {
                "type": "knn_vector",
                "dimension": embedding_dimension,
                "method": {
                    "name": "hnsw",
                    "space_type": "cosinesimil",
                    "engine": "nmslib",
                    "parameters": {
                        "ef_construction": 128,
                        "m": 24
                    }
                }
            },

            # Quality and metadata
            "quality_score": {
                "type": "float"
            },
            "word_count": {
                "type": "integer"
            },
            "page_count": {
                "type": "integer"
            },
            "has_figures": {
                "type": "boolean"
            },
            "has_tables": {
                "type": "boolean"
            },

            # Processing metadata
            "processed_at": {
                "type": "date",
                "format": "yyyy-MM-dd'T'HH:mm:ss||epoch_millis"
            },
            "source_url": {
                "type": "keyword"
            },
            "file_path": {
                "type": "keyword"
            },

            # Search analytics
            "view_count": {
                "type": "integer"
            },
            "download_count": {
                "type": "integer"
            },
            "last_accessed": {
                "type": "date",
                "format": "yyyy-MM-dd'T'HH:mm:ss||epoch_millis"
            }
        }
    }


def get_research_paper_settings() -> Dict[str, Any]:
    """Get settings for research papers index"""
    return {
        "index": {
            "number_of_shards": 3,
            "number_of_replicas": 1,
            "refresh_interval": "30s",
            "knn": True,  # Enable k-NN search
            "knn.algo_param": {
                "ef_search": 100
            }
        },
        "analysis": {
            "analyzer": {
                "standard": {
                    "type": "standard",
                    "stopwords": "_english_"
                }
            }
        }
    }


def get_chunk_mapping(provider: str = "openrouter") -> Dict[str, Any]:
    """Get mapping for document chunks index based on embedding provider"""
    embedding_dimension = EMBEDDING_DIMENSIONS.get(provider, 1536)
    return {
        "properties": {
            "chunk_id": {
                "type": "keyword"
            },
            "paper_id": {
                "type": "keyword"
            },
            "content": {
                "type": "text",
                "analyzer": "standard",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 1000
                    }
                }
            },
            "chunk_index": {
                "type": "integer"
            },
            "total_chunks": {
                "type": "integer"
            },
            "page_number": {
                "type": "integer"
            },
            "section": {
                "type": "keyword"
            },
            "word_count": {
                "type": "integer"
            },
            "embedding": {
                "type": "knn_vector",
                "dimension": embedding_dimension,
                "method": {
                    "name": "hnsw",
                    "space_type": "cosinesimil",
                    "engine": "nmslib",
                    "parameters": {
                        "ef_construction": 128,
                        "m": 24
                    }
                }
            },
            "created_at": {
                "type": "date",
                "format": "yyyy-MM-dd'T'HH:mm:ss||epoch_millis"
            }
        }
    }


def get_chunk_settings() -> Dict[str, Any]:
    """Get settings for chunks index"""
    return {
        "index": {
            "number_of_shards": 5,
            "number_of_replicas": 1,
            "refresh_interval": "10s",
            "knn": True,
            "knn.algo_param": {
                "ef_search": 100
            }
        },
        "analysis": {
            "analyzer": {
                "standard": {
                    "type": "standard",
                    "stopwords": "_english_"
                }
            }
        }
    }