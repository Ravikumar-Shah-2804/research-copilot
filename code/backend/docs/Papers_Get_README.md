# Papers Get Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/papers/{paper_id}` (assuming the router is mounted at `/api/v1/papers` in the main application; the endpoint is defined as `@router.get("/{paper_id}")`)

### HTTP Method
GET

### Description
This endpoint allows authenticated users to retrieve a specific research paper by its unique identifier. It returns the full paper details including metadata, content, and processing status.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations.
- Calls `PaperRepository.get_by_id` (from `src/repositories/paper.py`) to retrieve the paper.
- Uses Pydantic schemas from `src/schemas/paper.py` for response validation.

## Authentication

### Requirements
- Authentication is mandatory and handled via the `get_current_active_user` dependency (from `src/services/auth.py`).
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).
- The token is decoded and verified to ensure the user is active.

### Required Headers
- `Authorization`: Bearer token (required for authentication; the token is validated via `get_current_active_user` dependency).

## Authorization

### Requirements
- No specific authorization checks beyond authentication; any active authenticated user can retrieve papers.

## Request

### Path Parameters
- **paper_id** (UUID, required): The unique identifier of the paper to retrieve.

### Content-Type
- Not applicable (GET request with path parameter)

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
The response conforms to the `PaperResponse` schema (from `src/schemas/paper.py`). Fields are identical to those in the Papers Create endpoint.

### Example Response (JSON)
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "arxiv_id": "2101.12345",
  "doi": null,
  "title": "Sample Research Paper",
  "authors": ["Author One", "Author Two"],
  "abstract": "This is a sample abstract...",
  "categories": ["cs.AI"],
  "published_date": "2021-01-15T00:00:00Z",
  "pdf_url": "https://arxiv.org/pdf/2101.12345.pdf",
  "raw_text": null,
  "sections": null,
  "references": null,
  "parser_used": null,
  "parser_metadata": null,
  "pdf_processed": false,
  "pdf_processing_date": null,
  "pdf_file_size": null,
  "pdf_page_count": null,
  "tags": null,
  "keywords": null,
  "journal_ref": null,
  "comments": null,
  "ingestion_status": "pending",
  "ingestion_attempts": 0,
  "last_ingestion_attempt": null,
  "ingestion_errors": null,
  "created_at": "2023-10-01T12:00:00Z",
  "updated_at": "2023-10-01T12:00:00Z",
  "created_by": "456e7890-e89b-12d3-a456-426614174001",
  "last_modified_by": null,
  "source": "arxiv",
  "quality_score": null,
  "duplicate_of": null
}
```

## Error Responses

### 404 Not Found
- **Status Code**: 404
- **Message**: "Paper not found"
- **Condition**: Triggered when the specified `paper_id` does not exist in the database.

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Failed to get paper: {error details}"
- **Condition**: Triggered when the repository method raises an exception during paper retrieval.

## Testing Example

### Example Command
```bash
curl -X GET 'http://localhost:8000/api/v1/papers/123e4567-e89b-12d3-a456-426614174000' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I'
```

### Valid Request
```
GET /api/v1/papers/123e4567-e89b-12d3-a456-426614174000
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I
```

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"id":"123e4567-e89b-12d3-a456-426614174000","arxiv_id":"2101.12345","doi":null,"title":"Sample Research Paper","authors":["Author One","Author Two"],"abstract":"This is a sample abstract...","categories":["cs.AI"],"published_date":"2021-01-15T00:00:00Z","pdf_url":"https://arxiv.org/pdf/2101.12345.pdf","raw_text":null,"sections":null,"references":null,"parser_used":null,"parser_metadata":null,"pdf_processed":false,"pdf_processing_date":null,"pdf_file_size":null,"pdf_page_count":null,"tags":null,"keywords":null,"journal_ref":null,"comments":null,"ingestion_status":"pending","ingestion_attempts":0,"last_ingestion_attempt":null,"ingestion_errors":null,"created_at":"2023-10-01T12:00:00Z","updated_at":"2023-10-01T12:00:00Z","created_by":"456e7890-e89b-12d3-a456-426614174001","last_modified_by":null,"source":"arxiv","quality_score":null,"duplicate_of":null}
```

Note: The response includes all paper fields. If the paper has been processed, fields like `raw_text`, `sections`, and `references` will contain extracted content.