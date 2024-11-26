variable "cidr_blocks" {
  type        = list(string)
  description = "cidr blocks definition"
}

variable "fck-nat-ami-name" {
  type        = string
  description = "name of the AMI for image id filter"
}

variable "fck-nat-owner-id" {
    type = string
    description = "AMI owner AWS id"
}




