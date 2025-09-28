# Roles Check Permission Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/roles/check-permission`

### HTTP Method
POST

### Description
This endpoint allows authenticated users to check if they have a specific permission based on their assigned roles.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations.
- Calls `role_service.check_user_permission` (from `src/services/role.py`) to perform the permission check logic.

## Authentication

### Requirements
- Authentication is mandatory and handled via the `get_current_active_user` dependency (from `src/services/auth.py`).
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).
- The token is decoded and verified to ensure the user is active.

### Required Headers
- `Authorization`: Bearer token (required for authentication; the token is validated via `get_current_active_user` dependency).

## Authorization

### Requirements
- No additional authorization checks; any authenticated user can check their own permissions.

## Request

### Request Body Schema
The request body must conform to the `PermissionCheck` schema (from `src/schemas/role.py`). All fields are required and validated using Pydantic.

- **resource** (str, required): The resource to check permission for.
- **action** (str, required): The action to check permission for.

### Content-Type
- `application/json`

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
The response conforms to the `PermissionCheckResponse` schema (from `src/schemas/role.py`).

- **has_permission** (bool): Whether the user has the specified permission.
- **user_id** (UUID): The unique identifier of the user.
- **resource** (str): The resource checked.
- **action** (str): The action checked.
- **roles** (List[str]): The list of role names assigned to the user.

### Example Response (JSON)
```json
{
  "has_permission": true,
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "resource": "papers",
  "action": "read",
  "roles": ["Admin", "Editor"]
}
```

## Error Responses

### 400 Bad Request
- **Status Code**: 400
- **Message**: Dynamic string based on exceptions from `role_service.check_user_permission` (e.g., validation errors, database issues).
- **Condition**: Any exception raised during permission checking in the service layer.

## Testing Example

### Example Command
```bash
curl -X POST 'http://localhost:8000/api/v1/roles/check-permission' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I' \
  -d '{"resource": "papers", "action": "read"}'
```

### Valid Payload
```json
{
  "resource": "papers",
  "action": "read"
}
```

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"has_permission":true,"user_id":"123e4567-e89b-12d3-a456-426614174000","resource":"papers","action":"read","roles":["Admin","Editor"]}
```

Note: The response includes the permission check result and the user's roles. The `has_permission` field indicates whether the user has the specified permission based on their assigned roles.