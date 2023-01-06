variable "region" {
    default = "eu-west-2"
    description = "AWS Region to deploy to"
}

variable "app_env" {
    default = "sthompson-pic-bup"
    description = "Common prefix for all Terraform created resources"
}
