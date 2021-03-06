terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
      version = "3.73.0"
    }
  }
}

provider "aws" {
  region = var.region
}

# i've probably given too many permissions here
# This role currently is not being used with Lambda, but might be useful eventually with enough functions
module "iam_assumable_role" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-assumable-role"
  version = "4.10.1"
  
  # required
  number_of_custom_role_policy_arns = 4

  # optional
  create_role = true
  custom_role_policy_arns = [
      "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole",
      "arn:aws:iam::aws:policy/AWSXRayDaemonWriteAccess",
      "arn:aws:iam::aws:policy/AmazonS3FullAccess",
      "arn:aws:iam::aws:policy/service-role/AWSLambdaVPCAccessExecutionRole",]
  role_description = "Lambda function with access to S3 and public internet" 
  role_name = "syc-lambda"
  role_requires_mfa = false
  tags = {
      Terraform = true,
  }

  trusted_role_services = [
    "lambda.amazonaws.com"
  ]
}

# hard coded bucket name
module "s3-bucket" {
  source  = "terraform-aws-modules/s3-bucket/aws"
  version = "2.13.0"

  bucket = "syc-lambda-bucket"

  tags = {
      Terraform = true,
  }

  block_public_policy = true
  attach_policy = true
  policy = <<EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowS3Access",
            "Effect": "Allow",
            "Principal": {
                "AWS": "${module.iam_assumable_role.iam_role_arn}"
            },
            "Action": [
                "s3:*"
            ],
            "Resource": [
                "arn:aws:s3:::syc-lambda-bucket",
                "arn:aws:s3:::syc-lambda-bucket/*"
            ]
        }
    ]
}
EOF
}

# define Lambda functions x2
module "lambda_function_existing_package_s3" {
  source = "terraform-aws-modules/lambda/aws"

  function_name = "MembershipBot"
  description   = "Membership Bot"
  handler       = "MembershipBot.handler"
  runtime       = "python3.9"
  create_package      = false

  s3_existing_package = {
    bucket = module.s3-bucket.s3_bucket_id
    key    = "MembershipBot.zip"
  }

  environment_variables = {
    SQUARESPACE_API_KEY = var.SQUARESPACE_API_KEY
    STRIPE_API_KEY = var.STRIPE_API_KEY
  }

  timeout = 300

  allowed_triggers = {
    ScanAmiRule = {
      principal  = "events.amazonaws.com"
      source_arn = module.eventbridge.eventbridge_rule_arns["crons"]
    }
  }

  layers = [
    module.lambda_layer_s3.lambda_layer_arn,
  ]

  tags = {
    Terraform = "true"
  }
}

module "lambda_function_schedule_bot" {
  source = "terraform-aws-modules/lambda/aws"

  function_name = "ScheduleBot"
  description   = "Schedule Bot"
  handler       = "ScheduleBot.handler"
  runtime       = "python3.9"
  create_package      = false

  s3_existing_package = {
    bucket = module.s3-bucket.s3_bucket_id
    key    = "ScheduleBot.zip"
  }

  environment_variables = {
    ACUITY_API_KEY = var.ACUITY_API_KEY
    ACUITY_API_USER = var.ACUITY_API_USER
  }

  timeout = 300
  
  # api is made through the console for now, pass the arn
  allowed_triggers = {
    APIGateway = {
      service  = "apigateway"
      source_arn = var.api_gateway_arn
    }
  }

  layers = [
    module.lambda_layer_s3.lambda_layer_arn,
  ]

  tags = {
    Terraform = "true"
  }
}

module "lambda_layer_s3" {
  source = "terraform-aws-modules/lambda/aws"

  create_layer = true

  layer_name          = "MembershipBot-layer"
  description         = "General layer for gspread, google auth, stripe, and python-dateutil"
  compatible_runtimes = ["python3.9"]
  create_package      = false

  s3_existing_package = {
    bucket = module.s3-bucket.s3_bucket_id
    key    = "LambdaLayer.zip"
  }

  store_on_s3 = true
  s3_bucket   = module.s3-bucket.s3_bucket_id
}

# define eventbridge cron job
module "eventbridge" {
  source  = "terraform-aws-modules/eventbridge/aws"
  version = "1.13.4"
  # insert the 6 required variables her
  create_bus = false

  rules = {
    crons = {
      description         = "Trigger for a Lambda"
      schedule_expression = "cron(0 * * * ? *)"
    }
  }

  targets = {
    crons = [
      {
        name  = "MembershipBot"
        arn   = module.lambda_function_existing_package_s3.lambda_function_arn
        input = jsonencode({"job": "cron-by-rate"})
      }
    ]
  }
}