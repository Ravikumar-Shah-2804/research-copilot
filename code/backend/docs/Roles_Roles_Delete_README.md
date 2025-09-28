# Roles Roles Delete Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/roles/roles/{role_id}`

### HTTP Method
DELETE

### Description
This endpoint allows superusers to delete an existing role by its ID.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations.
- Calls `role_service.delete_role` (from `src/services/role.py`) to perform the deletion logic.

## Authentication

### Requirements
- Authentication is mandatory and handled via the `get_current_active_user` dependency (from `src/services/auth.py`).
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).
- The token is decoded and verified to ensure the user is active.

### Required Headers
- `Authorization`: Bearer token (required for authentication; the token is validated via `get_current_active_user` dependency).

## Authorization

### Requirements
- Only superusers (`current_user.is_superuser` is `True`) can delete roles.

## Request

### Request Body Schema
No request body required.

### Path Parameters
- **role_id** (UUID, required): The unique identifier of the role to delete.

### Content-Type
- Not applicable (DELETE request)

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
  "message": "Role deleted successfully"
}
```

## Error Responses

### 403 Forbidden
- **Status Code**: 403
- **Message**: "Only superusers can delete roles"
- **Condition**: Triggered if the authenticated user is not a superuser.

### 400 Bad Request
- **Status Code**: 400
- **Message**: Dynamic string based on the exception from `role_service.delete_role` (e.g., validation errors, database issues).
- **Condition**: Any exception raised during role deletion in the service layer.

## Testing Example

### Example Command
```bash
curl -X DELETE 'http://localhost:8000/api/v1/roles/roles/123e4567-e89b-12d3-a456-426614174000' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I'
```

### Valid Payload
Not applicable (DELETE request)

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"message": "Role deleted successfully"}
```

Note: The response is a simple confirmation message. The role is permanently removed from the database.