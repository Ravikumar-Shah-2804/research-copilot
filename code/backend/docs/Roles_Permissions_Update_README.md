# Roles Permissions Update Endpoint Documentation

## Endpoint Overview

### URL Path
`/api/v1/roles/permissions/{permission_id}`

### HTTP Method
PUT

### Description
This endpoint allows superusers to update an existing permission by its ID.

### Dependencies
- Relies on `AsyncSession` from `get_db` for database operations.
- Calls `role_service.update_permission` (from `src/services/role.py`) to perform the update logic.

## Authentication

### Requirements
- Authentication is mandatory and handled via the `get_current_active_user` dependency (from `src/services/auth.py`).
- The user must provide a valid JWT token in the `Authorization` header (format: `Bearer <token>`).
- The token is decoded and verified to ensure the user is active.

### Required Headers
- `Authorization`: Bearer token (required for authentication; the token is validated via `get_current_active_user` dependency).

## Authorization

### Requirements
- Only superusers (`current_user.is_superuser` is `True`) can update permissions.

## Request

### Request Body Schema
The request body must conform to the `PermissionUpdate` schema (from `src/schemas/role.py`). All fields are optional and validated using Pydantic.

- **name** (str, optional): The name of the permission. Constraints: minimum length 1, maximum length 100.
- **description** (str, optional): A description of the permission.
- **resource** (str, optional): The resource associated with the permission. Constraints: minimum length 1, maximum length 100.
- **action** (str, optional): The action for the permission. Constraints: minimum length 1, maximum length 50.

### Path Parameters
- **permission_id** (UUID, required): The unique identifier of the permission to update.

### Content-Type
- `application/json`

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
  "name": "Read Papers Updated",
  "description": "Updated permission to read papers",
  "resource": "papers",
  "action": "read",
  "created_at": "2023-10-01T12:00:00Z",
  "updated_at": "2023-10-02T12:00:00Z"
}
```

## Error Responses

### 403 Forbidden
- **Status Code**: 403
- **Message**: "Only superusers can update permissions"
- **Condition**: Triggered if the authenticated user is not a superuser.

### 400 Bad Request
- **Status Code**: 400
- **Message**: Dynamic string based on the exception from `role_service.update_permission` (e.g., validation errors, database issues).
- **Condition**: Any exception raised during permission update in the service layer.

## Testing Example

### Example Command
```bash
curl -X PUT 'http://localhost:8000/api/v1/roles/permissions/123e4567-e89b-12d3-a456-426614174000' \
  -H 'Content-Type: application/json' \
  -H 'Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiIsImV4cCI6MTc1ODg3MDc4OH0.GrXDnxCPAYJxm3rG33_0bP3hMJXTu5FX68uHHF1WV1I' \
  -d '{"name": "Read Papers Updated", "description": "Updated permission to read papers"}'
```

### Valid Payload
```json
{
  "name": "Read Papers Updated",
  "description": "Updated permission to read papers"
}
```

### Expected Output
```
StatusCode: 200
StatusDescription: OK
Content: {"id":"123e4567-e89b-12d3-a456-426614174000","name":"Read Papers Updated","description":"Updated permission to read papers","resource":"papers","action":"read","created_at":"2023-10-01T12:00:00Z","updated_at":"2023-10-02T12:00:00Z"}
```

Note: The full JSON response includes all fields as per the `PermissionResponse` schema. Timestamps and UUIDs will be dynamically generated.