# Roles Permissions Get Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/roles/permissions/{permission_id}`

### HTTP Method
GET

### Description
This endpoint allows authenticated users to retrieve a specific permission by its ID.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations.
- Calls `role_service.get_permission` (from `src/services/role.py`) to retrieve the permission.

## Authentication

### Requirements
- Authentication is mandatory and handled via the `get_current_active_user` dependency (from `src/services/auth.py`).
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).
- The token is decoded and verified to ensure the user is active.

### Required Headers
- `Authorization`: Bearer token (required for authentication; the token is validated via `get_current_active_user` dependency).

## Authorization

### Requirements
- No additional authorization checks; any authenticated user can retrieve a permission.

## Request

### Request Body Schema
No request body required.

### Path Parameters
- **permission_id** (UUID, required): The unique identifier of the permission to retrieve.

### Content-Type
- Not applicable (GET request)

## Response

### Success Response
- **Status Code**: 200 OK
- **Content-Type**: `application/json`

### Response Schema
The response conforms to the `PermissionResponse` schema (from `src/schemas/role.py`).

- **id** (UUID): The unique identifier of the permission.
- **name** (str): The name of the permission.
- **description** (str, optional): The description of the permission.
- **resource** (str): The resource.
- **action** (str): The action.
- **created_at** (datetime): The creation timestamp.
- **updated_at** (datetime): The last update timestamp.

### Example Response (JSON)
```json
{
  "id": "123e4567-e89b-12d3-a456-426614174000",
  "name": "Read Papers",
  "description": "Permission to read papers",
  "resource": "papers",
  "action": "read",
  "created_at": "2023-10-01T12:00:00Z",
  "updated_at": "2023-10-01T12:00:00Z"
}
```

## Error Responses

### 404 Not Found
- **Status Code**: 404
- **Message**: Dynamic string based on the exception from `role_service.get_permission` (e.g., "Permission not found").
- **Condition**: Triggered if the permission with the specified ID does not exist or other retrieval errors occur.

## Testing Example

### Example Command
```bash
curl -X GET 'http://localhost:8000/api/v1/roles/permissions/123e4567-e89b-12d3-a456-426614174000' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I'
```

### Valid Payload
Not applicable (GET request)

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"id":"123e4567-e89b-12d3-a456-426614174000","name":"Read Papers","description":"Permission to read papers","resource":"papers","action":"read","created_at":"2023-10-01T12:00:00Z","updated_at":"2023-10-01T12:00:00Z"}
```

Note: The response includes all fields as per the `PermissionResponse` schema. Timestamps and UUIDs will be dynamically generated based on actual data.