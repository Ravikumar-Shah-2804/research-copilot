# Ingestion Retry Failed Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/ingestion/retry-failed/{paper_id}` (assuming the router is mounted at `/api/v1/ingestion` in the main application; the endpoint is defined as `@router.post("/retry-failed/{paper_id}")`)

### HTTP Method
POST

### Description
This endpoint allows admin users to retry the ingestion process for a paper that previously failed. It resets the paper's status to "pending" and initiates background processing to attempt ingestion again.

### Dependencies
- Relies on `PaperRepository` from `src/repositories/paper.py` to check paper status and update it.
- Relies on `IngestionService` from `src/services/ingestion.py` to handle the retry processing.
- Calls `repo.update_ingestion_status` to reset status and `ingestion_service.process_single_paper_pdf` as a background task.
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

### Path Parameters
- **paper_id** (UUID, required): The unique identifier of the failed paper to retry.

### Content-Type
- No request body required.

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
A simple JSON object with a confirmation message.

- **message** (str): Confirmation message indicating the retry has started.

### Example Response (JSON)
```json
{
  "message": "Retry started for paper 123e4567-e89b-12d3-a456-426614174000"
}
```

## Error Responses

### 403 Forbidden
- **Status Code**: 403
- **Message**: "Admin access required"
- **Condition**: Triggered if the authenticated user does not have admin privileges.

### 404 Not Found
- **Status Code**: 404
- **Message**: "Paper not found"
- **Condition**: Triggered if the specified `paper_id` does not exist in the database.

### 400 Bad Request
- **Status Code**: 400
- **Message**: "Paper is not in failed state"
- **Condition**: Triggered if the paper's `ingestion_status` is not "failed".

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Failed to retry ingestion: {error_message}"
- **Condition**: Triggered if an exception occurs during the retry process.

## Testing Example

### Example Command
```powershell
Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/ingestion/retry-failed/123e4567-e89b-12d3-a456-426614174000' -Method POST -Headers @{Authorization="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I"}
```

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"message":"Retry started for paper 123e4567-e89b-12d3-a456-426614174000"}
```

Note: This endpoint is restricted to admin users only. The paper must be in "failed" status to be eligible for retry. The retry resets the status to "pending" and starts background processing. Monitor the paper's status using other endpoints to check retry progress.