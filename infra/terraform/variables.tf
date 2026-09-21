variable "aws_region" {
  type    = string
  default = "us-east-1"
}

variable "name_prefix" {
  type    = string
  default = "trao"
}

variable "my_ip_cidr" {
  type        = string
  description = "Your public IP as CIDR for SSH (e.g. 1.2.3.4/32)."
}

variable "public_key_path" {
  type        = string
  description = "Path to an SSH public key file."
}

variable "instance_type" {
  type    = string
  default = "t3.small"
}

variable "repo_url" {
  type        = string
  description = "Git clone URL for the application repository."
}

variable "data_volume_gb" {
  type    = number
  default = 20
}

variable "budget_usd" {
  type    = string
  default = "30"
}

variable "budget_email" {
  type        = string
  description = "Email for the AWS Budgets alarm."
}
