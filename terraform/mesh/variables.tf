variable "environment" {
  type        = string
  description = "Environment name (dev/staging/prod)"
}

variable "project_name" {
  type        = string
  description = "Name of the project"
}

variable "mesh_module_version" {
  type        = string
  description = "Version of the NHS MESH module to use"
}

variable "mesh_env" {
  type        = string
  description = "MESH environment (local/production/integration)"
}

variable "subnet_ids" {
  type        = list(string)
  description = "List of subnet IDs"
}

variable "mailbox_ids" {
  type        = list(string)
  description = "List of MESH mailbox IDs"
}

variable "verify_ssl" {
  type        = bool
  description = "Whether to verify SSL"
  default     = true
}

variable "get_message_max_concurrency" {
  type        = number
  description = "Maximum concurrency for getting messages"
  default     = 10
}

variable "compress_threshold" {
  type        = number
  description = "Compression threshold in bytes"
  default     = 1048576  # 1MB
}

variable "account_id" {
  type        = string
  description = "Account ID"
}