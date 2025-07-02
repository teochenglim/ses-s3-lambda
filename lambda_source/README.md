## 📧 AWS SES → S3 → Lambda Email Processor

This project processes incoming emails received via Amazon SES, stores the raw .eml in an S3 bucket, and triggers a Lambda function to extract email content, attachments, and inline images. Results are saved to a destination S3 bucket and forwarded to an external Collaboration Manager endpoint.

### 🧩 Architecture

```
Email Sent
   │
   ▼
AWS SES
   │
   ▼
S3 (EMAILS_BUCKET)
   │
   ▼
Lambda Trigger
   │
   ▼
Parses & Extracts:
  - Plain text / HTML body
  - Attachments
  - Embedded images (CID)
   │
   ▼
S3 (WORKFLOWMAX_BUCKET)
   │
   ▼
Collaboration Manager (HTTP POST)
```

### 📁 File Structure

```
.
├── lambda_function.py       # Main AWS Lambda handler
├── utils.py                 # Email parsing logic (shared for Lambda + local)
├── test_utils.py            # CLI for local testing of .eml files
├── README.md                # You're here
```

### 🔧 Lambda Function Responsibilities
- Triggered via S3 event when .eml is uploaded by SES.
- Skips email if any SES verdict fails: spf, dkim, spam, virus.
- Downloads .eml file from EMAILS_BUCKET.

    #### Extracts:

    - from, to, cc, and inferred bcc
    - Subject and timestamp
    - Plaintext and HTML body
    - All attachments under attachments/
    - Embedded/inline images under embedded_images/

    ### Uploads parsed parts to WORKFLOWMAX_BUCKET.

    Sends a structured JSON payload to COLLABORATION_MANAGER via HTTP POST.

### 🧪 Local Testing (no AWS needed)

Prerequisites

- Python 3.7+
- .eml sample file
- Install dependencies (if any). This version uses standard library only, so no pip needed.

### Testing

```bash
python test_utils.py path/to/sample.eml

```

### Output Structure

```shell
output/<message_id>/
├── email-body.txt
├── metadata.json
├── attachments/
│   └── invoice.pdf
└── embedded_images/
    └── logo.png
```

### The metadata.json includes:

```json
{
  "destination": ["bcc@example.com"],
  "attachments": ["attachments/invoice.pdf"],
  "embedded_attachments": ["embedded_images/logo.png"]
}
```

### ✅ Environment Variables (Lambda)
Variable	Description
- EMAILS_BUCKET	S3 bucket containing SES .eml files
- WORKFLOWMAX_BUCKET	S3 bucket where parsed content is stored
- COLLABORATION_MANAGER	URL to forward extracted payload as JSON

### 🔐 SES Verdict Handling
The Lambda exits early if any of these verdicts fail:

- X-SES-SPF-VERDICT
- X-SES-DKIM-VERDICT
- X-SES-SPAM-VERDICT
- X-SES-VIRUS-VERDICT

### 📤 Sample Collaboration Manager Payload

```json
{
  "timestamp": "2025-07-01T12:00:00Z",
  "source": "alice@example.com",
  "messageID": "abc123xyz",
  "destination": ["bob@example.com", "carol@example.com"],
  "To": ["bob@example.com"],
  "CC": ["carol@example.com"],
  "Subject": "Invoice Attached",
  "Content": "... email body ...",
  "Attachments": [
    "abc123xyz/attachments/invoice.pdf"
  ],
  "EmbeddedAttachments": [
    "abc123xyz/embedded_images/logo.png"
  ]
}
```

### 📌 Notes

- Bcc detection is inferred from the Received: header using a regex.
- Attachments are preserved with original filenames where possible.
- Embedded CIDs are stored with filenames so they can be restored to HTML if needed.
- HTML <img src="cid:..."> replacements are not included but can be added.