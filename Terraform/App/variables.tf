variable "region" {
  description = "This is the AWS region for the VPC"
  default = "us-east-1"
}

variable "SQUARESPACE_API_KEY" {
  description = "API key for Squarespace"
}

variable "STRIPE_API_KEY" {
  description = "API key for Stripe"
}

variable "ACUITY_API_KEY" {
  description = "API key for Acuity"
}

variable "ACUITY_API_USER" {
  description = "UserID for Acuity"
}

variable "api_gateway_arn" {
  description = "arn for the API Gateway, this should be created in the console for now"
}