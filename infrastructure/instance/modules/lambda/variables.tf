variable "prefix" {
  type = string
}

variable "short_prefix" {
  type = string
}

variable "function_name" {
  type = string
}

variable "error_alarm_notifications_enabled" {
  description = "Switch to enable error alarm notifications to Slack"
  type        = string
}

variable "image_uri" {
  type = string
}

variable "environment_variables" {
  type    = map(string)
  default = {}
}

variable "policy_json" {
  type = string
}

variable "vpc_security_group_ids" {
  type    = list(string)
  default = null
}

variable "vpc_subnet_ids" {
  type    = list(string)
  default = null
}

variable "environment" {
  description = "The deployment environment (e.g., dev, int, internal-qa, prod)"
  type        = string
}