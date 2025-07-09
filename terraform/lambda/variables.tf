variable "prefix" {
    type = string
}

variable "short_prefix" {
    type = string
}

variable "function_name" {
    type = string
}

variable "image_uri" {
    type = string
}

variable "environments" {
    type = map(string)
    default = {}
}

variable "policy_json" {
    type = string
}

variable "vpc_security_group_ids" {
    type = list(string)
    default = null
}

variable "vpc_subnet_ids" {
    type = list(string)
    default = null
}
