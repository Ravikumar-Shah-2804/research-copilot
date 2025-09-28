# RAG Stream Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/rag/stream`

### HTTP Method
POST

### Description
This endpoint streams the RAG (Retrieval-Augmented Generation) answer generation in real-time. It sends chunks of the response as they are generated, followed by the sources used.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations.
- Uses `RAGPipeline` from `src/services/rag_pipeline.py` to retrieve context.
- Uses `LLMFactory` and `LLMService` from `src/services/llm/` for streaming generation.
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
- **Content-Type**: `text/event-stream`
- **Headers**:
  - `Cache-Control`: no-cache
  - `Connection`: keep-alive

### Response Schema
The response is a server-sent events stream. Each event is formatted as `data: {json}\n\n`.

- **Chunk events**: `{"chunk": "text chunk here"}` - Incremental text chunks of the answer.
- **Sources event**: `{"type": "sources", "sources": [list of source documents]}`
- **Done event**: `[DONE]`

### Example Response (Stream)
```
data: {"chunk": "Machine learning is"}\n\n
data: {"chunk": " a subset of artificial intelligence..."}\n\n
...
data: {"type": "sources", "sources": [{"id": "doc1", "title": "Intro to ML", ...}]}\n\n
data: [DONE]\n\n
```

## Error Responses

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "RAG streaming failed: {error message}"
- **Condition**: Any exception during streaming execution.

## Testing Example

### Example Command
```bash
curl -X POST http://localhost:8000/api/v1/rag/stream \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-jwt-token>" \
  -d '{"query": "What is machine learning?", "context_limit": 5, "max_tokens": 1000, "temperature": 0.7}' \
  --no-buffer
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
A stream of events as described in the response schema, ending with sources and [DONE].