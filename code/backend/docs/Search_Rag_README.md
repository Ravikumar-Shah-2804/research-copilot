# Search RAG Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/search/rag`

### HTTP Method
POST

### Description
RAG (Retrieval-Augmented Generation) query. This endpoint performs a hybrid search to retrieve relevant context documents, then uses a language model to generate an answer based on the query and retrieved context. The response includes the generated answer, sources, confidence score, and token usage.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations.
- Calls `OpenSearchService` for performing hybrid search to retrieve context documents.
- Uses `EmbeddingService` for generating vector embeddings for the query.
- Uses `OpenRouterClient` for generating RAG responses using external LLM services.
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
- No specific authorization checks beyond authentication; any active user can perform RAG queries.

## Request

### Request Body Schema
The request body must conform to the `RAGRequest` schema (from `src/schemas/search.py`). All fields are validated using Pydantic.

- **query** (str, required): The RAG query string.
- **context_limit** (int, optional): Maximum number of context documents to retrieve. Defaults to 5.
- **max_tokens** (int, optional): Maximum number of tokens for the generated response. Defaults to 1000.
- **temperature** (float, optional): Temperature parameter for response generation (controls randomness). Defaults to 0.7.

### Content-Type
- `application/json`

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
The response conforms to the `RAGResponse` schema.

- **query** (str): The original RAG query.
- **answer** (str): The generated answer from the language model.
- **sources** (List[Dict[str, Any]]): List of source documents used for context.
- **confidence** (float): Confidence score for the answer (currently hardcoded to 0.8).
- **tokens_used** (int): Number of tokens used in the generation process.

### Example Response (JSON)
```json
{
  "query": "What is machine learning?",
  "answer": "Machine learning is a subset of artificial intelligence that enables computers to learn and improve from experience without being explicitly programmed. It involves algorithms that can identify patterns in data and make predictions or decisions based on those patterns.",
  "sources": [
    {
      "id": "doc1",
      "title": "Introduction to Machine Learning",
      "abstract": "This paper introduces...",
      "content": "Machine learning...",
      "score": 0.95
    }
  ],
  "confidence": 0.8,
  "tokens_used": 150
}
```

## Error Responses

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "RAG query failed: {error details}"
- **Condition**: Any exception during RAG query execution, such as service connection failures, embedding generation errors, or LLM API failures.

## Testing Example

### Example Command
```powershell
Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/search/rag' -Method POST -ContentType 'application/json' -Headers @{Authorization="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I"} -Body '{"query": "What is machine learning?", "context_limit": 5, "max_tokens": 1000, "temperature": 0.7}'
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
```
StatusCode: 200
StatusDescription: OK
Content: {"query":"What is machine learning?","answer":"Machine learning is...","sources":[...],"confidence":0.8,"tokens_used":150}
```

Note: The RAG process involves retrieving relevant documents via hybrid search, then generating an answer using an external LLM service. The confidence score is currently a placeholder value.