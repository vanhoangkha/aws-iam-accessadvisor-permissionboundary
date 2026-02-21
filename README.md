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

## Cost Estimation (2026 Pricing)

> **Region:** Asia Pacific (Singapore) - ap-southeast-1  
> **Last Updated:** February 2026  
> **Scenario:** Worst-case (maximum cost estimation)

### Pricing Reference (Singapore Region)

| Service | Unit | Price (USD) |
|---------|------|-------------|
| Lambda Requests | per 1M requests | $0.20 |
| Lambda Duration (x86) | per GB-second | $0.0000166667 |
| Step Functions | per 1,000 state transitions | $0.025 |
| DynamoDB Write | per 1M write request units | $0.625 |
| DynamoDB Read | per 1M read request units | $0.125 |
| DynamoDB Storage | per GB-month | $0.285 |
| S3 Standard | per GB-month | $0.025 |
| S3 PUT requests | per 1,000 requests | $0.005 |
| KMS CMK | per key per month | $1.00 |
| KMS Requests | per 10,000 requests | $0.03 |
| CloudWatch Logs | per GB ingested | $0.57 |
| CloudWatch Alarms | per alarm per month | $0.10 |
| SNS Publish | per 1M requests | $0.50 |
| SNS Email | per 1,000 notifications | $2.00 |

### Worst-Case Assumptions

| Parameter | Worst-Case Value | Notes |
|-----------|------------------|-------|
| IAM Entities | 1,000 | Large enterprise |
| Executions per month | 1 | Full monthly run |
| ProcessEntity duration | 300 seconds | Max timeout |
| ProcessEntity memory | 512 MB | Configured value |
| Lambda retries | 3 per entity | Max retries on failure |
| Step Functions retries | 2 per state | Error handling |
| Log size per execution | 1 GB | Verbose logging |
| Report size | 10 MB | Large JSON report |
| DynamoDB item size | 4 KB | Max per entity |
| KMS requests | 10,000 | Encryption operations |

### Monthly Cost Calculation (Worst-Case: 1,000 Entities)

| Service | Worst-Case Calculation | Monthly Cost |
|---------|------------------------|--------------|
| **Lambda Requests** | | |
| - ListEntities | 1 × 3 retries = 3 requests | $0.00 |
| - ProcessEntity | 1,000 × 3 retries = 3,000 requests | $0.00 |
| - GenerateReport | 1 × 3 retries = 3 requests | $0.00 |
| - Total requests | 3,006 × $0.20/1M | **$0.00** |
| **Lambda Duration** | | |
| - ListEntities | 60s × 0.256GB × 3 retries × $0.0000166667 | $0.00 |
| - ProcessEntity | 1,000 × 300s × 0.512GB × 3 × $0.0000166667 | **$7.68** |
| - GenerateReport | 60s × 0.256GB × 3 retries × $0.0000166667 | $0.00 |
| **Step Functions** | | |
| - State transitions | (5 + 1,000×3) × 2 retries = 6,010 | |
| - Cost | 6,010 × $0.025/1000 | **$0.15** |
| **DynamoDB** | | |
| - Writes | 1,000 items × 4KB = 4,000 WRU | |
| - Write cost | 4,000 × $0.625/1M | $0.00 |
| - Storage | 1,000 × 4KB = 4MB × $0.285/GB | $0.00 |
| - Total DynamoDB | | **$0.01** |
| **S3** | | |
| - Storage | 10MB report × 12 months = 120MB | |
| - Storage cost | 0.12GB × $0.025 | $0.00 |
| - PUT requests | 10 × $0.005/1000 | $0.00 |
| - Total S3 | | **$0.01** |
| **KMS** | | |
| - CMK | 1 key × $1.00 | $1.00 |
| - Requests | 10,000 × $0.03/10000 | $0.03 |
| - Total KMS | | **$1.03** |
| **CloudWatch** | | |
| - Logs ingested | 1GB × $0.57 | $0.57 |
| - Log storage | 1GB × $0.033 | $0.03 |
| - Alarms | 2 × $0.10 | $0.20 |
| - Total CloudWatch | | **$0.80** |
| **SNS** | | |
| - Publish | 10 × $0.50/1M | $0.00 |
| - Email delivery | 10 × $2.00/1000 | $0.02 |
| - Total SNS | | **$0.02** |
| **EventBridge** | | |
| - Scheduled rules | Free | **$0.00** |
| | | |
| **TOTAL WORST-CASE** | | **$9.70** |

### Cost by Scale (Worst-Case)

| Scale | Entities | Lambda GB-s | Step Transitions | Monthly Cost | Annual Cost |
|-------|----------|-------------|------------------|--------------|-------------|
| Startup | 50 | 23,040 | 310 | $1.95 | $23.40 |
| SMB | 100 | 46,080 | 610 | $2.58 | $30.96 |
| Medium | 500 | 230,400 | 3,010 | $5.88 | $70.56 |
| Large | 1,000 | 460,800 | 6,010 | $9.70 | $116.40 |
| Enterprise | 5,000 | 2,304,000 | 30,010 | $41.22 | $494.64 |
| Max Scale | 10,000 | 4,608,000 | 60,010 | $80.38 | $964.56 |

### Worst-Case Cost Breakdown (1,000 Entities)

```
Lambda Duration:    $7.68  (79.2%)
KMS:                $1.03  (10.6%)
CloudWatch:         $0.80  ( 8.2%)
Step Functions:     $0.15  ( 1.5%)
SNS:                $0.02  ( 0.2%)
DynamoDB:           $0.01  ( 0.1%)
S3:                 $0.01  ( 0.1%)
─────────────────────────────────
TOTAL:              $9.70  (100%)
```

### Comparison: Best vs Worst Case (1,000 Entities)

| Scenario | Monthly Cost | Annual Cost | Assumptions |
|----------|--------------|-------------|-------------|
| Best Case | $1.79 | $21.48 | No retries, minimal logs, Free Tier |
| Typical | $3.50 | $42.00 | Some retries, normal logs |
| Worst Case | $9.70 | $116.40 | Max retries, verbose logs, no Free Tier |
| **Absolute Max** | $15.00 | $180.00 | Everything fails + retries |

### AWS Free Tier Impact

| Service | Free Tier | Worst-Case Usage | Savings |
|---------|-----------|------------------|---------|
| Lambda Requests | 1,000,000 | 3,006 | $0.00 |
| Lambda Compute | 400,000 GB-s | 460,800 GB-s | -$1.01 (exceeds) |
| DynamoDB | 25 WCU | 4,000 WRU | $0.00 |
| S3 | 5 GB | 0.12 GB | $0.00 |
| Step Functions | 4,000 transitions | 6,010 | -$0.05 (exceeds) |
| CloudWatch | 10 alarms | 2 | $0.00 |

**With Free Tier (worst-case): ~$8.64/month**  
**Without Free Tier (worst-case): ~$9.70/month**

### Cost Optimization Applied

| Optimization | Implementation | Worst-Case Savings |
|--------------|----------------|-------------------|
| On-Demand DynamoDB | PAY_PER_REQUEST | ~$50/month vs Provisioned |
| Reserved Concurrency | Max 10 concurrent | Prevents runaway costs |
| S3 Intelligent-Tiering | Lifecycle after 30 days | ~40% on old reports |
| DynamoDB TTL | Auto-delete 365 days | ~$3/year storage |
| Lambda Memory | 512MB (not 10GB) | ~95% savings |
| 90-day Schedule | Not daily | ~97% savings |

### ROI Analysis (Worst-Case)

| Approach | Time | Annual Cost | Notes |
|----------|------|-------------|-------|
| Manual Audit | 132 hrs/year | $6,600 | 4× audit × 33hrs × $50/hr |
| This Solution (worst) | 20 min/year | $116.40 | Fully automated |
| **Savings** | 131.7 hrs | **$6,483.60** | **98.2% cost reduction** |

### Cost Alerts Recommendation

Set up AWS Budgets alerts:

| Alert | Threshold | Action |
|-------|-----------|--------|
| Monthly budget | $20 | Email notification |
| Forecasted | $50 | Email + SNS |
| Anomaly detection | 150% baseline | Immediate alert |

> ⚠️ **Note:** Worst-case assumes all retries trigger, verbose logging enabled, and no Free Tier.  
> 📊 Use [AWS Pricing Calculator](https://calculator.aws/#/createCalculator) for custom estimates.  
> 📈 Prices effective February 2026. Check [AWS Pricing](https://aws.amazon.com/pricing/) for updates.

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
