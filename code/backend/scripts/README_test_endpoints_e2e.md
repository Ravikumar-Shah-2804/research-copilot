# Comprehensive E2E API Testing Script

This document provides detailed information about the `test_endpoints_e2e.py` script, which performs comprehensive end-to-end testing of all Research Copilot API endpoints.

## Overview

The E2E testing script systematically tests all API endpoints across multiple categories:

- **Authentication**: User registration, login, token management, logout
- **User Management**: Profile management, organization operations
- **Paper Operations**: CRUD operations, file uploads, search
- **Search Operations**: Text search, hybrid search, RAG queries, suggestions
- **RAG Operations**: Generation, streaming, batch processing, model management
- **Analytics**: Performance metrics, search analytics, usage tracking, audit trails
- **Ingestion**: ArXiv ingestion, PDF processing, job management
- **Admin Operations**: System stats, user management, cache operations, logs
- **Roles & Permissions**: Role management, permission assignment
- **API Keys**: Key generation, management, usage tracking
- **Health Checks**: System health, database connectivity, service status
- **Audit Operations**: Event logging, trail retrieval

## Features

### Modular Architecture
- **Test Suites**: Each endpoint category has a dedicated test suite class
- **Base Classes**: Common functionality shared across test suites
- **Extensibility**: Easy to add new test suites or modify existing ones

### Authentication Management
- **Token Handling**: Automatic JWT token acquisition and management
- **Multi-User Support**: Support for different user types (regular, admin)
- **Session Management**: Proper token refresh and logout handling

### Test Data Management
- **Automated Setup**: Creates test users, papers, and other resources
- **Cleanup**: Automatically removes test data after execution
- **Configurable**: Adjustable number of test entities via command line

### Environment Support
- **Multiple Environments**: dev, staging, prod, test configurations
- **Environment-Specific Settings**: URLs, timeouts, rate limits per environment
- **Mock Services**: Optional mock service integration for testing

### Performance Monitoring
- **Response Time Tracking**: Measures and logs response times
- **Success Rate Calculation**: Tracks request success/failure rates
- **Detailed Metrics**: Comprehensive performance statistics
- **Exportable Reports**: JSON export of performance data

### Observability Integration
- **Metrics Collection**: Integration with existing metrics testing
- **Monitoring Scripts**: Tests observability script execution
- **Dashboard Validation**: Checks Grafana dashboard accessibility

### Error Handling
- **Graceful Failures**: Continues testing even when individual tests fail
- **Detailed Logging**: Comprehensive error reporting and debugging
- **Schema Validation**: Validates API response formats

## Installation & Setup

### Prerequisites

```bash
# Python 3.8+
python --version

# Required packages (install via pip or poetry)
pip install httpx pydantic pytest

# For the full Research Copilot environment
# Follow the main project setup instructions
```

### Environment Variables

Set these environment variables for proper authentication:

```bash
export API_BASE_URL="http://localhost:8000"
export ADMIN_EMAIL="admin@example.com"
export ADMIN_PASSWORD="AdminPass123!"
export TEST_USER_EMAIL="testuser@example.com"
export TEST_USER_PASSWORD="TestPass123!"
export JWT_SECRET_KEY="your-secret-key"
```

## Usage

### Basic Usage

```bash
# Run all tests in development environment
python scripts/test_endpoints_e2e.py --env dev

# Run with verbose logging
python scripts/test_endpoints_e2e.py --env dev --verbose

# Run in staging environment
python scripts/test_endpoints_e2e.py --env staging
```

### Advanced Usage

```bash
# Production testing with performance metrics
python scripts/test_endpoints_e2e.py --env prod --performance --metrics

# Custom configuration
python scripts/test_endpoints_e2e.py \
  --env dev \
  --url "http://localhost:8000" \
  --users 10 \
  --papers 20 \
  --timeout 60 \
  --verbose

# Test environment with observability
python scripts/test_endpoints_e2e.py \
  --env test \
  --observability \
  --metrics \
  --performance
```

### Command Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--env` | Environment (dev/staging/prod/test) | dev |
| `--url` | API base URL | Environment-specific |
| `--verbose`, `-v` | Enable verbose logging | False |
| `--performance` | Enable performance metrics | False |
| `--metrics` | Enable detailed metrics collection | False |
| `--observability` | Enable observability integration tests | False |
| `--users` | Number of test users to create | 3 |
| `--papers` | Number of test papers to create | 5 |
| `--timeout` | Request timeout in seconds | 30 |
| `--retries` | Max retries per request | 3 |
| `--cleanup` | Force cleanup of test data | False |

## Test Structure

### Test Suites

Each test suite focuses on a specific API category:

1. **AuthTestSuite**: Authentication endpoints
2. **PapersTestSuite**: Paper CRUD operations
3. **SearchTestSuite**: Search functionality
4. **RAGTestSuite**: RAG operations
5. **AdminTestSuite**: Administrative functions
6. **IngestionTestSuite**: Data ingestion
7. **AnalyticsTestSuite**: Analytics and reporting
8. **HealthTestSuite**: Health checks
9. **RolesTestSuite**: Role management
10. **APIKeysTestSuite**: API key management
11. **AuditTestSuite**: Audit operations

### Test Flow

1. **Setup Phase**
   - Environment configuration
   - Test data creation
   - Authentication setup

2. **Execution Phase**
   - Sequential test suite execution
   - Metrics collection
   - Error handling

3. **Cleanup Phase**
   - Test data removal
   - Resource cleanup
   - Report generation

## Output & Reporting

### Console Output

The script provides real-time feedback:

```
Starting comprehensive E2E API tests...
Environment: dev
Base URL: http://localhost:8000

==================================================
Running AuthTestSuite
==================================================
✓ User registration successful
✓ User login successful, tokens stored
✓ Token list retrieved successfully
✓ User profile retrieved successfully
✓ Logout all devices successful
AuthTestSuite: PASSED

==================================================
Running PapersTestSuite
==================================================
✓ Paper created successfully with ID: 123e4567-...
✓ Paper retrieval successful
✓ Paper update successful
✓ Paper deletion successful
✓ Paper listing successful
✓ Paper search successful
PapersTestSuite: PASSED
```

### Log Files

- **Console Logs**: Real-time output with test progress
- **Detailed Logs**: `e2e_test_YYYYMMDD_HHMMSS.log` with full debug information
- **Metrics Export**: `e2e_metrics_YYYYMMDD_HHMMSS.json` with performance data

### Metrics Report

```
E2E TEST REPORT
============================================================
Test Suites: 11/11 passed
Overall Status: PASSED

Suite Results:
  ✓ PASS AuthTestSuite
  ✓ PASS PapersTestSuite
  ✓ PASS SearchTestSuite
  ✓ PASS RAGTestSuite
  ✓ PASS AdminTestSuite
  ✓ PASS IngestionTestSuite
  ✓ PASS AnalyticsTestSuite
  ✓ PASS HealthTestSuite
  ✓ PASS RolesTestSuite
  ✓ PASS APIKeysTestSuite
  ✓ PASS AuditTestSuite

Performance Metrics:
  Total Duration: 45.67s
  Total Requests: 247
  Success Rate: 98.4%
  Avg Response Time: 0.185s
  Errors: 4

Environment: dev
Features: full_api, debug_mode, mock_services
============================================================
```

## Environment Configurations

### Development (dev)
- **URL**: `http://localhost:8000`
- **Timeout**: 30 seconds
- **Rate Limit**: 60 requests/minute
- **Features**: Full API, debug mode, mock services

### Staging (staging)
- **URL**: `https://api-staging.research-copilot.com`
- **Timeout**: 60 seconds
- **Rate Limit**: 30 requests/minute
- **Features**: Full API, monitoring, rate limiting

### Production (prod)
- **URL**: `https://api.research-copilot.com`
- **Timeout**: 30 seconds
- **Rate Limit**: 20 requests/minute
- **Features**: Full API, monitoring, security, rate limiting

### Test (test)
- **URL**: `http://testserver`
- **Timeout**: 10 seconds
- **Rate Limit**: 100 requests/minute
- **Features**: Full API, mock services, fast mode

## Troubleshooting

### Common Issues

#### Authentication Failures
```bash
# Check environment variables
echo $ADMIN_EMAIL
echo $ADMIN_PASSWORD

# Verify API is running
curl -X GET http://localhost:8000/health
```

#### Connection Timeouts
```bash
# Increase timeout
python scripts/test_endpoints_e2e.py --timeout 120

# Check network connectivity
ping your-api-host.com
```

#### Test Data Issues
```bash
# Force cleanup
python scripts/test_endpoints_e2e.py --cleanup

# Reduce test data size
python scripts/test_endpoints_e2e.py --users 1 --papers 2
```

#### Permission Errors
```bash
# Run with appropriate user
sudo -u www-data python scripts/test_endpoints_e2e.py

# Check file permissions
ls -la scripts/test_endpoints_e2e.py
```

### Debug Mode

Enable verbose logging for detailed debugging:

```bash
python scripts/test_endpoints_e2e.py --verbose --env dev
```

This will show:
- Individual request/response details
- Authentication token flows
- Test data creation/deletion
- Performance timings per request

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: E2E API Tests
on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  e2e-tests:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Setup Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.9'
    - name: Install dependencies
      run: |
        pip install -r requirements.txt
    - name: Run E2E Tests
      env:
        API_BASE_URL: ${{ secrets.API_BASE_URL }}
        ADMIN_EMAIL: ${{ secrets.ADMIN_EMAIL }}
        ADMIN_PASSWORD: ${{ secrets.ADMIN_PASSWORD }}
      run: |
        python scripts/test_endpoints_e2e.py --env staging --metrics --performance
```

### Docker Integration

```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
CMD ["python", "scripts/test_endpoints_e2e.py", "--env", "prod", "--observability"]
```

## Extending the Script

### Adding New Test Suites

1. Create a new class inheriting from `BaseTestSuite`
2. Implement the `run_tests()` method
3. Add the suite to the `test_suites` list in `TestEndpointsE2E.run_all_tests()`

```python
class CustomTestSuite(BaseTestSuite):
    async def run_tests(self) -> bool:
        self.logger.info("Running custom tests...")
        # Your test logic here
        return True
```

### Adding New Environments

Update the `EnvironmentConfig.configs` dictionary:

```python
"custom": {
    "base_url": "https://custom-api.example.com",
    "timeout": 45,
    "rate_limits": {"requests_per_minute": 50},
    "features": ["full_api", "custom_feature"]
}
```

### Custom Metrics

Extend the `TestMetrics` class to track custom metrics:

```python
def record_custom_metric(self, name: str, value: float):
    if name not in self.custom_metrics:
        self.custom_metrics[name] = []
    self.custom_metrics[name].append(value)
```

## Performance Considerations

### Optimizing Test Execution

- **Parallel Execution**: Consider running test suites in parallel for faster execution
- **Selective Testing**: Use `--users` and `--papers` to reduce test data
- **Mock Services**: Use test environment with mock services for faster runs
- **Rate Limiting**: Respect API rate limits to avoid throttling

### Memory Usage

- **Large Test Data**: Monitor memory usage with many test users/papers
- **Cleanup**: Ensure proper cleanup to prevent resource leaks
- **Batch Operations**: Use batch operations where available

### Network Considerations

- **Timeouts**: Adjust timeouts based on network conditions
- **Retries**: Configure appropriate retry logic for network issues
- **Concurrent Requests**: Limit concurrent requests to avoid overwhelming the API

## Security Considerations

### Credential Management

- **Environment Variables**: Never hardcode credentials
- **Secret Management**: Use secure secret management systems
- **Token Handling**: Properly handle and cleanup authentication tokens

### Data Privacy

- **Test Data**: Use realistic but non-sensitive test data
- **Cleanup**: Ensure complete removal of test data
- **Audit Logs**: Monitor and review test activities in audit logs

### API Security

- **Rate Limiting**: Respect API rate limits
- **Authentication**: Properly authenticate all requests
- **Authorization**: Test appropriate permission levels

## Contributing

### Code Style

Follow the existing code style:
- Use type hints for all function parameters and return values
- Include comprehensive docstrings
- Use logging instead of print statements
- Handle exceptions appropriately

### Testing

- Add unit tests for new functionality
- Update integration tests as needed
- Test in all supported environments

### Documentation

- Update this README for any new features
- Add inline code comments for complex logic
- Include examples for new command-line options

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review the detailed logs: `e2e_test_*.log`
3. Check the metrics export: `e2e_metrics_*.json`
4. Review the main project documentation
5. Create an issue in the project repository

## Changelog

### Version 1.0.0
- Initial comprehensive E2E testing implementation
- Support for all major API endpoint categories
- Environment-specific configurations
- Performance metrics and observability integration
- Modular test suite architecture
- Comprehensive error handling and reporting