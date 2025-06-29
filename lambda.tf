data "archive_file" "lambda_zip" {
  type        = "zip"
  source_file = "${path.module}/lambda_source/lambda_function.py"
  output_path = "${path.module}/lambda_function.zip"
}

resource "aws_lambda_function" "email_processor" {
  filename         = data.archive_file.lambda_zip.output_path
  function_name    = "email-processor"
  role             = aws_iam_role.lambda_exec.arn
  handler          = "lambda_function.lambda_handler"
  runtime          = "python3.11"
  timeout          = var.lambda_timeout
  memory_size      = var.lambda_memory_size
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      BUCKET_NAME = aws_s3_bucket.email_bucket.id
    }
  }
}

resource "aws_iam_role" "lambda_exec" {
  name = "lambda-exec-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action    = "sts:AssumeRole",
      Effect    = "Allow",
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "lambda_policy" {
  name = "lambda_policy"
  role = aws_iam_role.lambda_exec.id

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
        Action   = [
          "s3:GetObject",
          "s3:PutObject"
        ],
        Resource = [
          "${aws_s3_bucket.email_bucket.arn}/raw/*",
          "${aws_s3_bucket.email_bucket.arn}/parsed/*"
        ]
      },
      {
        Effect   = "Allow",
        Action   = "logs:CreateLogGroup",
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Effect   = "Allow",
        Action   = ["logs:CreateLogStream", "logs:PutLogEvents"],
        Resource = "arn:aws:logs:*:*:log-group:/aws/lambda/${aws_lambda_function.email_processor.function_name}:*"
      }
    ]
  })
}

resource "aws_lambda_permission" "allow_ses" {
  statement_id  = "AllowExecutionFromSES"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.email_processor.function_name
  principal     = "ses.amazonaws.com"
  source_arn    = aws_ses_receipt_rule_set.main.arn
}

resource "aws_s3_bucket_notification" "email_event_trigger" {
  bucket = aws_s3_bucket.email_bucket.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.email_processor.arn
    events              = ["s3:ObjectCreated:*"]
    filter_suffix       = ""
    filter_prefix       = "raw/"
  }

  depends_on = [aws_lambda_permission.allow_ses]
}