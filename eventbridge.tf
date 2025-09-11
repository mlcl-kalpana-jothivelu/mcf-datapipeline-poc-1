# EventBridge rule to capture S3 events
resource "aws_cloudwatch_event_rule" "s3_events" {
  name        = "${var.project_name}-s3-events"
  description = "Capture S3 object created events"

  event_pattern = jsonencode({
    source      = ["aws.s3"]
    detail-type = ["Object Created"]
    detail = {
      bucket = {
        name = [aws_s3_bucket.main.bucket]
      }
    }
  })
}

# EventBridge target to invoke Lambda
resource "aws_cloudwatch_event_target" "lambda_target" {
  rule      = aws_cloudwatch_event_rule.s3_events.name
  target_id = "S3EventLambdaTarget"
  arn       = aws_lambda_function.main.arn
}

# Permission for EventBridge to invoke Lambda
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.main.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.s3_events.arn
}