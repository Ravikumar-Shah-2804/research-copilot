# Ingestion Job Cancel Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/ingestion/job/{job_id}` (assuming the router is mounted at `/api/v1/ingestion` in the main application; the endpoint is defined as `@router.delete("/job/{job_id}")`)

### HTTP Method
DELETE

### Description
This endpoint allows authenticated users to cancel an active arXiv ingestion job. Only jobs in "pending" or "running" status can be cancelled. Once cancelled, the job status is updated and no further processing occurs.

### Dependencies
- Relies on `IngestionService` from `src/services/ingestion.py` to handle job cancellation.
- Calls `ingestion_service.cancel_job` to attempt cancellation of the specified job.

## Authentication

### Requirements
- Authentication is mandatory and handled via the `get_current_user` dependency (from `src/services/auth.py`).
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).
- The token is decoded and verified to ensure the user is active.

### Required Headers
- `Authorization`: Bearer token (required for authentication; the token is validated via `get_current_user` dependency).

## Authorization

### Requirements
- No specific authorization checks beyond authentication; any authenticated user can cancel ingestion jobs.

## Request

### Path Parameters
- **job_id** (str, required): The unique identifier of the ingestion job to cancel.

### Content-Type
- No request body required.

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
A simple JSON object with a success message.

- **message** (str): Confirmation message indicating the job was cancelled successfully.

### Example Response (JSON)
```json
{
  "message": "Job 123e4567-e89b-12d3-a456-426614174000 cancelled successfully"
}
```

## Error Responses

### 400 Bad Request
- **Status Code**: 400
- **Message**: "Job could not be cancelled"
- **Condition**: Triggered if the job is not in a cancellable state (not "pending" or "running") or if the job does not exist.

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Failed to cancel job: {error_message}"
- **Condition**: Triggered if an exception occurs during job cancellation in the service layer.

## Testing Example

### Example Command
```powershell
Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/ingestion/job/123e4567-e89b-12d3-a456-426614174000' -Method DELETE -Headers @{Authorization="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I"}
```

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"message":"Job 123e4567-e89b-12d3-a456-426614174000 cancelled successfully"}
```

Note: If the job cannot be cancelled (e.g., already completed or failed), a 400 error will be returned. The cancellation only affects jobs that are still active.