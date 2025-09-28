# Enterprise Paper Ingestion DAG

This directory contains the enterprise-grade Airflow DAG for automated paper ingestion in the research-copilot system.

## Overview

The `enterprise_paper_ingestion` DAG extends the basic arxiv-paper-curator pipeline with enterprise features:

- **Organization-based access control**: Papers are assigned to specific organizations with proper isolation
- **Distributed processing**: Utilizes multiple workers for parallel processing of papers
- **Comprehensive monitoring**: Integrated Prometheus metrics and detailed pipeline monitoring
- **Enterprise security**: API key validation, audit logging, and compliance features
- **Multi-tenant architecture**: Supports multiple organizations with resource limits and quotas

## Architecture

### DAG Structure

```
enterprise_paper_ingestion
├── enterprise_setup_validation      # Environment and dependency validation
├── security_access_validation       # Security checks and access control
├── get_active_organizations         # Retrieve eligible organizations
├── check_organizations_available    # Branch based on available organizations
├── distributed_paper_fetch          # Parallel paper fetching by organization
├── organization_paper_assignment    # Assign papers to organizations
├── distributed_processing_indexing  # Parallel processing and indexing
├── enterprise_indexing              # Organization-aware indexing
├── enterprise_monitoring_reporting  # Comprehensive monitoring
├── enterprise_cleanup_audit         # Cleanup and audit logging
├── pipeline_success_notification    # Success notifications
└── no_organizations_skip           # Skip when no organizations available
```

### Key Components

#### 1. Setup & Validation (`setup.py`)
- Validates database connectivity
- Checks OpenSearch cluster health
- Verifies arXiv API access
- Confirms organization service availability
- Validates monitoring system

#### 2. Security & Access Control (`security.py`)
- API key authentication
- Organization permission validation
- Rate limiting checks
- Audit logging setup
- Data encryption validation

#### 3. Organization Management (`organization.py`)
- Retrieves active organizations
- Assigns papers based on capacity and priority
- Implements organization-based access control
- Tracks organization-specific metrics

#### 4. Distributed Fetching (`fetching.py`)
- Concurrent paper fetching across organizations
- Implements organization-specific limits
- Handles API rate limiting
- Provides detailed fetch metrics

#### 5. Distributed Processing (`distributed.py`)
- Parallel PDF processing using ProcessPoolExecutor
- Text chunking and embedding generation
- Organization-aware processing
- Resource-efficient batch processing

#### 6. Enterprise Indexing (`indexing.py`)
- Organization-isolated indexing
- Hybrid search index management
- Chunk embedding and storage
- Index health monitoring

#### 7. Monitoring & Reporting (`monitoring.py`)
- Comprehensive pipeline metrics
- Organization performance analysis
- Error categorization and alerting
- Performance recommendations
- System health monitoring

#### 8. Cleanup & Audit (`cleanup.py`)
- Automated cleanup of temporary files
- Database record maintenance
- Comprehensive audit trail creation
- Retention policy enforcement

#### 9. Notifications (`notifications.py`)
- Email notifications for pipeline events
- Monitoring alerts for failures
- Configurable notification channels
- Priority-based alerting

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/research_copilot

# OpenSearch
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200

# arXiv API
ARXIV_BASE_URL=http://export.arxiv.org/api/query

# Security
RESEARCH_COPILOT_API_KEY=your-api-key-here
ENCRYPTION_ENABLED=true
ENCRYPTION_KEY=your-encryption-key

# Notifications
PIPELINE_NOTIFICATION_EMAILS=admin@example.com,team@example.com
```

### DAG Configuration

Key configuration parameters in the DAG:

```python
ENTERPRISE_CONFIG = {
    "max_organizations_per_run": 10,        # Maximum organizations to process
    "papers_per_organization_limit": 500,   # Papers per organization limit
    "distributed_workers": 4,               # Number of parallel workers
    "monitoring_enabled": True,             # Enable monitoring
    "audit_logging": True,                  # Enable audit logging
    "security_validation": True,            # Enable security checks
    "cleanup_retention_days": 30,           # Data retention period
}
```

## Usage

### Running the DAG

The DAG runs automatically on a daily schedule at midnight UTC. You can also trigger it manually:

```bash
# Trigger manually via Airflow CLI
airflow dags trigger enterprise_paper_ingestion

# Unpause the DAG
airflow dags unpause enterprise_paper_ingestion
```

### Monitoring

Monitor the DAG execution through:

1. **Airflow UI**: View task status, logs, and XCom values
2. **Prometheus Metrics**: Access performance and system metrics
3. **Organization Dashboard**: Monitor per-organization ingestion stats
4. **Audit Logs**: Review comprehensive audit trails

### Troubleshooting

#### Common Issues

1. **No Organizations Available**
   - Check organization service connectivity
   - Verify organizations are active and have ingestion permissions
   - Review security validation logs

2. **Fetching Failures**
   - Check arXiv API connectivity
   - Verify rate limiting hasn't been exceeded
   - Review network connectivity

3. **Indexing Failures**
   - Check OpenSearch cluster health
   - Verify index permissions
   - Review disk space and memory usage

4. **Processing Timeouts**
   - Increase worker count in configuration
   - Check system resources
   - Review paper processing complexity

#### Logs

Access logs through:
- Airflow task logs in the UI
- Application logs in `logs/app.log`
- Audit logs in the database
- Monitoring system dashboards

## Enterprise Features

### Multi-Tenant Architecture

- **Organization Isolation**: Each organization's data is logically separated
- **Resource Quotas**: Configurable limits per organization
- **Priority Scheduling**: Organizations processed based on priority scores
- **Access Control**: Role-based permissions for ingestion operations

### Security & Compliance

- **API Key Authentication**: Secure access to ingestion endpoints
- **Audit Logging**: Comprehensive tracking of all operations
- **Data Encryption**: Optional encryption for sensitive data
- **Rate Limiting**: Protection against abuse and resource exhaustion

### Monitoring & Observability

- **Real-time Metrics**: Prometheus integration for system monitoring
- **Performance Analytics**: Detailed pipeline performance insights
- **Error Tracking**: Categorized error analysis and alerting
- **Health Checks**: Automated system health validation

### Scalability

- **Distributed Processing**: Horizontal scaling with multiple workers
- **Batch Processing**: Efficient handling of large paper volumes
- **Resource Management**: Automatic resource allocation and cleanup
- **Load Balancing**: Intelligent distribution across organizations

## Development

### Adding New Features

1. Create new modules in `enterprise_ingestion/`
2. Update the main DAG with new tasks
3. Add appropriate error handling and logging
4. Update monitoring and metrics collection
5. Test thoroughly in development environment

### Testing

```bash
# Syntax check
python -m py_compile airflow/dags/enterprise_paper_ingestion.py

# Import test (in proper environment)
python -c "from dags.enterprise_paper_ingestion import dag"

# Unit tests
pytest tests/dags/test_enterprise_ingestion.py
```

## Support

For issues or questions:
1. Check the troubleshooting section above
2. Review Airflow and application logs
3. Contact the development team
4. Check the research-copilot documentation