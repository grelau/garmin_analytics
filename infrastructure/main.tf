terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "= 5.77.0"
    }
  }
}

terraform {
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

resource "aws_vpc" "main" {
    cidr_block = "10.0.0.0/16"
}

resource "aws_subnet" "private" {
    vpc_id                  = aws_vpc.main.id
    cidr_block              = "10.0.1.0/24"
}

resource "aws_subnet" "public" {
    vpc_id                  = aws_vpc.main.id
    cidr_block              = "10.0.2.0/24"
    map_public_ip_on_launch = true
}

resource "aws_internet_gateway" "igw" {
    vpc_id = aws_vpc.main.id
}

# Public route table
resource "aws_route_table" "rt-public" {
    vpc_id = aws_vpc.main.id
    route {
        cidr_block = "0.0.0.0/0"
        gateway_id = aws_internet_gateway.igw.id
    } 
}

# Public route table association with public subnet 
resource "aws_route_table_association" "assoc-rt-public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.rt-public.id
}

# Private route table for private subnet 
resource "aws_route_table" "rt-private" {
  vpc_id = aws_vpc.main.id
}

# Private route table association with private subnet 
resource "aws_route_table_association" "assoc-rt-private" {
  subnet_id      = aws_subnet.private.id
  route_table_id = aws_route_table.rt-private.id
}




# Security Group for NAT Instance
resource "aws_security_group" "sg-nat-instance" {
  name        = "nat-instance-sg"
  description = "Security Group for NAT instance"
  vpc_id      = aws_vpc.main.id
}

# NAT Instance security group rule to allow all traffic from within the VPC
resource "aws_security_group_rule" "vpc-inbound" {
  type              = "ingress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = [aws_vpc.main.cidr_block]
  security_group_id = aws_security_group.sg-nat-instance.id
}

# NAT Instance security group rule to allow outbound traffic
resource "aws_security_group_rule" "outbound-nat-instance" {
  type              = "egress"
  from_port         = 0
  to_port           = 0
  protocol          = "-1"
  cidr_blocks       = ["0.0.0.0/0"]
  security_group_id = aws_security_group.sg-nat-instance.id
}

# Get the community AMI Image Id
data "aws_ami" "fck-nat-amzn2" {
  most_recent = true
  filter {
    name   = "name"
    values = ["fck-nat-amzn2-hvm-1.2.1*-x86_64-ebs"]
  }
  filter {
    name   = "owner-id"
    values = ["568608671756"]
  }
}

# Build the NAT Instance
resource "aws_instance" "nat-instance" {
  ami                         = data.aws_ami.fck-nat-amzn2.id
  instance_type               = "t2.nano"
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.sg-nat-instance.id]
  associate_public_ip_address = true
  source_dest_check           = false

  # Root disk for NAT instance 
  root_block_device {
    volume_size = "2"
    volume_type = "gp2"
    encrypted   = true
  }
}



resource "aws_security_group" "lambda_sg" {
    vpc_id = aws_vpc.main.id

    ingress {
        from_port = 0
        to_port = 0
        protocol = -1
        cidr_blocks = [aws_subnet.public.cidr_block]
    }
    # Autoriser le trafic sortant vers Internet (pour l'API)
    egress {
      from_port   = 0
      to_port     = 0
      protocol    = -1
      cidr_blocks = ["0.0.0.0/0"]
    }

    tags = {
      Name = "collect-lambda-sg"
    }
}

# Route table entry to forward traffic to NAT instance
resource "aws_route" "outbound-nat-route" {
  route_table_id         = aws_route_table.rt-private.id
  destination_cidr_block = "0.0.0.0/0"
  network_interface_id   = aws_instance.nat-instance.primary_network_interface_id
}

# Création du rôle IAM pour Lambda
resource "aws_iam_role" "lambda_exec_role" {
    name = "lambda-exec-role"

    assume_role_policy = jsonencode({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Action": "sts:AssumeRole",
                "Principal": {
                    "Service": "lambda.amazonaws.com"
                },
                "Effect": "Allow",
                "Sid": ""
            }
        ]
    })
}

# Politique d'écriture S3
resource "aws_iam_policy" "lambda_s3_policy" {
    name = "lambda-s3-policy"

    policy = jsonencode({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "s3:PutObject",
                    "s3:PutObjectAcl",
                    "s3:ListBucket"
                ],
                "Resource": "${aws_s3_bucket.garmin_activity_bucket.arn}/*"
            }
        ]
    })
}

resource "aws_iam_policy" "lambda_dynamodb_policy" {
    name        = "LambdaDynamoDBPolicy"
    description = "IAM Policy for Lambda to access DynamoDB"

    policy = jsonencode({
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": [
                    "dynamodb:PutItem",
                    "dynamodb:UpdateItem",
                    "dynamodb:BatchWriteItem",
                    "dynamodb:Scan"
                ],
                "Resource": "${aws_dynamodb_table.activities.arn}"
            }
        ]
    })
}

resource "aws_iam_policy" "lambda_logs_policy" {
    name = "lambda_logging_policy"
    description = "Policy for Lambda function to create log group" 
    
    policy = jsonencode({
        "Version" : "2012-10-17",
        "Statement" : [{
            "Action" : [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Effect" : "Allow",
            "Resource" : "arn:aws:logs:*:*:*"
        }]
    })
}

resource "aws_iam_policy" "lambda_vpc_policy" {
    name        = "lambda-vpc-policy"
    description = "Policy for Lambda function to access VPC resources"

    policy = jsonencode({
        Version = "2012-10-17"
        Statement = [
            {
                Effect = "Allow"
                Action = [
                    "ec2:CreateNetworkInterface",
                    "ec2:DescribeNetworkInterfaces",
                    "ec2:DescribeSecurityGroups",
                    "ec2:DescribeSubnets",
                    "ec2:DeleteNetworkInterface"
                ]
                Resource = "*"
            }
        ]
    })
}

# Attacher les politiques S3 au rôle
resource "aws_iam_role_policy_attachment" "lambda_s3_attachment" {
    role       = aws_iam_role.lambda_exec_role.name
    policy_arn = aws_iam_policy.lambda_s3_policy.arn
}

resource "aws_iam_role_policy_attachment" "lambda_dynamo_db_attachment" {
    role       = aws_iam_role.lambda_exec_role.name
    policy_arn = aws_iam_policy.lambda_dynamodb_policy.arn
}

resource "aws_iam_role_policy_attachment" "lambda_log_groups" {
    role       = aws_iam_role.lambda_exec_role.name
    policy_arn = aws_iam_policy.lambda_logs_policy.arn
}

resource "aws_iam_role_policy_attachment" "attach_lambda_vpc_policy" {
    role       = aws_iam_role.lambda_exec_role.name
    policy_arn = aws_iam_policy.lambda_vpc_policy.arn
}

resource "aws_cloudwatch_event_rule" "collect_lambda_trigger" {
  name        = "daily_lambda_trigger"
  description = "Déclenche la Lambda chaque jour à 22h UTC"
  schedule_expression = "cron(30 21 * * ? *)"
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.main_lambda.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.collect_lambda_trigger.arn
}

resource "aws_cloudwatch_event_target" "invoke_collect_lambda" {
  rule      = aws_cloudwatch_event_rule.collect_lambda_trigger.name
  target_id = "LambdaDailyTrigger"
  arn       = aws_lambda_function.main_lambda.arn
}

resource "aws_lambda_function" "main_lambda" {
    function_name    = "collect-lambda"
    handler          = "collect.request"
    runtime          = "python3.13"
    role             = aws_iam_role.lambda_exec_role.arn
    filename         = "../collect/collect.zip"
    source_code_hash         = filebase64sha256("../collect/collect.zip")

    vpc_config {
        subnet_ids         = [aws_subnet.private.id]
        security_group_ids = [aws_security_group.lambda_sg.id]
    }

    lifecycle {
        ignore_changes = [
            environment,
            timeout
        ]
    }

    tags = {
        Name = "collect-lambda"
    }
}

resource "aws_s3_bucket" "garmin_activity_bucket" {
    bucket = "garmin-activity-bucket"

    tags = {
        Name = "garmin-activity-bucket"
    }
}

resource "aws_s3_bucket_acl" "data_bucket_acl" {
    bucket = aws_s3_bucket.garmin_activity_bucket.id
    acl    = "private"
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