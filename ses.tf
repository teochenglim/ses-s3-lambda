resource "aws_ses_receipt_rule_set" "main" {
  rule_set_name = "email-processing-rule-set"
}

resource "aws_ses_receipt_rule" "save_to_s3" {
  name          = "save-emails-to-s3"
  rule_set_name = aws_ses_receipt_rule_set.main.rule_set_name
  recipients    = ["${var.workmail_user_name}@${var.organization_alias}.awsapps.com"]
  enabled       = true
  scan_enabled  = true

  s3_action {
    position          = 1
    bucket_name       = aws_s3_bucket.email_bucket.id
    object_key_prefix = "raw/"
    iam_role_arn      = aws_iam_role.ses_s3_role.arn
  }

#   lambda_action {
#     position        = 2
#     function_arn    = aws_lambda_function.email_processor.arn
#     invocation_type = "Event"
#   }
}

resource "aws_iam_role" "ses_s3_role" {
  name = "ses-s3-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Effect    = "Allow",
      Principal = { Service = "ses.amazonaws.com" },
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "ses_s3_policy" {
  name = "ses-s3-policy"
  role = aws_iam_role.ses_s3_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect   = "Allow",
        Action   = "s3:ListBucket",
        Resource = aws_s3_bucket.email_bucket.arn
      },
      {
        Effect   = "Allow",
        Action   = "s3:PutObject",
        Resource = "${aws_s3_bucket.email_bucket.arn}/raw/*"
      },
      {
        Effect   = "Allow",
        Action   = "s3:GetBucketLocation",
        Resource = aws_s3_bucket.email_bucket.arn
      }
    ]
  })
}