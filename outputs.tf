output "workmail_email" {
  value = "${var.workmail_user_name}@${var.organization_alias}.awsapps.com"
}

output "s3_bucket" {
  value = aws_s3_bucket.email_bucket.id
}

output "lambda_function" {
  value = aws_lambda_function.email_processor.function_name
}

output "ses_rule_set" {
  value = aws_ses_receipt_rule_set.main.rule_set_name
}