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


resource "aws_s3_bucket" "garmin_activity_bucket" {
  bucket = "garmin-activity-bucket"

  tags = {
    Name = "garmin-activity-bucket"
  }
}

resource "aws_dynamodb_table" "activities" {
  name         = "ActivitiesTable"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "activity_id"

  attribute {
    name = "activity_id"
    type = "N"
  }
}



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

resource "aws_iam_policy" "lambda_dynamodb" {
  name = "lambda-dynamodb-policy"

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


resource "aws_iam_role_policy_attachment" "logs" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.lambda_logs.arn
}

resource "aws_iam_role_policy_attachment" "s3" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.lambda_s3.arn
}

resource "aws_iam_role_policy_attachment" "dynamodb" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.lambda_dynamodb.arn
}

resource "aws_lambda_function" "collect_lambda" {
  function_name = "collect-garmin-activities"
  runtime       = "python3.13"
  handler       = "collect.request"
  role          = aws_iam_role.lambda_exec_role.arn

  filename         = "../collect/collect.zip"
  source_code_hash = filebase64sha256("../collect/collect.zip")

  timeout = 900

  tags = {
    Name = "collect-garmin-activities"
  }
  
  lifecycle {
      ignore_changes = [
          environment
      ]
  }

}


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
