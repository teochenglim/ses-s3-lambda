# AWS Email Processing Pipeline

This Terraform configuration creates a complete email processing pipeline using AWS WorkMail, SES, S3, and Lambda.

## Features
- Creates a WorkMail user with test domain (e.g., `test@your-alias.awsapps.com`)
- Configures SES to receive emails and store raw messages in S3
- Processes emails with Lambda to extract:
  - Email headers (stored in metadata.json)
  - Text and HTML bodies
  - Attachments
  - Embedded images
- Automatically cleans up old emails after retention period

## Architecture
📨 Email -> WorkMail -> SES -> S3 (raw) -> Lambda -> S3 (parsed)

### S3

s3://your-bucket/
├── raw/
│ └── <message_id>
└── parsed/
└── <message_id>/
├── metadata.json
├── content.txt
├── content.html
├── attachments/
  ├── file1.pdf
  └── file2.jpg
└── embedded_images/
  └── image1.png


## Deployment

1. **Initialize Terraform**

```bash
terraform init
terraform plan
```

2. Apply Configuration

```bash
terraform apply -auto-approve
```

3. Send Test Email

```bash
aws ses send-email \
  --from "sender@example.com" \
  --to "$(terraform output -raw workmail_email)" \
  --subject "Test Email" \
  --text "Hello from SES!" \
  --region us-east-1

```

## Testing Pipeline

1. Check Lambda logs:

```bash
aws logs tail \
  "/aws/lambda/$(terraform output -raw lambda_function)" \
  --region us-east-1
```

2. List processed emails in S3:

```bash
aws s3 ls s3://$(terraform output -raw s3_bucket)/parsed/
```

3. View metadata for an email:

```bash
aws s3 cp s3://$(terraform output -raw s3_bucket)/parsed/<message_id>/metadata.json -
```

## Cleanup

1. Delete WorkMail Resources

```bash
ORG_ID=$(cat .workmail_org_id)

# Delete user
aws workmail delete-user \
  --organization-id $ORG_ID \
  --user-id $(aws workmail list-users --organization-id $ORG_ID --query 'Users[0].Id' --output text) \
  --region [region]

# Delete organization
aws workmail delete-organization \
  --organization-id $ORG_ID \
  --region [region]
```

2. Destroy Terraform Resources

```bash
terraform destroy -auto-approve
```

3. Remove Local Files

```bash
rm -f .workmail_org_id lambda_function.zip
```