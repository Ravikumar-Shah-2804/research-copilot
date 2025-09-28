# Roles Roles Create Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/roles/roles`

### HTTP Method
POST

### Description
This endpoint allows superusers to create a new role with associated permissions.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations.
- Calls `role_service.create_role` (from `src/services/role.py`) to perform the creation logic.

## Authentication

### Requirements
- Authentication is mandatory and handled via the `get_current_active_user` dependency (from `src/services/auth.py`).
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).
- The token is decoded and verified to ensure the user is active.

### Required Headers
- `Authorization`: Bearer token (required for authentication; the token is validated via `get_current_active_user` dependency).

## Authorization

### Requirements
- Only superusers (`current_user.is_superuser` is `True`) can create roles.

## Request

### Request Body Schema
The request body must conform to the `RoleCreate` schema (from `src/schemas/role.py`). All fields are validated using Pydantic.

- **name** (str, required): The name of the role. Constraints: minimum length 1, maximum length 100.
- **description** (str, optional): A description of the role.
- **is_default** (bool, optional): Whether the role is a default role. Defaults to `False`.
- **organization_id** (UUID, optional): The UUID of the organization the role belongs to.
- **permission_ids** (List[UUID], optional): A list of permission UUIDs to associate with the role. Defaults to an empty list (`[]`).

### Content-Type
- `application/json`

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
The response conforms to the `RoleResponse` schema (from `src/schemas/role.py`).

- **id** (UUID): The unique identifier of the role.
- **name** (str): The name of the role.
- **description** (str, optional): The description of the role.
- **is_default** (bool): Whether the role is a default role.
- **organization_id** (UUID, optional): The UUID of the associated organization.
- **is_system** (bool): Whether the role is a system role.
- **permissions** (List[PermissionResponse]): The list of associated permissions.
- **created_at** (datetime): The creation timestamp.
- **updated_at** (datetime): The last update timestamp.

### Example Response (JSON)
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Admin Role",
  "description": "Administrator role",
  "is_default": false,
  "organization_id": "456e7890-e89b-12d3-a456-426614174001",
  "is_system": false,
  "permissions": [
    {
      "id": "789e0123-e89b-12d3-a456-426614174002",
      "name": "Read Papers",
      "description": "Permission to read papers",
      "resource": "papers",
      "action": "read",
      "created_at": "2023-10-01T12:00:00Z",
      "updated_at": "2023-10-01T12:00:00Z"
    }
  ],
  "created_at": "2023-10-01T12:00:00Z",
  "updated_at": "2023-10-01T12:00:00Z"
}
```

## Error Responses

### 403 Forbidden
- **Status Code**: 403
- **Message**: "Only superusers can create roles"
- **Condition**: Triggered if the authenticated user is not a superuser.

### 400 Bad Request
- **Status Code**: 400
- **Message**: Dynamic string based on the exception from `role_service.create_role` (e.g., validation errors, database issues).
- **Condition**: Any exception raised during role creation in the service layer.

## Testing Example

### Example Command
```bash
curl -X POST 'http://localhost:8000/api/v1/roles/roles' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I' \
  -d '{"name": "Admin Role", "description": "Administrator role", "permission_ids": ["789e0123-e89b-12d3-a456-426614174002"]}'
```

### Valid Payload
```json
{
  "name": "Admin Role",
  "description": "Administrator role",
  "permission_ids": ["789e0123-e89b-12d3-a456-426614174002"]
}
```

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"id":"123e4567-e89b-12d3-a456-426614174000","name":"Admin Role","description":"Administrator role","is_default":false,"organization_id":"456e7890-e89b-12d3-a456-426614174001","is_system":false,"permissions":[{"id":"789e0123-e89b-12d3-a456-426614174002","name":"Read Papers","description":"Permission to read papers","resource":"papers","action":"read","created_at":"2023-10-01T12:00:00Z","updated_at":"2023-10-01T12:00:00Z"}],"created_at":"2023-10-01T12:00:00Z","updated_at":"2023-10-01T12:00:00Z"}
```

Note: The full JSON response includes all fields as per the `RoleResponse` schema. Timestamps and UUIDs will be dynamically generated.