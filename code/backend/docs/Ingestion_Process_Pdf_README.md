# Ingestion Process Pdf Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/ingestion/paper/{paper_id}/process-pdf` (assuming the router is mounted at `/api/v1/ingestion` in the main application; the endpoint is defined as `@router.post("/paper/{paper_id}/process-pdf")`)

### HTTP Method
POST

### Description
This endpoint allows authenticated users to manually trigger PDF processing for a specific paper. This is useful for retrying failed processing or manually processing papers that were not automatically processed. The processing runs in the background.

### Dependencies
- Relies on `PaperRepository` from `src/repositories/paper.py` to check paper existence and ownership.
- Relies on `IngestionService` from `src/services/ingestion.py` to handle the PDF processing.
- Calls `ingestion_service.process_single_paper_pdf` as a background task to perform the actual processing.
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
- The authenticated user must either be the creator of the paper (`paper.created_by == current_user.id`) or have admin privileges (`current_user.is_admin` is `True`).

## Request

### Path Parameters
- **paper_id** (UUID, required): The unique identifier of the paper to process.

### Content-Type
- No request body required.

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
A simple JSON object with a confirmation message.

- **message** (str): Confirmation message indicating PDF processing has started.

### Example Response (JSON)
```json
{
  "message": "PDF processing started for paper 123e4567-e89b-12d3-a456-426614174000"
}
```

## Error Responses

### 404 Not Found
- **Status Code**: 404
- **Message**: "Paper not found"
- **Condition**: Triggered if the specified `paper_id` does not exist in the database.

### 403 Forbidden
- **Status Code**: 403
- **Message**: "Not authorized to process this paper"
- **Condition**: Triggered if the authenticated user is neither the paper's creator nor an admin.

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Failed to start PDF processing: {error_message}"
- **Condition**: Triggered if an exception occurs during processing initiation.

## Testing Example

### Example Command
```powershell
Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/ingestion/paper/123e4567-e89b-12d3-a456-426614174000/process-pdf' -Method POST -Headers @{Authorization="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I"}
```

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"message":"PDF processing started for paper 123e4567-e89b-12d3-a456-426614174000"}
```

Note: The processing runs asynchronously in the background. If the user is not authorized or the paper doesn't exist, appropriate error responses will be returned. The paper must have a valid PDF URL for processing to succeed.