# Search Text Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/search/text`

### HTTP Method
POST

### Description
Text-based search with BM25, vector, or hybrid modes. Supports different search modes including BM25-only, vector-only, and hybrid search combining both approaches. The endpoint performs searches against indexed documents using OpenSearch, with optional vector embeddings for semantic search.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations.
- Calls `OpenSearchService` for performing BM25, vector, or hybrid searches.
- Uses `EmbeddingService` for generating vector embeddings when vector or hybrid modes are selected.
- Uses `RedisCache` for caching successful search results (TTL: 300 seconds).
- Uses `performance_monitor`, `search_analytics`, and `search_audit_logger` for monitoring, analytics recording, and audit logging.
- Uses `rate_limit("search")` for rate limiting search requests.
- Uses Pydantic schemas from `src/schemas/search.py` for request and response validation.

## Authentication

### Requirements
- Authentication is mandatory and handled via the `get_current_active_user` dependency (from `src/services/auth.py`).
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).
- The token is decoded and verified to ensure the user is active.

### Required Headers
- `Authorization`: Bearer token (required for authentication; the token is validated via `get_current_active_user` dependency).

## Authorization

### Requirements
- No specific authorization checks beyond authentication; any active user can perform searches.

## Request

### Request Body Schema
The request body must conform to the `SearchRequest` schema (from `src/schemas/search.py`). All fields are validated using Pydantic.

- **query** (str, required): The search query string.
- **mode** (str, optional): Search mode. Options: "bm25_only", "vector_only", "hybrid". Defaults to "hybrid".
- **limit** (int, optional): Maximum number of results to return. Defaults to 10.
- **offset** (int, optional): Number of results to skip. Defaults to 0.
- **filters** (Dict[str, Any], optional): Additional filters to apply to the search. Defaults to None.
- **include_highlights** (bool, optional): Whether to include highlight snippets in results. Defaults to True.
- **search_fields** (List[str], optional): Specific fields to search in. Defaults to None.
- **field_boosts** (Dict[str, float], optional): Field boost values for scoring. Defaults to None.

### Content-Type
- `application/json`

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
The response conforms to the `SearchResponse` schema.

- **query** (str): The original search query.
- **total** (int): Total number of matching documents.
- **results** (List[SearchResult]): List of search results.
- **took** (float): Time taken for the search in seconds.

Each SearchResult contains:
- **id** (str): Document ID.
- **title** (str): Document title.
- **abstract** (str, optional): Document abstract.
- **authors** (List[str]): List of authors.
- **score** (float): Relevance score.
- **highlights** (Dict[str, List[str]], optional): Highlighted snippets.

### Example Response (JSON)
```json
{
  "query": "machine learning",
  "total": 150,
  "results": [
    {
      "id": "doc1",
      "title": "Introduction to Machine Learning",
      "abstract": "This paper introduces...",
      "authors": ["John Doe"],
      "score": 0.95,
      "highlights": {
        "title": ["<em>Introduction</em> to <em>Machine Learning</em>"]
      }
    }
  ],
  "took": 0.123
}
```

## Error Responses

### 400 Bad Request
- **Status Code**: 400
- **Message**: "Unknown search mode: {mode}"
- **Condition**: Triggered when an invalid search mode is provided (not one of "bm25_only", "vector_only", "hybrid").

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Search failed: {error details}"
- **Condition**: Any exception during search execution, such as service connection failures or processing errors.

## Testing Example

### Example Command
```powershell
Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/search/text' -Method POST -ContentType 'application/json' -Headers @{Authorization="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I"} -Body '{"query": "machine learning", "mode": "hybrid", "limit": 10}'
```

### Valid Payload
```json
{
  "query": "machine learning",
  "mode": "hybrid",
  "limit": 10
}
```

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"query":"machine learning","total":150,"results":[...],"took":0.123}
```

Note: The response includes search results based on the query and mode. Results are cached for 5 minutes. Analytics and audit logs are recorded for each search.