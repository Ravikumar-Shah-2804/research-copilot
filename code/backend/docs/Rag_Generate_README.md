# RAG Generate Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/rag/generate`

### HTTP Method
POST

### Description
This endpoint generates an answer using the RAG (Retrieval-Augmented Generation) pipeline. It retrieves relevant context from documents and generates a response based on the query.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations.
- Uses `RAGPipeline` from `src/services/rag_pipeline.py` to generate answers.
- Calls `search_analytics.record_search_query` and `search_audit_logger.log_rag_operation` for monitoring and auditing.
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

### Request Body Schema
The request body must conform to the `RAGRequest` schema (from `src/schemas/search.py`). All fields are validated using Pydantic.

- **query** (str, required): The query string for which to generate an answer.
- **context_limit** (int, optional): Number of context documents to retrieve. Defaults to 5. Constraints: minimum 1, maximum likely limited by service.
- **max_tokens** (int, optional): Maximum tokens in the response. Defaults to 1000.
- **temperature** (float, optional): Response temperature for generation. Defaults to 0.7. Constraints: 0.0 to 1.0.

### Content-Type
- `application/json`

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
The response conforms to the `RAGResponse` schema (from `src/schemas/search.py`).

- **query** (str): The original query.
- **answer** (str): The generated answer.
- **sources** (List[Dict[str, Any]]): List of source documents used.
- **confidence** (float): Confidence score of the answer.
- **tokens_used** (int): Number of tokens used in generation.

### Example Response (JSON)
```json
{
  "query": "What is machine learning?",
  "answer": "Machine learning is a subset of artificial intelligence...",
  "sources": [
    {
      "id": "doc1",
      "title": "Introduction to ML",
      "content": "..."
    }
  ],
  "confidence": 0.85,
  "tokens_used": 150
}
```

## Error Responses

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "RAG generation failed: {error message}"
- **Condition**: Any exception during RAG pipeline execution.

## Testing Example

### Example Command
```bash
curl -X POST http://localhost:8000/api/v1/rag/generate \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -d '{"query": "What is machine learning?", "context_limit": 5, "max_tokens": 1000, "temperature": 0.7}'
```

### Valid Payload
```json
{
  "query": "What is machine learning?",
  "context_limit": 5,
  "max_tokens": 1000,
  "temperature": 0.7
}
```

### Expected Output
```json
{
  "query": "What is machine learning?",
  "answer": "Machine learning is a method of data analysis...",
  "sources": [...],
  "confidence": 0.9,
  "tokens_used": 200
}