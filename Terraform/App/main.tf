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

# define eventbridge cron job
