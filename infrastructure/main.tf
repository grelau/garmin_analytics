terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "garmin-tf-state"
    key            = "terraform/state.tfstate"
    region         = "eu-west-3"
    dynamodb_table = "terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = "eu-west-3"
}

# Activities S3 bucket
resource "aws_s3_bucket" "garmin_activity_bucket" {
  bucket = "garmin-activity-bucket"

  tags = {
    Name = "garmin-activity-bucket"
  }
}
#Activities Dynamo DB
resource "aws_dynamodb_table" "activities" {
  name         = "Activities"
  billing_mode = "PAY_PER_REQUEST"

  hash_key  = "user_id"
  range_key = "activity_id"

  attribute {
    name = "user_id"
    type = "N"
  }

  attribute {
    name = "activity_id"
    type = "N"
  }

  attribute {
    name = "startTimeLocal"
    type = "S"
  }

  global_secondary_index {
    name            = "user_date_index"
    hash_key        = "user_id"
    range_key       = "startTimeLocal"
    projection_type = "ALL"
  }
}
#Users Dynamo DB
resource "aws_dynamodb_table" "users" {
  name         = "Users"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"

  attribute {
    name = "user_id"
    type = "N"
  }
}

#INGESTION LAMBDA
resource "aws_lambda_function" "collect_lambda" {
  function_name = "collect-garmin-activities"
  runtime       = "python3.13"
  handler       = "collect.request"
  role          = aws_iam_role.lambda_exec_role.arn

  filename         = "../lambdas/lambdas.zip"
  source_code_hash = filebase64sha256("../lambdas/lambdas.zip")

  timeout = 900
  memory_size  = 1024

  tags = {
    Name = "collect-garmin-activities"
  }
  
  environment {
    variables = {
      SQS_URL = aws_sqs_queue.activity_queue.url
    }
  }
  
  lifecycle {
     ignore_changes = [
          environment
      ]
  }

}

#WORKER LAMBDA
resource "aws_lambda_function" "processing_lambda" {
  function_name = "process-garmin-activity"
  runtime       = "python3.13"
  handler       = "process.request"
  role          = aws_iam_role.lambda_exec_role.arn

  filename         = "../lambdas/lambdas.zip"
  source_code_hash = filebase64sha256("../lambdas/lambdas.zip")

  timeout = 300
  reserved_concurrent_executions = 10

  tags = {
    Name = "process-garmin-activity"
  }
  
  lifecycle {
      ignore_changes = [
          environment
      ]
  }

}

#SQS QUEUE
resource "aws_sqs_queue" "activity_queue" {
  name = "garmin-activity-queue"

  visibility_timeout_seconds = 300
}

#TRIGGER SQS => lambda process
resource "aws_lambda_event_source_mapping" "sqs_trigger" {
  event_source_arn = aws_sqs_queue.activity_queue.arn
  function_name    = aws_lambda_function.processing_lambda.arn

  batch_size = 1
}

#ROLE EXEC LAMBDA
resource "aws_iam_role" "lambda_exec_role" {
  name = "collect-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Action    = "sts:AssumeRole"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

#POLICY SQS
resource "aws_iam_policy" "sqs_lambda" {
  name = "lambda_sqs_policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "sqs:SendMessage",
        "sqs:ReceiveMessage",
        "sqs:DeleteMessage",
        "sqs:GetQueueAttributes"
      ]
      Resource = aws_sqs_queue.activity_queue.arn
    }]
  })
}

#POLICY LAMBDA LOGS
resource "aws_iam_policy" "lambda_logs" {
  name = "lambda-logs-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ]
      Resource = "*"
    }]
  })
}
#POLICY LAMBDA <==> Activities DYNAMO DB
resource "aws_iam_policy" "lambda_dynamodb_users" {
  name = "lambda-users-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "dynamodb:Scan",
        "dynamodb:GetItem"
      ]
      Resource = aws_dynamodb_table.users.arn
    }]
  })
}

#POLICY LAMBDA <==> Activities DYNAMO DB
resource "aws_iam_policy" "lambda_dynamodb_activities" {
  name = "lambda-activities-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:Scan",
        "dynamodb:BatchWriteItem"
      ]
      Resource = aws_dynamodb_table.activities.arn
    }]
  })
}

#POLICY LAMBDA ==> S3
resource "aws_iam_policy" "lambda_s3" {
  name = "lambda-s3-policy"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "s3:PutObject",
        "s3:GetObject",
        "s3:ListBucket"
      ]
      Resource = [
        aws_s3_bucket.garmin_activity_bucket.arn,
        "${aws_s3_bucket.garmin_activity_bucket.arn}/*"
      ]
    }]
  })
}


resource "aws_iam_role_policy_attachment" "logs" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.lambda_logs.arn
}

resource "aws_iam_role_policy_attachment" "s3" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.lambda_s3.arn
}

resource "aws_iam_role_policy_attachment" "dynamodb_activities" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.lambda_dynamodb_activities.arn
}

resource "aws_iam_role_policy_attachment" "dynamodb_users" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.lambda_dynamodb_users.arn
}

resource "aws_iam_role_policy_attachment" "lambda_sqs" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.sqs_lambda.arn
}

#CRON LAMBDA
resource "aws_cloudwatch_event_rule" "daily_trigger" {
  name                = "collect-garmin-daily"
  schedule_expression = "cron(30 21 * * ? *)"
}

resource "aws_cloudwatch_event_target" "lambda_target" {
  rule = aws_cloudwatch_event_rule.daily_trigger.name
  arn  = aws_lambda_function.collect_lambda.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.collect_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.daily_trigger.arn
}
