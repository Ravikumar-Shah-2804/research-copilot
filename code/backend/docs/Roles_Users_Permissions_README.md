# Roles Users Permissions Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/roles/users/{user_id}/permissions`

### HTTP Method
GET

### Description
This endpoint allows users to view their own permissions or admins to view any user's permissions.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations.
- Calls `role_service.get_user_permissions` (from `src/services/role.py`) to retrieve the user's permissions.

## Authentication

### Requirements
- Authentication is mandatory and handled via the `get_current_active_user` dependency (from `src/services/auth.py`).
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).
- The token is decoded and verified to ensure the user is active.

### Required Headers
- `Authorization`: Bearer token (required for authentication; the token is validated via `get_current_active_user` dependency).

## Authorization

### Requirements
- Users can view their own permissions (`current_user.id == user_id`).
- Superusers (`current_user.is_superuser` is `True`) can view any user's permissions.

## Request

### Request Body Schema
No request body required.

### Path Parameters
- **user_id** (UUID, required): The unique identifier of the user whose permissions to retrieve.

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

### 403 Forbidden
- **Status Code**: 403
- **Message**: "Cannot view other users' permissions"
- **Condition**: Triggered if the authenticated user is not a superuser and is trying to view another user's permissions.

### 404 Not Found
- **Status Code**: 404
- **Message**: Dynamic string based on the exception from `role_service.get_user_permissions` (e.g., "User not found").
- **Condition**: Triggered if the user does not exist or other retrieval errors occur.

## Testing Example

### Example Command
```bash
curl -X GET 'http://localhost:8000/api/v1/roles/users/123e4567-e89b-12d3-a456-426614174000/permissions' \
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