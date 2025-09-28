# Ingestion Failed Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/ingestion/papers/failed` (assuming the router is mounted at `/api/v1/ingestion` in the main application; the endpoint is defined as `@router.get("/papers/failed")`)

### HTTP Method
GET

### Description
This endpoint allows admin users to retrieve a paginated list of papers that have failed ingestion processing. This is useful for monitoring pipeline failures and identifying papers that need retry or manual intervention.

### Dependencies
- Relies on `PaperRepository` from `src/repositories/paper.py` to query failed papers.
- Calls `repo.get_failed_ingestions` with pagination parameters.
- Uses `PaperResponse` schema from `src/schemas/paper.py` for response formatting.
- Uses `get_db` dependency for database access.

## Authentication

### Requirements
- Authentication is mandatory and handled via the `get_current_user` dependency (from `src/services/auth.py`).
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).
- The token is decoded and verified to ensure the user is active.

### Required Headers
- `Authorization`: Bearer token (required for authentication; the token is validated via `get_current_user` dependency).

## Authorization

### Requirements
- The authenticated user must have admin privileges (`current_user.is_admin` is `True`).

## Request

### Query Parameters
- **limit** (int, optional, default 50): Maximum number of papers to return.
- **offset** (int, optional, default 0): Number of papers to skip for pagination.

### Content-Type
- No request body required.

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
An array of `PaperResponse` objects, each containing full paper metadata including error details. See the PaperResponse schema for complete field details.

### Example Response (JSON)
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "arxiv_id": "2101.12345",
    "doi": null,
    "title": "Sample Paper Title",
    "authors": ["Author One", "Author Two"],
    "abstract": "Paper abstract...",
    "categories": ["cs.AI"],
    "published_date": "2021-01-01T00:00:00Z",
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
    "ingestion_status": "failed",
    "ingestion_attempts": 3,
    "last_ingestion_attempt": "2023-10-01T12:30:00Z",
    "ingestion_errors": [{"error": "PDF download failed", "timestamp": "2023-10-01T12:30:00Z"}],
    "created_at": "2023-10-01T12:00:00Z",
    "updated_at": "2023-10-01T12:30:00Z",
    "created_by": "456e7890-e89b-12d3-a456-426614174001",
    "last_modified_by": null,
    "source": "arxiv",
    "quality_score": null,
    "duplicate_of": null
  }
]
```

## Error Responses

### 403 Forbidden
- **Status Code**: 403
- **Message**: "Admin access required"
- **Condition**: Triggered if the authenticated user does not have admin privileges.

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Failed to get failed ingestions: {error_message}"
- **Condition**: Triggered if an exception occurs during database query.

## Testing Example

### Example Command
```powershell
Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/ingestion/papers/failed?limit=10&offset=0' -Method GET -Headers @{Authorization="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I"}
```

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: [{"id":"123e4567-e89b-12d3-a456-426614174000","arxiv_id":"2101.12345","doi":null,"title":"Sample Paper Title","authors":["Author One","Author Two"],"abstract":"Paper abstract...","categories":["cs.AI"],"published_date":"2021-01-01T00:00:00Z","pdf_url":"https://arxiv.org/pdf/2101.12345.pdf","raw_text":null,"sections":null,"references":null,"parser_used":null,"parser_metadata":null,"pdf_processed":false,"pdf_processing_date":null,"pdf_file_size":null,"pdf_page_count":null,"tags":null,"keywords":null,"journal_ref":null,"comments":null,"ingestion_status":"failed","ingestion_attempts":3,"last_ingestion_attempt":"2023-10-01T12:30:00Z","ingestion_errors":[{"error":"PDF download failed","timestamp":"2023-10-01T12:30:00Z"}],"created_at":"2023-10-01T12:00:00Z","updated_at":"2023-10-01T12:30:00Z","created_by":"456e7890-e89b-12d3-a456-426614174001","last_modified_by":null,"source":"arxiv","quality_score":null,"duplicate_of":null}]
```

Note: This endpoint is restricted to admin users only. Failed papers have `ingestion_status` of "failed" and may include `ingestion_errors` with details about the failure. Use pagination parameters to control the response size.