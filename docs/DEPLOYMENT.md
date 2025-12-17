# Deployment Guide

**Purpose**: Document deployment procedures, infrastructure setup, and production operations.

---

## Overview

**Deployment Strategy**: Blue-Green | Rolling | Canary | Recreate

**Hosting**: Cloud Provider | On-Premise | Hybrid | Serverless

**CI/CD**: Automated | Manual | Hybrid

---

## Prerequisites

### Required Accounts & Access

- [ ] Cloud provider account (AWS | Azure | GCP)
- [ ] Domain name and DNS access
- [ ] SSL certificate
- [ ] CI/CD platform access (GitHub Actions | GitLab CI | Jenkins)
- [ ] Production database access
- [ ] Monitoring/logging service access

### Required Tools

- [ ] Cloud CLI (aws-cli | gcloud | az)
- [ ] Infrastructure as Code tool (Terraform | CloudFormation)
- [ ] Container tools (Docker | kubectl)
- [ ] Database migration tool

---

## Environments

### Development

**Purpose**: Local development and testing

**Access**: All developers

**Infrastructure**: Local Docker containers | Dev cloud resources

**Database**: Local SQLite | Dev database instance

**Deployment**: Manual, developer-initiated

---

### Staging

**Purpose**: Pre-production testing and QA

**Access**: Developers, QA team, stakeholders

**Infrastructure**: Mirrors production (scaled down)

**Database**: Staging database (anonymized production data)

**Deployment**: Automated on merge to `develop` branch

**URL**: `https://staging.example.com`

---

### Production

**Purpose**: Live user-facing environment

**Access**: Limited (DevOps, senior engineers)

**Infrastructure**: Production-grade, highly available

**Database**: Production database with backups

**Deployment**: Automated on merge to `main` branch (with approval)

**URL**: `https://example.com`

---

## Infrastructure Setup

### Cloud Infrastructure (Example: AWS)

#### 1. Initial Setup

```bash
# Configure AWS CLI
aws configure

# Set default region
export AWS_DEFAULT_REGION=us-east-1

# Create S3 bucket for Terraform state
aws s3 mb s3://my-terraform-state-bucket

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket my-terraform-state-bucket \
  --versioning-configuration Status=Enabled
```

#### 2. Infrastructure as Code

**Terraform Structure**:

```
infrastructure/
├── terraform/
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── environments/
│   │   ├── staging.tfvars
│   │   └── production.tfvars
│   └── modules/
│       ├── networking/
│       ├── compute/
│       └── database/
```

**Deploy Infrastructure**:

```bash
cd infrastructure/terraform

# Initialize Terraform
terraform init

# Plan changes
terraform plan -var-file=environments/production.tfvars

# Apply changes
terraform apply -var-file=environments/production.tfvars
```

---

## Container Deployment

### Docker Setup

**Dockerfile**:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**Build and Push**:

```bash
# Build image
docker build -t myapp:v1.0.0 .

# Tag for registry
docker tag myapp:v1.0.0 registry.example.com/myapp:v1.0.0

# Push to registry
docker push registry.example.com/myapp:v1.0.0
```

---

### Kubernetes Deployment (if applicable)

**Deployment Manifest**:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    metadata:
      labels:
        app: myapp
    spec:
      containers:
        - name: myapp
          image: registry.example.com/myapp:v1.0.0
          ports:
            - containerPort: 8000
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  name: myapp-secrets
                  key: database-url
```

**Deploy to Kubernetes**:

```bash
# Apply configuration
kubectl apply -f k8s/deployment.yaml

# Check status
kubectl get pods

# View logs
kubectl logs -f deployment/myapp
```

---

## Database Deployment

### Migrations

**Run Database Migrations**:

```bash
# Python/Alembic example
alembic upgrade head

# Node.js/Knex example
npx knex migrate:latest

# Go/golang-migrate example
migrate -path ./migrations -database ${DATABASE_URL} up
```

### Backup Before Migration

```bash
# PostgreSQL backup
pg_dump -h localhost -U user -d database > backup_$(date +%Y%m%d_%H%M%S).sql

# MySQL backup
mysqldump -h localhost -u user -p database > backup_$(date +%Y%m%d_%H%M%S).sql
```

---

## CI/CD Pipeline

### GitHub Actions Example

**.github/workflows/deploy.yml**:

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          npm install
          npm test

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build Docker image
        run: |
          docker build -t myapp:${{ github.sha }} .
          docker tag myapp:${{ github.sha }} registry.example.com/myapp:latest
      - name: Push to registry
        run: docker push registry.example.com/myapp:latest

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        run: |
          kubectl set image deployment/myapp myapp=registry.example.com/myapp:latest
          kubectl rollout status deployment/myapp
```

---

## Deployment Process

### Manual Deployment Steps

1. **Pre-Deployment Checklist**
   - [ ] All tests passing
   - [ ] Code reviewed and approved
   - [ ] Database migrations tested
   - [ ] Rollback plan prepared
   - [ ] Stakeholders notified

2. **Deploy Application**

   ```bash
   # Pull latest code
   git pull origin main

   # Build application
   make build

   # Run database migrations
   make migrate

   # Deploy application
   make deploy
   ```

3. **Post-Deployment Verification**
   - [ ] Health check endpoint responding
   - [ ] Key features functioning
   - [ ] No error spikes in logs
   - [ ] Metrics look normal
   - [ ] Update status page

---

## Rollback Procedures

### Quick Rollback

**Container-Based**:

```bash
# Rollback to previous version
kubectl rollout undo deployment/myapp

# Rollback to specific revision
kubectl rollout undo deployment/myapp --to-revision=2
```

**Traditional Server**:

```bash
# Revert to previous release
cd /app/releases/
ln -sfn previous current
systemctl restart myapp
```

### Database Rollback

```bash
# Alembic (Python)
alembic downgrade -1

# Knex (Node.js)
npx knex migrate:rollback

# golang-migrate (Go)
migrate -path ./migrations -database ${DATABASE_URL} down 1
```

---

## Monitoring & Health Checks

### Health Check Endpoint

**Example** (`/health`):

```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "version": "1.0.0",
  "checks": {
    "database": "ok",
    "cache": "ok",
    "external_api": "ok"
  }
}
```

### Monitoring Setup

**Metrics to Monitor**:

- Response time (p50, p95, p99)
- Error rate
- Request rate
- CPU/Memory usage
- Database connection pool
- Queue depth

**Alerting Thresholds**:

- Error rate > 1%
- p99 response time > 1s
- CPU usage > 80%
- Memory usage > 85%
- Disk usage > 90%

**Related Documentation**: See `docs/OBSERVABILITY.md` for monitoring details

---

## Security Considerations

### Secrets Management

**Do NOT**:

- ❌ Commit secrets to version control
- ❌ Hardcode API keys or passwords
- ❌ Share secrets in plain text

**Do**:

- ✅ Use environment variables
- ✅ Use secrets management service (AWS Secrets Manager, HashiCorp Vault)
- ✅ Rotate secrets regularly
- ✅ Use different secrets per environment

### SSL/TLS Configuration

**Certificate Management**:

- Use Let's Encrypt for free SSL certificates
- Automate certificate renewal
- Use TLS 1.2 or higher
- Disable weak cipher suites

---

## Scaling

### Horizontal Scaling

**Auto-Scaling Configuration**:

```bash
# Kubernetes Horizontal Pod Autoscaler
kubectl autoscale deployment myapp \
  --cpu-percent=70 \
  --min=3 \
  --max=10
```

### Vertical Scaling

**When to Scale Up**:

- Consistent high CPU/memory usage
- Increased traffic patterns
- Performance degradation

**How to Scale**:

- Update instance size in infrastructure code
- Apply changes during maintenance window
- Monitor performance after scaling

---

## Disaster Recovery

### Backup Strategy

**Database Backups**:

- Daily automated backups
- 30-day retention period
- Cross-region replication
- Tested restore procedures

**Application Backups**:

- Code in version control (Git)
- Infrastructure as code (Terraform)
- Configuration in version control

### Restore Procedures

**Database Restore**:

```bash
# PostgreSQL restore
psql -h localhost -U user -d database < backup.sql

# MySQL restore
mysql -h localhost -u user -p database < backup.sql
```

---

## Troubleshooting

### Common Deployment Issues

**Issue**: Deployment timeout

- **Cause**: Slow health check response
- **Solution**: Increase timeout, optimize health check

**Issue**: Database migration fails

- **Cause**: Lock contention, invalid migration
- **Solution**: Review migration, run during low-traffic period

**Issue**: Container won't start

- **Cause**: Missing environment variable, port conflict
- **Solution**: Check logs, verify configuration

### Debugging Commands

```bash
# Check application logs
kubectl logs -f deployment/myapp

# Check pod status
kubectl describe pod <pod-name>

# Access container shell
kubectl exec -it <pod-name> -- /bin/bash

# Check resource usage
kubectl top pods
```

---

## Maintenance Windows

**Scheduled Maintenance**:

- Time: Sunday 2:00 AM - 4:00 AM UTC
- Frequency: Monthly
- Notification: 1 week advance notice
- Status Page: Update before, during, and after

---

## Useful Commands

```bash
# Check deployment status
make status

# View logs
make logs

# Restart application
make restart

# Run health check
make health-check

# View metrics
make metrics
```

---

## Additional Resources

- **Cloud Provider Documentation**: [AWS Docs | Azure Docs | GCP Docs]
- **Kubernetes Documentation**: https://kubernetes.io/docs/
- **Terraform Documentation**: https://www.terraform.io/docs/
- **Internal Runbook**: [Link to internal operations runbook]

---

## Project-Specific Deployment Details

<!-- Add project-specific deployment procedures here -->

**TODO**: Complete deployment guide after infrastructure is set up.
