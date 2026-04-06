resource "aws_sqs_queue" "ticker_dlq" {
  name                        = "alt-ticker-dlq.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
}

resource "aws_sqs_queue" "ticker_queue" {
  name                        = "alt-ticker-queue.fifo"
  fifo_queue                  = true
  content_based_deduplication = true
  delay_seconds               = 0
  max_message_size            = 262144
  message_retention_seconds   = 86400
  receive_wait_time_seconds   = 0

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.ticker_dlq.arn
    maxReceiveCount     = 3
  })
}
