# Production Deployment Guide

This guide explains how to deploy the Research Copilot application in production using Docker Compose.

## Prerequisites

- Docker and Docker Compose installed
- SSL certificates for your domain
- A domain name pointing to your server

## Setup

1. **Clone the repository** and navigate to the project root.

2. **SSL Certificates**:
   - Obtain SSL certificates for your domain (e.g., using Let's Encrypt or your CA)
   - Place the certificates in the `./ssl/` directory:
     - `fullchain.pem` - Full certificate chain
     - `privkey.pem` - Private key

3. **Environment Variables**:
   - Copy `.env.prod` to `.env.prod` (if not already)
   - Fill in all the required values with your actual secrets:
     - Database passwords
     - JWT secrets
     - API keys
     - Domain information

4. **Update Domain Configuration**:
   - In `nginx-prod.conf`, replace `yourdomain.com` with your actual domain
   - In `docker-compose.prod.yml`, update the `NEXT_PUBLIC_API_BASE_URL` build arg
   - In `.env.prod`, set `PRODUCTION_DOMAIN` and `API_BASE_URL`

## Deployment

1. **Build and start the services**:
   ```bash
   docker-compose -f docker-compose.prod.yml up -d --build
   ```

2. **Verify deployment**:
   - Check that all services are running: `docker-compose -f docker-compose.prod.yml ps`
   - Visit your domain in a browser
   - API should be accessible at `https://yourdomain.com/api`

## Services Included

- **Backend**: FastAPI application (Python)
- **Frontend**: Next.js application served via Nginx
- **Nginx**: Reverse proxy with SSL termination and load balancing
- **Database**: PostgreSQL
- **Redis**: Caching
- **OpenSearch**: Search engine
- **Langfuse**: LLM observability
- **Prometheus**: Metrics collection
- **Grafana**: Monitoring dashboard

## Load Balancing

The current configuration includes basic load balancing setup. To scale the backend:

1. Add multiple backend services in `docker-compose.prod.yml`:
   ```yaml
   backend1:
     # ... same config
   backend2:
     # ... same config
   ```

2. Update the `upstream backend` block in `nginx-prod.conf`:
   ```nginx
   upstream backend {
       server backend1:8000;
       server backend2:8000;
   }
   ```

## Security Notes

- All secrets are loaded from the `.env.prod` file
- SSL/TLS is enforced with HTTP redirect to HTTPS
- Security headers are configured in Nginx
- Database passwords and API keys are externalized

## Monitoring

- Access Grafana at `http://localhost:3001` (internal only, not exposed)
- Prometheus metrics at `http://localhost:9090` (internal)
- Application logs are available in `./backend/logs/`

## Troubleshooting

- Check service logs: `docker-compose -f docker-compose.prod.yml logs <service_name>`
- Verify SSL certificates are correctly mounted
- Ensure domain DNS points to your server
- Check firewall settings for ports 80 and 443