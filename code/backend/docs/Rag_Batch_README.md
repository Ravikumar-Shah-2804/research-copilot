# RAG Batch Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/rag/batch`

### HTTP Method
POST

### Description
This endpoint generates answers for multiple queries in a batch using the RAG pipeline. It processes up to 10 queries per request and returns results for each.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations.
- Uses `RAGPipeline` from `src/services/rag_pipeline.py` to generate answers.
- Calls `search_audit_logger.log_rag_operation` for auditing.
- Applies rate limiting via `@rate_limit("rag")` from `src/services/rate_limiting.py`.

## Authentication

### Requirements
- Authentication is mandatory and handled via the `get_current_active_user` dependency (from `src/services/auth.py`).
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).
- The token is decoded and verified to ensure the user is active.

### Required Headers
- `Authorization`: Bearer token (required for authentication).

## Authorization

### Requirements
- No specific authorization checks beyond authentication; any active user can access this endpoint.

## Request

### Request Parameters
Parameters are passed as query strings since this is a POST endpoint with query parameters.

- **queries** (List[str], required): List of query strings to process. Constraints: maximum 10 queries per batch.
- **context_limit** (int, optional): Number of context documents per query. Defaults to 5.
- **max_tokens** (int, optional): Maximum tokens per response. Defaults to 1000.
- **temperature** (float, optional): Response temperature for generation. Defaults to 0.7.

### Content-Type
- Not applicable (query parameters only).

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
Custom response structure.

- **results** (List[Dict]): List of result objects, one per query.
  - **query** (str): The original query.
  - **answer** (str): The generated answer.
  - **sources** (List[Dict[str, Any]]): Source documents used.
  - **confidence** (float): Confidence score.
  - **tokens_used** (int): Tokens used.
- **total_queries** (int): Number of queries processed.

### Example Response (JSON)
```json
{
  "results": [
    {
      "query": "What is AI?",
      "answer": "Artificial Intelligence is...",
      "sources": [...],
      "confidence": 0.9,
      "tokens_used": 100
    },
    {
      "query": "What is ML?",
      "answer": "Machine Learning is...",
      "sources": [...],
      "confidence": 0.85,
      "tokens_used": 120
    }
  ],
  "total_queries": 2
}
```

## Error Responses

### 400 Bad Request
- **Status Code**: 400
- **Message**: "Maximum 10 queries per batch"
- **Condition**: When more than 10 queries are provided.

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "RAG batch generation failed: {error message}"
- **Condition**: Any exception during batch processing.

## Testing Example

### Example Command
```bash
curl -X POST "http://localhost:8000/api/v1/rag/batch?queries=What%20is%20AI?&queries=What%20is%20ML?&context_limit=5&max_tokens=1000&temperature=0.7" \
  -H "Authorization: Bearer <your-jwt-token>"
```

### Valid Parameters
- queries: ["What is AI?", "What is ML?"]
- context_limit: 5
- max_tokens: 1000
- temperature: 0.7

### Expected Output
```json
{
  "results": [
    {
      "query": "What is AI?",
      "answer": "...",
      "sources": [...],
      "confidence": 0.9,
      "tokens_used": 100
    },
    {
      "query": "What is ML?",
      "answer": "...",
      "sources": [...],
      "confidence": 0.85,
      "tokens_used": 120
    }
  ],
  "total_queries": 2
}