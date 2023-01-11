module "dynamodb_table" {
  source   = "terraform-aws-modules/dynamodb-table/aws"

  name     = "${var.app_env}-${var.db_table_name}"
  hash_key = "object_url"

  attributes = [
    {
      name = "object_url"
      type = "S"
    }
  ]
  }
