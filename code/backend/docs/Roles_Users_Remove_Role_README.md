# Roles Users Remove Role Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/roles/users/remove-role`

### HTTP Method
POST

### Description
This endpoint allows superusers to remove a role from a user.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations.
- Calls `role_service.remove_role_from_user` (from `src/services/role.py`) to perform the removal logic.

## Authentication

### Requirements
- Authentication is mandatory and handled via the `get_current_active_user` dependency (from `src/services/auth.py`).
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).
- The token is decoded and verified to ensure the user is active.

### Required Headers
- `Authorization`: Bearer token (required for authentication; the token is validated via `get_current_active_user` dependency).

## Authorization

### Requirements
- Only superusers (`current_user.is_superuser` is `True`) can remove roles from users.

## Request

### Request Body Schema
The request body must conform to the `UserRoleRemoval` schema (from `src/schemas/role.py`). All fields are required and validated using Pydantic.

- **user_id** (UUID, required): The unique identifier of the user to remove the role from.
- **role_id** (UUID, required): The unique identifier of the role to remove.

### Content-Type
- `application/json`

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
A simple JSON object with a success message.

- **message** (str): Confirmation message indicating successful removal.

### Example Response (JSON)
```json
{
  "message": "Role removed successfully"
}
```

## Error Responses

### 403 Forbidden
- **Status Code**: 403
- **Message**: "Only superusers can remove roles"
- **Condition**: Triggered if the authenticated user is not a superuser.

### 400 Bad Request
- **Status Code**: 400
- **Message**: Dynamic string based on the exception from `role_service.remove_role_from_user` (e.g., validation errors, database issues).
- **Condition**: Any exception raised during role removal in the service layer.

## Testing Example

### Example Command
```bash
curl -X POST 'http://localhost:8000/api/v1/roles/users/remove-role' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I' \
  -d '{"user_id": "123e4567-e89b-12d3-a456-426614174000", "role_id": "456e7890-e89b-12d3-a456-426614174001"}'
```

### Valid Payload
```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "role_id": "456e7890-e89b-12d3-a456-426614174001"
}
```

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"message": "Role removed successfully"}
```

Note: The response is a simple confirmation message. The role is removed from the user in the database.