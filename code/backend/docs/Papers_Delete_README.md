# Papers Delete Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/papers/{paper_id}` (assuming the router is mounted at `/api/v1/papers` in the main application; the endpoint is defined as `@router.delete("/{paper_id}")`)

### HTTP Method
DELETE

### Description
This endpoint allows authenticated users to delete a research paper by its unique identifier. The operation permanently removes the paper from the database.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations.
- Calls `PaperRepository.delete` (from `src/repositories/paper.py`) to perform the deletion.
- No response schema validation is applied as it returns a simple message.

## Authentication

### Requirements
- Authentication is mandatory and handled via the `get_current_active_user` dependency (from `src/services/auth.py`).
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).
- The token is decoded and verified to ensure the user is active.

### Required Headers
- `Authorization`: Bearer token (required for authentication; the token is validated via `get_current_active_user` dependency).

## Authorization

### Requirements
- No specific authorization checks beyond authentication; any active authenticated user can delete papers.

## Request

### Path Parameters
- **paper_id** (UUID, required): The unique identifier of the paper to delete.

### Content-Type
- Not applicable (DELETE request with path parameter)

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
A simple JSON object with a success message.

- **message** (str): Confirmation message indicating successful deletion.

### Example Response (JSON)
```json
{
  "message": "Paper deleted successfully"
}
```

## Error Responses

### 404 Not Found
- **Status Code**: 404
- **Message**: "Paper not found"
- **Condition**: Triggered when the specified `paper_id` does not exist in the database.

### 500 Internal Server Error
- **Status Code**: 500
- **Message**: "Failed to delete paper: {error details}"
- **Condition**: Triggered when the repository method raises an exception during paper deletion.

## Testing Example

### Example Command
```bash
curl -X DELETE 'http://localhost:8000/api/v1/papers/123e4567-e89b-12d3-a456-426614174000' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I'
```

### Valid Request
```
DELETE /api/v1/papers/123e4567-e89b-12d3-a456-426614174000
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I
```

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"message": "Paper deleted successfully"}
```

Note: The deletion is permanent and cannot be undone. Ensure the correct `paper_id` is provided as the operation does not prompt for confirmation.