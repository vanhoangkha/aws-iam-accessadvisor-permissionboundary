# AWS IAM Access Advisor Automation

Automatically audit IAM permissions and enforce least privilege using AWS Access Advisor data.

![Architecture](architecture.png)

## Features

- **Automated Audit**: Analyzes all IAM users and roles using Access Advisor API
- **Permissions Boundary**: Automatically creates and applies boundaries based on actual usage
- **Scheduled Execution**: Runs every 90 days via EventBridge
- **Audit History**: Stores results in DynamoDB with 365-day TTL
- **Reports**: Generates JSON reports in S3
- **Notifications**: Email alerts via SNS when audit completes
- **Security**: KMS encryption for all data at rest

## Architecture

![High Level](architecture-high-level.png)

### Components

| Service | Purpose |
|---------|---------|
| EventBridge | Scheduled trigger (90 days) |
| Step Functions | Workflow orchestration |
| Lambda (3 functions) | ListEntities, ProcessEntity, GenerateReport |
| DynamoDB | Audit history storage |
| S3 | Reports storage |
| SNS | Email notifications |
| KMS | Encryption at rest |
| CloudWatch | Alarms & monitoring |

## Deployment

### Prerequisites

- AWS CLI configured
- SAM CLI installed
- Python 3.11+

### Deploy

```bash
sam build
sam deploy --guided \
  --stack-name AccessAdvisor-prod \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    Environment=prod \
    DaysExpire=180 \
    Enforce=yes \
    NotificationEmail=your-email@example.com
```

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| Environment | prod | Environment name |
| DaysExpire | 180 | Days before unused permissions are restricted |
| Enforce | yes | Apply permissions boundaries (yes/no) |
| NotificationEmail | - | Email for notifications |

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

## Output

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
  "details": [...]
}
```

## Security

- All data encrypted with KMS CMK (auto-rotation enabled)
- Least privilege IAM roles for each Lambda function
- S3 bucket policy enforces SSL and KMS encryption
- DLQ for failed processing with CloudWatch alarms

## Files

| File | Description |
|------|-------------|
| `template.yaml` | SAM template (production-ready) |
| `statemachine.asl.json` | Step Functions definition |
| `cf.yml` | Simple CloudFormation template |
| `accessadvisor_automation.py` | Standalone Python script |

## License

Apache 2.0
