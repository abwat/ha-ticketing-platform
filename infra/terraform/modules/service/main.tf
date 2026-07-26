variable "service_name" {
  type = string
}

variable "container_image" {
  type = string
}

variable "desired_count" {
  type    = number
  default = 2
}

output "service_contract" {
  value = {
    name          = var.service_name
    image         = var.container_image
    desired_count = var.desired_count
    health_path   = "/health"
    ready_path    = "/ready"
  }
}

