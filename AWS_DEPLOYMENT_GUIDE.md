# AllerSense — AWS Deployment Guide

## Architecture Overview

```
                    ┌─────────────────┐
                    │   CloudFront    │  (optional CDN)
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
    ┌─────────▼─────────┐       ┌──────────▼──────────┐
    │  App Runner        │       │  App Runner          │
    │  (Frontend)        │       │  (Backend)           │
    │  Next.js :3000     │──────▶│  FastAPI :8000       │
    └────────────────────┘       └──────┬───────────────┘
                                        │
                    ┌───────────────────┼───────────────────┐
                    │                   │                   │
          ┌────────▼───────┐  ┌────────▼───────┐  ┌───────▼────────┐
          │  RDS PostgreSQL │  │  Redis Cloud   │  │  S3 Bucket     │
          │  (Free Tier)    │  │  (Existing)    │  │  (Reports)     │
          └─────────────────┘  └────────────────┘  └────────────────┘
                                                          │
                                                   ┌──────▼──────┐
                                                   │  Gemini API  │
                                                   │  (External)  │
                                                   └──────────────┘
```

## AWS Services Used

| Service | Tier | Est. Cost (with $120 credits) |
|---------|------|-------------------------------|
| **App Runner** (backend) | 0.25 vCPU, 0.5 GB | ~$5/month |
| **App Runner** (frontend) | 0.25 vCPU, 0.5 GB | ~$5/month |
| **RDS PostgreSQL** | db.t3.micro, 20 GB | Free tier (750 hrs/month) |
| **S3** | 5 GB storage | Free tier |
| **ECR** | Docker image registry | Free tier (500 MB) |
| **Redis Cloud** | Existing free plan | $0 |
| **Gemini API** | External | Free tier (15 req/min) |
| **Total** | | **~$10/month** (covered by credits) |

---

## Prerequisites

1. **AWS CLI** installed and configured: `aws configure`
2. **Docker** installed locally
3. **Gemini API key** from https://aistudio.google.com/apikey
4. AWS account with $120 credits

---

## Step 1: Create ECR Repositories

Push your Docker images to ECR so App Runner can pull them.

```bash
# Set your region
export AWS_REGION=us-east-1

# Create repos
aws ecr create-repository --repository-name allersense-backend --region $AWS_REGION
aws ecr create-repository --repository-name allersense-frontend --region $AWS_REGION

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.$AWS_REGION.amazonaws.com
```

## Step 2: Create RDS PostgreSQL (Free Tier)

```bash
# Create a DB subnet group (if using default VPC, skip this)
# Create the RDS instance
aws rds create-db-instance \
  --db-instance-identifier allersense-db \
  --db-instance-class db.t3.micro \
  --engine postgres \
  --engine-version 16.3 \
  --master-username allersense \
  --master-user-password YOUR_STRONG_PASSWORD_HERE \
  --allocated-storage 20 \
  --db-name allersense \
  --publicly-accessible \
  --backup-retention-period 1 \
  --no-multi-az \
  --storage-type gp2 \
  --region $AWS_REGION
```

Wait for the instance to be available (~5 minutes):
```bash
aws rds wait db-instance-available --db-instance-identifier allersense-db
```

Get the endpoint:
```bash
aws rds describe-db-instances \
  --db-instance-identifier allersense-db \
  --query 'DBInstances[0].Endpoint.Address' \
  --output text
```

**Important:** Update the RDS security group to allow inbound on port 5432 from App Runner.

### Run the DB migration
```bash
# Connect to RDS and create tables
# Option A: Use psql
psql postgresql://allersense:YOUR_PASSWORD@YOUR_RDS_ENDPOINT:5432/allersense

# Then run the schema creation — the backend's create_all does this automatically on startup.
# For the structured_data column specifically:
# ALTER TABLE patient_reports ADD COLUMN IF NOT EXISTS structured_data JSONB;
```

## Step 3: Create S3 Bucket

```bash
aws s3 mb s3://allersense-reports --region $AWS_REGION

# Block public access (reports are private)
aws s3api put-public-access-block \
  --bucket allersense-reports \
  --public-access-block-configuration \
  BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

## Step 4: Create IAM Role for App Runner

```bash
# Create a trust policy file
cat > trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "tasks.apprunner.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create the role
aws iam create-role \
  --role-name allersense-apprunner-role \
  --assume-role-policy-document file://trust-policy.json

# Attach S3 access policy
cat > s3-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::allersense-reports",
        "arn:aws:s3:::allersense-reports/*"
      ]
    }
  ]
}
EOF

aws iam put-role-policy \
  --role-name allersense-apprunner-role \
  --policy-name s3-access \
  --policy-document file://s3-policy.json
```

Also create an ECR access role for App Runner:
```bash
cat > ecr-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "build.apprunner.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

aws iam create-role \
  --role-name allersense-apprunner-ecr-role \
  --assume-role-policy-document file://ecr-trust-policy.json

aws iam attach-role-policy \
  --role-name allersense-apprunner-ecr-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess
```

## Step 5: Build & Push Docker Images

```bash
# Get your account ID and ECR URL
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ECR_URL=$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build and push backend
cd backend
docker build -t allersense-backend .
docker tag allersense-backend:latest $ECR_URL/allersense-backend:latest
docker push $ECR_URL/allersense-backend:latest
cd ..

# Build and push frontend
cd frontend
docker build -t allersense-frontend .
docker tag allersense-frontend:latest $ECR_URL/allersense-frontend:latest
docker push $ECR_URL/allersense-frontend:latest
cd ..
```

## Step 6: Deploy Backend on App Runner

Use the AWS Console or CLI:

```bash
export ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ECR_URL=$ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com
export RDS_ENDPOINT=YOUR_RDS_ENDPOINT  # from Step 2

aws apprunner create-service \
  --service-name allersense-backend \
  --source-configuration '{
    "AuthenticationConfiguration": {
      "AccessRoleArn": "arn:aws:iam::'$ACCOUNT_ID':role/allersense-apprunner-ecr-role"
    },
    "ImageRepository": {
      "ImageIdentifier": "'$ECR_URL'/allersense-backend:latest",
      "ImageRepositoryType": "ECR",
      "ImageConfiguration": {
        "Port": "8000",
        "RuntimeEnvironmentVariables": {
          "DATABASE_URL": "postgresql+asyncpg://allersense:YOUR_RDS_PASSWORD@'$RDS_ENDPOINT':5432/allersense",
          "DATABASE_URL_SYNC": "postgresql://allersense:YOUR_RDS_PASSWORD@'$RDS_ENDPOINT':5432/allersense",
          "REDIS_URL": "redis://:fzUEbVAqTqxN68fDieGWfAAcrGiULwcJ@redis-10333.c322.us-east-1-2.ec2.cloud.redislabs.com:10333",
          "AI_BACKEND": "gemini",
          "GEMINI_API_KEY": "YOUR_GEMINI_API_KEY",
          "GEMINI_MODEL": "gemini-2.0-flash",
          "USE_S3": "true",
          "S3_BUCKET": "allersense-reports",
          "S3_REGION": "us-east-1",
          "APP_ENV": "production",
          "APP_DEBUG": "false",
          "CORS_ORIGINS": "https://YOUR_FRONTEND_URL"
        }
      }
    }
  }' \
  --instance-configuration '{
    "Cpu": "0.25 vCPU",
    "Memory": "0.5 GB",
    "InstanceRoleArn": "arn:aws:iam::'$ACCOUNT_ID':role/allersense-apprunner-role"
  }' \
  --health-check-configuration '{
    "Protocol": "HTTP",
    "Path": "/health",
    "Interval": 10,
    "Timeout": 5,
    "HealthyThreshold": 1,
    "UnhealthyThreshold": 3
  }' \
  --region $AWS_REGION
```

Wait for deployment, then get the backend URL:
```bash
aws apprunner list-services --query 'ServiceSummaryList[?ServiceName==`allersense-backend`].ServiceUrl' --output text
```

The URL will look like: `https://xxxxx.us-east-1.awsapprunner.com`

## Step 7: Deploy Frontend on App Runner

First, rebuild the frontend Docker image with the backend URL:

```bash
cd frontend
# Update next.config.js or use build-time env
docker build \
  --build-arg NEXT_PUBLIC_API_URL=https://YOUR_BACKEND_APPRUNNER_URL \
  -t allersense-frontend .
docker tag allersense-frontend:latest $ECR_URL/allersense-frontend:latest
docker push $ECR_URL/allersense-frontend:latest
cd ..
```

Then deploy:
```bash
aws apprunner create-service \
  --service-name allersense-frontend \
  --source-configuration '{
    "AuthenticationConfiguration": {
      "AccessRoleArn": "arn:aws:iam::'$ACCOUNT_ID':role/allersense-apprunner-ecr-role"
    },
    "ImageRepository": {
      "ImageIdentifier": "'$ECR_URL'/allersense-frontend:latest",
      "ImageRepositoryType": "ECR",
      "ImageConfiguration": {
        "Port": "3000",
        "RuntimeEnvironmentVariables": {
          "NEXT_PUBLIC_API_URL": "https://YOUR_BACKEND_APPRUNNER_URL"
        }
      }
    }
  }' \
  --instance-configuration '{
    "Cpu": "0.25 vCPU",
    "Memory": "0.5 GB"
  }' \
  --region $AWS_REGION
```

## Step 8: Update CORS

Once you have the frontend App Runner URL, update the backend's CORS_ORIGINS:

```bash
# Update the backend environment variable
aws apprunner update-service \
  --service-arn YOUR_BACKEND_SERVICE_ARN \
  --source-configuration '{
    "ImageRepository": {
      "ImageIdentifier": "'$ECR_URL'/allersense-backend:latest",
      "ImageRepositoryType": "ECR",
      "ImageConfiguration": {
        "Port": "8000",
        "RuntimeEnvironmentVariables": {
          "CORS_ORIGINS": "https://YOUR_FRONTEND_APPRUNNER_URL"
        }
      }
    }
  }'
```

---

## Step 9: Update Frontend Dockerfile for Build-Time Env

The Next.js frontend needs `NEXT_PUBLIC_API_URL` at **build time**. Update the Dockerfile:

The frontend Dockerfile already supports this via the build arg. Just pass it when building:
```bash
docker build --build-arg NEXT_PUBLIC_API_URL=https://your-backend.awsapprunner.com -t allersense-frontend .
```

---

## Quick Checklist

- [ ] AWS CLI configured (`aws configure`)
- [ ] ECR repos created (backend + frontend)
- [ ] RDS PostgreSQL instance created (db.t3.micro, free tier)
- [ ] RDS security group allows port 5432 from App Runner
- [ ] S3 bucket created (`allersense-reports`)
- [ ] IAM roles created (App Runner instance role + ECR access role)
- [ ] Backend Docker image built and pushed to ECR
- [ ] Backend App Runner service created with correct env vars
- [ ] Backend health check passing at `/health`
- [ ] Get backend App Runner URL
- [ ] Frontend Docker image built with `NEXT_PUBLIC_API_URL` set
- [ ] Frontend pushed to ECR
- [ ] Frontend App Runner service created
- [ ] CORS_ORIGINS updated on backend to include frontend URL
- [ ] Gemini API key set in backend env vars
- [ ] Test: open frontend URL, search patient, upload report, check drug

---

## Updating After Code Changes

```bash
# Rebuild and push
docker build -t allersense-backend ./backend
docker tag allersense-backend:latest $ECR_URL/allersense-backend:latest
docker push $ECR_URL/allersense-backend:latest

# App Runner auto-deploys on new image push (if auto-deploy enabled)
# Or trigger manually:
aws apprunner start-deployment --service-arn YOUR_SERVICE_ARN
```

---

## Cleanup (to stop charges)

```bash
# Delete App Runner services
aws apprunner delete-service --service-arn YOUR_BACKEND_SERVICE_ARN
aws apprunner delete-service --service-arn YOUR_FRONTEND_SERVICE_ARN

# Delete RDS
aws rds delete-db-instance --db-instance-identifier allersense-db --skip-final-snapshot

# Delete S3 bucket
aws s3 rb s3://allersense-reports --force

# Delete ECR repos
aws ecr delete-repository --repository-name allersense-backend --force
aws ecr delete-repository --repository-name allersense-frontend --force

# Delete IAM roles
aws iam delete-role-policy --role-name allersense-apprunner-role --policy-name s3-access
aws iam delete-role --role-name allersense-apprunner-role
aws iam detach-role-policy --role-name allersense-apprunner-ecr-role --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess
aws iam delete-role --role-name allersense-apprunner-ecr-role
```
