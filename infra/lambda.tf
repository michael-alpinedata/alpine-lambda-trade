variable "snowflake_account" {
  description = "Passed dynamically from .env to avoid exposure"
  type        = string
  sensitive   = true
}

variable "snowflake_user" {
  description = "Passed dynamically from .env"
  type        = string
  sensitive   = true
}

variable "snowflake_password" {
  description = "Passed dynamically from .env"
  type        = string
  sensitive   = true
}

resource "aws_iam_role" "lambda_exec_role" {
  name = "alt-lambda-speed-role"
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "lambda.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_sqs_policy" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaSQSQueueExecutionRole"
}

resource "aws_lambda_function" "speed_layer" {
  function_name    = "alt-speed-ema-processor"
  role             = aws_iam_role.lambda_exec_role.arn
  handler          = "app.lambda_handler"
  runtime          = "python3.12"
  timeout          = 15
  memory_size      = 256
  
  # Ensure deploy requires the zip artifact
  filename         = "${path.module}/../src/speed_layer/speed_layer.zip"
  source_code_hash = fileexists("${path.module}/../src/speed_layer/speed_layer.zip") ? filebase64sha256("${path.module}/../src/speed_layer/speed_layer.zip") : ""

  environment {
    variables = {
      SNOWFLAKE_ACCOUNT  = var.snowflake_account
      SNOWFLAKE_USER     = var.snowflake_user
      SNOWFLAKE_PASSWORD = var.snowflake_password
    }
  }
}

resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn                   = aws_sqs_queue.ticker_queue.arn
  function_name                      = aws_lambda_function.speed_layer.arn
  batch_size                         = 10
}
