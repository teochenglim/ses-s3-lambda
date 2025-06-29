resource "aws_s3_bucket" "email_bucket" {
  bucket = var.bucket_name
}
