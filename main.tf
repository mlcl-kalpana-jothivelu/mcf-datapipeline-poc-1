# Provider configuration
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# Variables
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "ap-southeast-2"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "mcf-data-pipeline"
}

# S3 Bucket
resource "aws_s3_bucket" "main" {
  bucket = "${var.project_name}-bucket-${random_id.bucket_suffix.hex}"
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

# resource "aws_s3_bucket_notification" "eventbridge" {
#   bucket = aws_s3_bucket.main.id

#   eventbridge = true
# }
# Enable EventBridge notifications on S3 bucket
resource "aws_s3_bucket_notification" "eventbridge" {
  bucket = aws_s3_bucket.main.id

  eventbridge = true

  depends_on = [aws_s3_bucket.main]
}

# IAM role for S3 to publish to EventBridge
resource "aws_iam_role" "s3_eventbridge_role" {
  name = "${var.project_name}-s3-eventbridge-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "s3.amazonaws.com"
        }
      }
    ]
  })
}

# IAM policy for S3 to publish to EventBridge
resource "aws_iam_role_policy" "s3_eventbridge_policy" {
  name = "${var.project_name}-s3-eventbridge-policy"
  role = aws_iam_role.s3_eventbridge_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "events:PutEvents"
        ]
        Resource = "*"
      }
    ]
  })
}

# Lambda function
resource "aws_lambda_function" "main" {
  filename         = "lambda_function.zip"
  function_name    = "${var.project_name}-lambda-processor"
  role            = aws_iam_role.lambda_role.arn
  handler         = "index.handler"
  runtime         = "python3.9"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      S3_BUCKET = aws_s3_bucket.main.bucket
      DB_HOST   = aws_db_instance.postgres.endpoint
      DB_NAME   = aws_db_instance.postgres.db_name
    }
  }
}

# Lambda deployment package
data "archive_file" "lambda_zip" {
  type        = "zip"
  output_path = "lambda_function.zip"
  source {
    content = file("${path.module}/fileparser.py")
    filename = "index.py"
  }
}

# IAM role for Lambda
resource "aws_iam_role" "lambda_role" {
  name = "${var.project_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}

# IAM policy for Lambda to access S3
resource "aws_iam_role_policy" "lambda_s3_policy" {
  name = "${var.project_name}-lambda-s3-policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.main.arn,
          "${aws_s3_bucket.main.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# RDS Subnet Group
resource "aws_db_subnet_group" "main" {
  name       = "${var.project_name}-subnet-group"
  subnet_ids = ["subnet-04123e95096d427db", "subnet-070a3cbcfc9f1e863"]

  tags = {
    Name = "${var.project_name}-db-subnet-group"
  }
}

# Security Group for RDS
resource "aws_security_group" "rds" {
  name_prefix = "${var.project_name}-rds-"
  vpc_id      = "vpc-0b0561352d4a49872"

  ingress {
    from_port   = 5432
    to_port     = 5432
    protocol    = "tcp"
    cidr_blocks = ["172.31.0.0/16"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# RDS PostgreSQL instance
resource "aws_db_instance" "postgres" {
  identifier     = "${var.project_name}-postgres"
  engine         = "postgres"
  engine_version = "17.4"
  instance_class = "db.t3.micro"
  allocated_storage = 20
  storage_type   = "gp2"

  db_name  = "mcfdb"
  username = "mcfdbuser"
  password = "TempPass123!" # Use random_password resource for production

  vpc_security_group_ids = [aws_security_group.rds.id]
  db_subnet_group_name   = aws_db_subnet_group.main.name

  backup_retention_period = 7
  backup_window          = "03:00-04:00"
  maintenance_window     = "sun:04:00-sun:05:00"

  skip_final_snapshot = true
}

# # Random password for database
# resource "random_password" "db_password" {
#   length  = 16
#   special = true
# }

# VPC
# resource "aws_vpc" "main" {
#   cidr_block           = "10.0.0.0/16"
#   enable_dns_hostnames = true
#   enable_dns_support   = true

#   tags = {
#     Name = "${var.project_name}-vpc"
#   }
# }

# Internet Gateway
# resource "aws_internet_gateway" "main" {
#   vpc_id = aws_vpc.main.id

#   tags = {
#     Name = "${var.project_name}-igw"
#   }
# }

# # Public Subnets
# resource "aws_subnet" "public_1" {
#   vpc_id                  = aws_vpc.main.id
#   cidr_block              = "10.0.1.0/24"
#   availability_zone       = data.aws_availability_zones.available.names[0]
#   map_public_ip_on_launch = true

#   tags = {
#     Name = "${var.project_name}-public-1"
#   }
# }

# resource "aws_subnet" "public_2" {
#   vpc_id                  = aws_vpc.main.id
#   cidr_block              = "10.0.2.0/24"
#   availability_zone       = data.aws_availability_zones.available.names[1]
#   map_public_ip_on_launch = true

#   tags = {
#     Name = "${var.project_name}-public-2"
#   }
# }

# # Private Subnets
# resource "aws_subnet" "private_1" {
#   vpc_id            = aws_vpc.main.id
#   cidr_block        = "10.0.3.0/24"
#   availability_zone = data.aws_availability_zones.available.names[0]

#   tags = {
#     Name = "${var.project_name}-private-1"
#   }
# }

# resource "aws_subnet" "private_2" {
#   vpc_id            = aws_vpc.main.id
#   cidr_block        = "10.0.4.0/24"
#   availability_zone = data.aws_availability_zones.available.names[1]

#   tags = {
#     Name = "${var.project_name}-private-2"
#   }
# }

# # Route Table for Public Subnets
# resource "aws_route_table" "public" {
#   vpc_id = aws_vpc.main.id

#   route {
#     cidr_block = "0.0.0.0/0"
#     gateway_id = aws_internet_gateway.main.id
#   }

#   tags = {
#     Name = "${var.project_name}-public-rt"
#   }
# }

# # Route Table Associations
# resource "aws_route_table_association" "public_1" {
#   subnet_id      = aws_subnet.public_1.id
#   route_table_id = aws_route_table.public.id
# }

# resource "aws_route_table_association" "public_2" {
#   subnet_id      = aws_subnet.public_2.id
#   route_table_id = aws_route_table.public.id
# }

# Data source for availability zones
# // data "aws_availability_zones" "available" {
# //   state = "available"
# // }

# Outputs
output "s3_bucket_name" {
  description = "Name of the S3 bucket"
  value       = aws_s3_bucket.main.bucket
}

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.main.function_name
}

output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.postgres.endpoint
  sensitive   = true
}

# output "rds_password" {
#   description = "RDS instance password"
#   value       = random_password.db_password.result
#   sensitive   = true
# }