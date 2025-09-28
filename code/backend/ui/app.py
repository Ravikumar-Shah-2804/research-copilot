import streamlit as st
import requests
import json
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse, parse_qs

# Global config
st.set_page_config(page_title="Research Copilot API Tester", page_icon="🔬", layout="wide")

# Base URL configuration
if 'base_url' not in st.session_state:
    st.session_state.base_url = "http://localhost:8000"

if 'auth_token' not in st.session_state:
    st.session_state.auth_token = None

if 'openapi_schema' not in st.session_state:
    st.session_state.openapi_schema = None

def fetch_openapi_schema() -> Optional[Dict[str, Any]]:
    """Fetch OpenAPI schema from the API"""
    try:
        url = f"{st.session_state.base_url}/openapi.json"
        headers = {}
        if st.session_state.auth_token:
            headers["Authorization"] = f"Bearer {st.session_state.auth_token}"

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch OpenAPI schema: {str(e)}")
        return None

def fetch_current_user() -> Optional[Dict[str, Any]]:
    """Fetch current user details"""
    if not st.session_state.auth_token:
        return None
    try:
        url = f"{st.session_state.base_url}/api/v1/auth/me"
        headers = {"Authorization": f"Bearer {st.session_state.auth_token}"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch user details: {str(e)}")
        return None

def fetch_organization_details(org_id: str) -> Optional[Dict[str, Any]]:
    """Fetch organization details by ID"""
    if not st.session_state.auth_token:
        return None
    try:
        url = f"{st.session_state.base_url}/api/v1/organizations/{org_id}"
        headers = {"Authorization": f"Bearer {st.session_state.auth_token}"}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch organization details: {str(e)}")
        return None

def parse_openapi_schema(schema: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse OpenAPI schema into list of endpoints"""
    endpoints = []

    paths = schema.get('paths', {})
    for path, methods in paths.items():
        for method, details in methods.items():
            if method.lower() not in ['get', 'post', 'put', 'delete']:
                continue

            endpoint = {
                'path': path,
                'method': method.upper(),
                'summary': details.get('summary', ''),
                'description': details.get('description', ''),
                'parameters': details.get('parameters', []),
                'requestBody': details.get('requestBody', None),
                'responses': details.get('responses', {}),
                'tags': details.get('tags', [])
            }
            endpoints.append(endpoint)

    # Sort by tags, then by path
    endpoints.sort(key=lambda x: (x['tags'][0] if x['tags'] else '', x['path']))

    return endpoints

def generate_parameter_input(param: Dict[str, Any], key_prefix: str = "") -> Any:
    """Generate Streamlit input widget for a parameter"""
    param_name = param.get('name', '')
    param_type = param.get('schema', {}).get('type', 'string')
    param_format = param.get('schema', {}).get('format', '')
    required = param.get('required', False)
    description = param.get('description', '')
    default = param.get('schema', {}).get('default', None)

    label = f"{param_name}{' *' if required else ''}"
    if description:
        label += f" ({description})"

    input_key = f"{key_prefix}_{param_name}"

    if param_type == 'string':
        if param_format == 'date':
            return st.date_input(label, key=input_key, value=default)
        elif param_format == 'date-time':
            return st.text_input(label, key=input_key, value=default or "", placeholder="YYYY-MM-DDTHH:MM:SS")
        else:
            return st.text_input(label, key=input_key, value=default or "")
    elif param_type == 'integer':
        return st.number_input(label, key=input_key, value=default or 0, step=1)
    elif param_type == 'number':
        return st.number_input(label, key=input_key, value=default or 0.0, step=0.1)
    elif param_type == 'boolean':
        return st.checkbox(label, key=input_key, value=default or False)
    elif param_type == 'array':
        items_type = param.get('schema', {}).get('items', {}).get('type', 'string')
        if items_type == 'string':
            return st.text_area(label, key=input_key, value=default or "", placeholder="Comma-separated values").split(',')
        else:
            st.warning(f"Array type {items_type} not fully supported")
            return st.text_area(label, key=input_key, value=str(default) if default else "")
    else:
        return st.text_input(label, key=input_key, value=str(default) if default else "")

def generate_schema_input(schema: Dict[str, Any], key_prefix: str, required: bool = False, description: str = "") -> Any:
    """Recursively generate input for a JSON schema"""
    schema_type = schema.get('type', 'string')
    default = schema.get('default', None)
    enum_values = schema.get('enum', None)
    title = schema.get('title', '')

    label = title or key_prefix.split('_')[-1]
    if required:
        label += ' *'
    if description:
        label += f" ({description})"

    input_key = key_prefix

    # Check for API key creation and pre-populate organization details
    pre_populated_org_id = None
    if "api-keys" in key_prefix and schema_type == 'object' and st.session_state.auth_token:
        if 'user_org_id' not in st.session_state:
            user_data = fetch_current_user()
            if user_data and 'organization_id' in user_data:
                st.session_state.user_org_id = user_data['organization_id']
            else:
                st.session_state.user_org_id = None
        pre_populated_org_id = st.session_state.user_org_id

    if enum_values:
        # Use selectbox for enums
        options = enum_values
        default_index = 0
        if default in options:
            default_index = options.index(default)
        return st.selectbox(label, options, index=default_index, key=input_key)

    if schema_type == 'object':
        if schema.get('additionalProperties', False):
            # Dictionary/object with additional properties - use JSON textarea
            value = st.text_area(label, key=input_key, value=json.dumps(default or {}, indent=2), placeholder="JSON object")
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                st.error(f"Invalid JSON for {label}")
                return {}
        else:
            # Regular object
            properties = schema.get('properties', {})
            required_fields = set(schema.get('required', []))
            result = {}
            with st.expander(label, expanded=False):
                for prop_name, prop_schema in properties.items():
                    if prop_name == 'organization_id' and pre_populated_org_id:
                        # Pre-populate and hide the field
                        result[prop_name] = pre_populated_org_id
                        continue
                    prop_required = prop_name in required_fields
                    prop_desc = prop_schema.get('description', '')
                    value = generate_schema_input(prop_schema, f"{key_prefix}_{prop_name}", prop_required, prop_desc)
                    result[prop_name] = value
            return result

    elif schema_type == 'array':
        items_schema = schema.get('items', {})
        items_type = items_schema.get('type', 'string')

        if items_type == 'object':
            # Array of objects
            count_key = f"{key_prefix}_count"
            if count_key not in st.session_state:
                st.session_state[count_key] = 1

            count = st.number_input(f"Number of {label}", min_value=0, max_value=50, value=st.session_state[count_key], key=count_key, step=1)
            st.session_state[count_key] = count

            result = []
            for i in range(count):
                item_label = f"{label} #{i+1}"
                with st.expander(item_label, expanded=False):
                    item_value = generate_schema_input(items_schema, f"{key_prefix}_{i}", False, "")
                    result.append(item_value)
            return result
        else:
            # Simple array
            if items_type == 'string':
                value = st.text_area(label, key=input_key, value=default or "", placeholder="Comma-separated values")
                return [v.strip() for v in value.split(',') if v.strip()]
            else:
                st.warning(f"Array of {items_type} not fully supported, using text input")
                return st.text_input(label, key=input_key, value=str(default) if default else "")

    elif schema_type == 'string':
        format_type = schema.get('format', '')
        if format_type == 'date':
            return st.date_input(label, key=input_key, value=default)
        elif format_type == 'date-time':
            return st.text_input(label, key=input_key, value=default or "", placeholder="YYYY-MM-DDTHH:MM:SS")
        else:
            pattern = schema.get('pattern', '')
            if pattern:
                label += f" (pattern: {pattern})"
            return st.text_input(label, key=input_key, value=default or "")

    elif schema_type == 'integer':
        minimum = schema.get('minimum', None)
        maximum = schema.get('maximum', None)
        return st.number_input(label, key=input_key, value=default or 0, step=1, min_value=minimum, max_value=maximum)

    elif schema_type == 'number':
        minimum = schema.get('minimum', None)
        maximum = schema.get('maximum', None)
        return st.number_input(label, key=input_key, value=default or 0.0, step=0.1, min_value=minimum, max_value=maximum)

    elif schema_type == 'boolean':
        return st.checkbox(label, key=input_key, value=default or False)

    else:
        # Fallback
        return st.text_input(label, key=input_key, value=str(default) if default else "")


def generate_request_body_input(request_body: Dict[str, Any], key_prefix: str = "") -> Dict[str, Any]:
    """Generate input for request body"""
    if not request_body:
        return {}

    content = request_body.get('content', {})
    json_schema = content.get('application/json', {}).get('schema', {})

    if json_schema:
        st.subheader("Request Body")
        return generate_schema_input(json_schema, f"{key_prefix}_body", False, json_schema.get('description', ''))
    else:
        return {}

def make_api_request(method: str, endpoint: str, path_params: Dict[str, Any] = None,
                    query_params: Dict[str, Any] = None, body_data: Dict[str, Any] = None) -> Dict[str, Any]:
    """Make HTTP request with authentication"""
    # Replace path parameters
    url = endpoint
    if path_params:
        for param_name, param_value in path_params.items():
            url = url.replace(f"{{{param_name}}}", str(param_value))

    full_url = f"{st.session_state.base_url}{url}"

    headers = {"Content-Type": "application/json"}
    if st.session_state.auth_token:
        headers["Authorization"] = f"Bearer {st.session_state.auth_token}"

    # Debug log
    st.write(f"Debug: Sending {method.upper()} to {full_url}")
    st.write(f"Debug: body_data = {body_data}, type = {type(body_data)}")

    try:
        if method.upper() == "GET":
            response = requests.get(full_url, headers=headers, params=query_params, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(full_url, headers=headers, json=body_data, timeout=30)
        elif method.upper() == "PUT":
            response = requests.put(full_url, headers=headers, json=body_data, timeout=30)
        elif method.upper() == "DELETE":
            response = requests.delete(full_url, headers=headers, timeout=30)
        else:
            return {"error": "Unsupported method"}

        result = {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "url": str(response.url)
        }

        try:
            result["response"] = response.json()
        except:
            result["response"] = response.text

        return result

    except requests.exceptions.RequestException as e:
        return {"error": str(e)}

def main():
    # Sidebar configuration
    st.sidebar.title("🔬 API Tester")

    # Base URL input
    base_url = st.sidebar.text_input("Base URL", value=st.session_state.base_url, key="base_url_input")
    st.session_state.base_url = base_url

    # Authentication status
    if st.session_state.auth_token:
        st.sidebar.success("Authenticated")
        if st.sidebar.button("Logout"):
            st.session_state.auth_token = None
            st.session_state.openapi_schema = None
            st.rerun()
    else:
        st.sidebar.warning("Not authenticated")

    # Authentication section
    with st.sidebar.expander("Authentication", expanded=not bool(st.session_state.auth_token)):
        if not st.session_state.auth_token:
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")

            if st.button("Login"):
                if username and password:
                    # Special handling for login - send form data instead of JSON
                    full_url = f"{st.session_state.base_url}/api/v1/auth/token"
                    headers = {"Content-Type": "application/x-www-form-urlencoded"}
                    try:
                        response = requests.post(full_url, headers=headers, data={
                            "username": username,
                            "password": password
                        }, timeout=30)
                        result = {
                            "status_code": response.status_code,
                            "headers": dict(response.headers),
                            "url": str(response.url)
                        }
                        st.write(result)
                        try:
                            result["response"] = response.json()
                        except:
                            result["response"] = response.text
                        st.write(result["response"])
                    except requests.exceptions.RequestException as e:
                        result = {"error": str(e)}

                    if result.get("status_code") == 200 and "response" in result and "access_token" in result["response"]:
                        st.session_state.auth_token = result["response"]["access_token"]
                        st.success("Login successful!")
                        st.rerun()
                    elif "response" in result and isinstance(result["response"], dict) and "detail" in result["response"]:
                        st.error(f"Login failed: {result['response']['detail']}")
                    else:
                        error_msg = result.get('error', 'Unknown error')
                        st.error(f"Login failed: {error_msg}")
                else:
                    st.error("Please enter username and password")

    # Fetch OpenAPI schema
    if st.sidebar.button("Load API Schema") or st.session_state.openapi_schema is None:
        with st.spinner("Fetching API schema..."):
            schema = fetch_openapi_schema()
            if schema:
                st.session_state.openapi_schema = schema
                st.sidebar.success("Schema loaded successfully")
            else:
                st.sidebar.error("Failed to load schema")

    # Main content
    st.title("🔬 Research Copilot API Tester")

    if not st.session_state.openapi_schema:
        st.info("Please load the API schema from the sidebar to begin testing.")
        return

    # Parse endpoints
    endpoints = parse_openapi_schema(st.session_state.openapi_schema)

    # Group endpoints by tags
    tagged_endpoints = {}
    for endpoint in endpoints:
        tag = endpoint['tags'][0] if endpoint['tags'] else 'General'
        if tag not in tagged_endpoints:
            tagged_endpoints[tag] = []
        tagged_endpoints[tag].append(endpoint)

    # Sidebar navigation
    selected_tag = st.sidebar.selectbox("Select API Section", list(tagged_endpoints.keys()))

    st.header(f"📋 {selected_tag}")

    # Display endpoints for selected tag
    for endpoint in tagged_endpoints[selected_tag]:
        with st.expander(f"{endpoint['method']} {endpoint['path']}", expanded=False):
            if endpoint['summary']:
                st.markdown(f"**{endpoint['summary']}**")
            if endpoint['description']:
                st.markdown(endpoint['description'])

            # Separate parameters by location
            path_params = [p for p in endpoint['parameters'] if p.get('in') == 'path']
            query_params = [p for p in endpoint['parameters'] if p.get('in') == 'query']
            header_params = [p for p in endpoint['parameters'] if p.get('in') == 'header']

            # Input form
            col1, col2 = st.columns([2, 1])

            with col1:
                st.subheader("Parameters")

                # Path parameters
                path_param_values = {}
                if path_params:
                    st.markdown("**Path Parameters**")
                    for param in path_params:
                        path_param_values[param['name']] = generate_parameter_input(param, f"path_{endpoint['path']}_{endpoint['method']}")

                # Query parameters
                query_param_values = {}
                if query_params:
                    st.markdown("**Query Parameters**")
                    for param in query_params:
                        query_param_values[param['name']] = generate_parameter_input(param, f"query_{endpoint['path']}_{endpoint['method']}")

                # Request body
                body_data = generate_request_body_input(endpoint.get('requestBody'), f"body_{endpoint['path']}_{endpoint['method']}")

            with col2:
                st.subheader("Actions")

                # Execute button
                button_key = f"execute_{endpoint['path']}_{endpoint['method']}"
                if st.button(f"Execute {endpoint['method']}", key=button_key):
                    with st.spinner("Executing request..."):
                        result = make_api_request(
                            endpoint['method'],
                            endpoint['path'],
                            path_params=path_param_values,
                            query_params=query_param_values,
                            body_data=body_data
                        )

                        # Store result in session state for display
                        result_key = f"result_{endpoint['path']}_{endpoint['method']}"
                        st.session_state[result_key] = result

                # Display result
                result_key = f"result_{endpoint['path']}_{endpoint['method']}"
                if result_key in st.session_state:
                    result = st.session_state[result_key]

                    st.subheader("Response")

                    # Status
                    if "status_code" in result:
                        if result["status_code"] < 300:
                            st.success(f"Status: {result['status_code']}")
                        else:
                            st.error(f"Status: {result['status_code']}")

                    # URL
                    if "url" in result:
                        st.code(f"URL: {result['url']}", language=None)

                    # Response body
                    if "response" in result:
                        st.markdown("**Response Body:**")
                        if isinstance(result["response"], dict):
                            st.json(result["response"])
                        else:
                            st.code(result["response"], language=None)

                    # Error
                    if "error" in result:
                        st.error(f"Error: {result['error']}")

                    # Headers
                    if "headers" in result:
                        with st.expander("Response Headers"):
                            st.json(result["headers"])

    # Footer
    st.markdown("---")
    st.markdown("*Research Copilot API Tester - Dynamic OpenAPI Integration*")

if __name__ == "__main__":
    main()