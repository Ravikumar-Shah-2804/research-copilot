# Roles Users Assign Role Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/roles/users/assign-role`

### HTTP Method
POST

### Description
This endpoint allows superusers to assign a role to a user.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations.
- Calls `role_service.assign_role_to_user` (from `src/services/role.py`) to perform the assignment logic.

## Authentication

### Requirements
- Authentication is mandatory and handled via the `get_current_active_user` dependency (from `src/services/auth.py`).
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).
- The token is decoded and verified to ensure the user is active.

### Required Headers
- `Authorization`: Bearer token (required for authentication; the token is validated via `get_current_active_user` dependency).

## Authorization

### Requirements
- Only superusers (`current_user.is_superuser` is `True`) can assign roles to users.

## Request

### Request Body Schema
The request body must conform to the `UserRoleAssignment` schema (from `src/schemas/role.py`). All fields are required and validated using Pydantic.

- **user_id** (UUID, required): The unique identifier of the user to assign the role to.
- **role_id** (UUID, required): The unique identifier of the role to assign.

### Content-Type
- `application/json`

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
A simple JSON object with a success message.

- **message** (str): Confirmation message indicating successful assignment.

### Example Response (JSON)
```json
{
  "message": "Role assigned successfully"
}
```

## Error Responses

### 403 Forbidden
- **Status Code**: 403
- **Message**: "Only superusers can assign roles"
- **Condition**: Triggered if the authenticated user is not a superuser.

### 400 Bad Request
- **Status Code**: 400
- **Message**: Dynamic string based on the exception from `role_service.assign_role_to_user` (e.g., validation errors, database issues).
- **Condition**: Any exception raised during role assignment in the service layer.

## Testing Example

### Example Command
```bash
curl -X POST 'http://localhost:8000/api/v1/roles/users/assign-role' \
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
Content: {"message": "Role assigned successfully"}
```

Note: The response is a simple confirmation message. The role is assigned to the user in the database.