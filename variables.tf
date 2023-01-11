variable "region" {
    default = "eu-west-2"
    description = "AWS Region to deploy to"
}

variable "app_env" {
    default = "sthompson-pic-bup"
    description = "Common prefix for all Terraform created resources"
}

variable "db_table_name" {
    default = "pic_db"
    description = "name of the dynamo db table"
}
