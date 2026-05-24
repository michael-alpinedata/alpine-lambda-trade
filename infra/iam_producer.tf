data "aws_region" "current" {}

resource "aws_iam_policy" "alt_producer_policy" {
  name        = "alt-producer-policy"
  description = "Permissions for Local Producer to access S3 (Batch) and SQS (Speed)"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:ListBucket"
        ]
        Resource = [
          "arn:aws:s3:::alt-raw-data-${data.aws_caller_identity.current.account_id}",
          "arn:aws:s3:::alt-raw-data-${data.aws_caller_identity.current.account_id}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "sqs:SendMessage",
          "sqs:GetQueueAttributes",
          "sqs:GetQueueUrl"
        ]
        Resource = [
          "arn:aws:sqs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:alt-ticker-queue.fifo"
        ]
      }
    ]
  })
}

resource "aws_iam_user_policy_attachment" "producer_attach" {
  user       = split("/", data.aws_caller_identity.current.arn)[1]
  policy_arn = aws_iam_policy.alt_producer_policy.arn
}
