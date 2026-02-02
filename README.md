# AWS IAM Access Advisor Automation

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![AWS](https://img.shields.io/badge/AWS-SAM-orange.svg)](https://aws.amazon.com/serverless/sam/)
[![Python](https://img.shields.io/badge/Python-3.11-green.svg)](https://www.python.org/)

Automatically audit IAM permissions and enforce least privilege using AWS Access Advisor data.

## Architecture

![Architecture](architecture.png)

## High-Level Overview

![High Level](architecture-high-level.png)

## Features

- **Automated Audit** - Analyzes all IAM users and roles using Access Advisor API
- **Permissions Boundary** - Automatically creates and applies boundaries based on actual usage
- **Scheduled Execution** - Runs every 90 days via EventBridge
- **Audit History** - Stores results in DynamoDB with 365-day TTL
- **Reports** - Generates JSON reports in S3
- **Notifications** - Email alerts via SNS when audit completes
- **Security** - KMS encryption for all data at rest

## Components

| Service | Purpose |
|---------|---------|
| EventBridge | Scheduled trigger (90 days) |
| Step Functions | Workflow orchestration |
| Lambda | ListEntities, ProcessEntity, GenerateReport |
| DynamoDB | Audit history storage |
| S3 | Reports storage |
| SNS | Email notifications |
| KMS | Encryption at rest |
| CloudWatch | Alarms & monitoring |

## Quick Start

### Prerequisites

- AWS CLI configured
- [SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html) installed
- Python 3.11+

### Deploy

```bash
# Clone repository
git clone https://github.com/vanhoangkha/aws-iam-accessadvisor-permissionboundary.git
cd aws-iam-accessadvisor-permissionboundary

# Build and deploy
sam build
sam deploy --guided
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `Environment` | prod | Environment name |
| `DaysExpire` | 180 | Days before unused permissions are restricted |
| `Enforce` | yes | Apply permissions boundaries (yes/no) |
| `NotificationEmail` | - | Email for notifications |

## How It Works

1. **EventBridge** triggers Step Functions workflow every 90 days
2. **ListEntities Lambda** retrieves all IAM users and roles
3. **ProcessEntity Lambda** (10 concurrent):
   - Calls IAM Access Advisor API
   - Analyzes service usage within expiration period
   - Tags entities with coverage metrics
   - Creates/updates permissions boundary policies
   - Stores audit data in DynamoDB
4. **GenerateReport Lambda** creates summary report in S3
5. **SNS** sends email notification with results

## Exclusions

The following entities are excluded from permissions boundary enforcement:

- `AccessAdvisor-*` (solution's own roles)
- `AWSServiceRole*` (AWS service-linked roles)
- `admin` (admin users)
- `OrganizationAccountAccess*`

## Output Examples

### DynamoDB Record

```json
{
  "pk": "role#my-role",
  "sk": "audit#2026-02-02",
  "coverage": 75,
  "total": 100,
  "used": 75,
  "services_used": ["s3", "dynamodb", "lambda"]
}
```

### S3 Report

```json
{
  "date": "2026-02-02",
  "total_entities": 85,
  "avg_coverage": 48,
  "details": [
    {"name": "my-role", "type": "role", "coverage": 75, "services": 3}
  ]
}
```

## Security

- All data encrypted with KMS CMK (auto-rotation enabled)
- Least privilege IAM roles for each Lambda function
- S3 bucket policy enforces SSL and KMS encryption
- DLQ for failed processing with CloudWatch alarms
- Point-in-time recovery enabled for DynamoDB

## Project Structure

```
.
├── template.yaml              # SAM template (production-ready)
├── statemachine.asl.json      # Step Functions definition
├── cf.yml                     # Simple CloudFormation template
├── accessadvisor_automation.py # Standalone Python script
├── architecture.png           # Detailed architecture diagram
└── architecture-high-level.png # High-level architecture diagram
```

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Based on [aws-samples/aws-iam-accessadvisor-permissionboundary](https://github.com/aws-samples/aws-iam-accessadvisor-permissionboundary)
- Enhanced with Step Functions, DynamoDB, and security hardening
