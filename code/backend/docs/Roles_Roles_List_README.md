# Roles Roles List Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/roles/roles`

### HTTP Method
GET

### Description
This endpoint allows authenticated users to list all roles, with optional filtering by organization and pagination.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations.
- Calls `role_service.list_roles` (from `src/services/role.py`) to retrieve the list of roles.

## Authentication

### Requirements
- Authentication is mandatory and handled via the `get_current_active_user` dependency (from `src/services/auth.py`).
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).
- The token is decoded and verified to ensure the user is active.

### Required Headers
- `Authorization`: Bearer token (required for authentication; the token is validated via `get_current_active_user` dependency).

## Authorization

### Requirements
- No additional authorization checks; any authenticated user can list roles.

## Request

### Request Body Schema
No request body required.

### Query Parameters
- **organization_id** (UUID, optional): Filter roles by organization UUID.
- **skip** (int, optional): Number of roles to skip for pagination. Defaults to 0.
- **limit** (int, optional): Maximum number of roles to return. Defaults to 100.

### Content-Type
- Not applicable (GET request)

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
The response is a list of `RoleResponse` schemas (from `src/schemas/role.py`).

Each item in the list:
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
[
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
]
```

## Error Responses

### 400 Bad Request
- **Status Code**: 400
- **Message**: Dynamic string based on exceptions from `role_service.list_roles` (e.g., database issues).
- **Condition**: Any exception raised during role listing in the service layer.

## Testing Example

### Example Command
```bash
curl -X GET 'http://localhost:8000/api/v1/roles/roles?organization_id=456e7890-e89b-12d3-a456-426614174001&skip=0&limit=10' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I'
```

### Valid Payload
Not applicable (GET request)

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: [{"id":"123e4567-e89b-12d3-a456-426614174000","name":"Admin Role","description":"Administrator role","is_default":false,"organization_id":"456e7890-e89b-12d3-a456-426614174001","is_system":false,"permissions":[{"id":"789e0123-e89b-12d3-a456-426614174002","name":"Read Papers","description":"Permission to read papers","resource":"papers","action":"read","created_at":"2023-10-01T12:00:00Z","updated_at":"2023-10-01T12:00:00Z"}],"created_at":"2023-10-01T12:00:00Z","updated_at":"2023-10-01T12:00:00Z"}]
```

Note: The response is an array of role objects as per the `RoleResponse` schema. Timestamps and UUIDs will be dynamically generated based on actual data.