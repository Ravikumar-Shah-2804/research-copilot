# Papers Update Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/papers/{paper_id}` (assuming the router is mounted at `/api/v1/papers` in the main application; the endpoint is defined as `@router.put("/{paper_id}")`)

### HTTP Method
PUT

### Description
This endpoint allows authenticated users to update an existing research paper's metadata. Only provided fields are updated, and the operation sets the `last_modified_by` field to the current user.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations.
- Calls `PaperRepository.update_paper` (from `src/repositories/paper.py`) to perform the update.
- Uses Pydantic schemas from `src/schemas/paper.py` for request and response validation.

## Authentication

### Requirements
- Authentication is mandatory and handled via the `get_current_active_user` dependency (from `src/services/auth.py`).
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).
- The token is decoded and verified to ensure the user is active.

### Required Headers
- `Authorization`: Bearer token (required for authentication; the token is validated via `get_current_active_user` dependency).

## Authorization

### Requirements
- No specific authorization checks beyond authentication; any active authenticated user can update papers.

## Request

### Path Parameters
- **paper_id** (UUID, required): The unique identifier of the paper to update.

### Request Body Schema
The request body must conform to the `PaperUpdate` schema (from `src/schemas/paper.py`). All fields are optional and only provided fields will be updated.

- **title** (str, optional): The title of the research paper.
- **abstract** (str, optional): The abstract or summary of the paper.
- **authors** (List[str], optional): A list of author names.
- **categories** (List[str], optional): A list of arXiv category codes.
- **doi** (str, optional): The Digital Object Identifier.
- **journal_ref** (str, optional): Journal reference information.
- **comments** (str, optional): Additional comments.
- **tags** (List[str], optional): User-defined tags.
- **keywords** (List[str], optional): Keywords associated with the paper.
- **quality_score** (float, optional): Quality score.
- **ingestion_status** (IngestionStatus, optional): Status of ingestion process.

### Content-Type
- `application/json`

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
The response conforms to the `PaperResponse` schema (from `src/schemas/paper.py`). Fields are identical to those in the Papers Create endpoint, with updated values where applicable.

### Example Response (JSON)
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "arxiv_id": "2101.12345",
  "doi": "10.1234/example",
  "title": "Updated Sample Research Paper",
  "authors": ["Author One", "Author Two"],
  "abstract": "This is an updated sample abstract...",
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
  "tags": ["updated"],
  "keywords": ["machine learning"],
  "journal_ref": null,
  "comments": "Updated comments",
  "ingestion_status": "pending",
  "ingestion_attempts": 0,
  "last_ingestion_attempt": null,
  "ingestion_errors": null,
  "created_at": "2023-10-01T12:00:00Z",
  "updated_at": "2023-10-01T13:00:00Z",
  "created_by": "456e7890-e89b-12d3-a456-426614174001",
  "last_modified_by": "456e7890-e89b-12d3-a456-426614174001",
  "source": "arxiv",
  "quality_score": 0.85,
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
- **Message**: "Failed to update paper: {error details}"
- **Condition**: Triggered when the repository method raises an exception during paper update.

## Testing Example

### Example Command
```bash
curl -X PUT 'http://localhost:8000/api/v1/papers/123e4567-e89b-12d3-a456-426614174000' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I' \
  -d '{
    "title": "Updated Sample Research Paper",
    "doi": "10.1234/example",
    "tags": ["updated"],
    "keywords": ["machine learning"],
    "comments": "Updated comments",
    "quality_score": 0.85
  }'
```

### Valid Payload
```json
{
  "title": "Updated Sample Research Paper",
  "doi": "10.1234/example",
  "tags": ["updated"],
  "keywords": ["machine learning"],
  "comments": "Updated comments",
  "quality_score": 0.85
}
```

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"id":"123e4567-e89b-12d3-a456-426614174000","arxiv_id":"2101.12345","doi":"10.1234/example","title":"Updated Sample Research Paper","authors":["Author One","Author Two"],"abstract":"This is a sample abstract...","categories":["cs.AI"],"published_date":"2021-01-15T00:00:00Z","pdf_url":"https://arxiv.org/pdf/2101.12345.pdf","raw_text":null,"sections":null,"references":null,"parser_used":null,"parser_metadata":null,"pdf_processed":false,"pdf_processing_date":null,"pdf_file_size":null,"pdf_page_count":null,"tags":["updated"],"keywords":["machine learning"],"journal_ref":null,"comments":"Updated comments","ingestion_status":"pending","ingestion_attempts":0,"last_ingestion_attempt":null,"ingestion_errors":null,"created_at":"2023-10-01T12:00:00Z","updated_at":"2023-10-01T13:00:00Z","created_by":"456e7890-e89b-12d3-a456-426614174001","last_modified_by":"456e7890-e89b-12d3-a456-426614174001","source":"arxiv","quality_score":0.85,"duplicate_of":null}
```

Note: Only the fields provided in the request body are updated. The `updated_at` timestamp and `last_modified_by` field are automatically set. Unprovided fields retain their existing values.