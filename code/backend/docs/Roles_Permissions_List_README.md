# Roles Permissions List Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/roles/permissions`

### HTTP Method
GET

### Description
This endpoint allows authenticated users to list all permissions with optional pagination.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations.
- Calls `role_service.list_permissions` (from `src/services/role.py`) to retrieve the list of permissions.

## Authentication

### Requirements
- Authentication is mandatory and handled via the `get_current_active_user` dependency (from `src/services/auth.py`).
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).
- The token is decoded and verified to ensure the user is active.

### Required Headers
- `Authorization`: Bearer token (required for authentication; the token is validated via `get_current_active_user` dependency).

## Authorization

### Requirements
- No additional authorization checks; any authenticated user can list permissions.

## Request

### Request Body Schema
No request body required.

### Query Parameters
- **skip** (int, optional): Number of permissions to skip for pagination. Defaults to 0.
- **limit** (int, optional): Maximum number of permissions to return. Defaults to 100.

### Content-Type
- Not applicable (GET request)

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
The response is a list of `PermissionResponse` schemas (from `src/schemas/role.py`).

Each item in the list:
- **id** (UUID): The unique identifier of the permission.
- **name** (str): The name of the permission.
- **description** (str, optional): The description of the permission.
- **resource** (str): The resource.
- **action** (str): The action.
- **created_at** (datetime): The creation timestamp.
- **updated_at** (datetime): The last update timestamp.

### Example Response (JSON)
```json
[
  {
    "id": "123e4567-e89b-12d3-a456-426614174000",
    "name": "Read Papers",
    "description": "Permission to read papers",
    "resource": "papers",
    "action": "read",
    "created_at": "2023-10-01T12:00:00Z",
    "updated_at": "2023-10-01T12:00:00Z"
  },
  {
    "id": "456e7890-e89b-12d3-a456-426614174001",
    "name": "Write Papers",
    "description": "Permission to write papers",
    "resource": "papers",
    "action": "write",
    "created_at": "2023-10-01T12:00:00Z",
    "updated_at": "2023-10-01T12:00:00Z"
  }
]
```

## Error Responses

### 400 Bad Request
- **Status Code**: 400
- **Message**: Dynamic string based on exceptions from `role_service.list_permissions` (e.g., database issues).
- **Condition**: Any exception raised during permission listing in the service layer.

## Testing Example

### Example Command
```bash
curl -X GET 'http://localhost:8000/api/v1/roles/permissions?skip=0&limit=10' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I'
```

### Valid Payload
Not applicable (GET request)

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: [{"id":"123e4567-e89b-12d3-a456-426614174000","name":"Read Papers","description":"Permission to read papers","resource":"papers","action":"read","created_at":"2023-10-01T12:00:00Z","updated_at":"2023-10-01T12:00:00Z"},{"id":"456e7890-e89b-12d3-a456-426614174001","name":"Write Papers","description":"Permission to write papers","resource":"papers","action":"write","created_at":"2023-10-01T12:00:00Z","updated_at":"2023-10-01T12:00:00Z"}]
```

Note: The response is an array of permission objects as per the `PermissionResponse` schema. Timestamps and UUIDs will be dynamically generated based on actual data.