variable "bucket_name" {
  description = "Name of the S3 bucket for storing emails"
  type        = string
}

variable "workmail_user_name" {
  description = "WorkMail username"
  type        = string
  default     = "test"
}

variable "workmail_user_password" {
  description = "Temporary password for WorkMail user"
  type        = string
  default     = "TempPassword123!"
  sensitive   = true
}

variable "organization_alias" {
  description = "Unique alias for WorkMail organization"
  type        = string
  default     = "email-pipeline"
}

variable "email_retention_days" {
  description = "Number of days to retain emails in S3"
  type        = number
  default     = 7
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "lambda_memory_size" {
  description = "Memory size for Lambda function"
  type        = number
  default     = 512
}

variable "lambda_timeout" {
  description = "Timeout for Lambda function"
  type        = number
  default     = 30
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default = {
    project     = "workmail-email-pipeline"
    environment = "dev"
    owner       = "chenglim.teo"
    ManagedBy   = "Terraform"
  }
}