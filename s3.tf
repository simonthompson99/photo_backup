module "aws_s3_bucket" {
  source  = "terraform-aws-modules/s3-bucket/aws"
  version = "~> v2.13.0"

  bucket = "${var.app_env}-input-s3-bucket"

  server_side_encryption_configuration = {
    rule = {
      apply_server_side_encryption_by_default = {
        kms_master_key_id = aws_kms_key.objects.arn
        sse_algorithm     = "aws:kms"
      }
    }
  }

  # S3 bucket-level Public Access Block configuration
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true

}

module "aws_s3_bucket_output_orig" {
  source  = "terraform-aws-modules/s3-bucket/aws"
  version = "~> v2.13.0"

  bucket = "${var.app_env}-output-orig-s3-bucket"

  server_side_encryption_configuration = {
    rule = {
      apply_server_side_encryption_by_default = {
        kms_master_key_id = aws_kms_key.objects.arn
        sse_algorithm     = "aws:kms"
      }
    }
  }

  # S3 bucket-level Public Access Block configuration
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true

  lifecycle_rule = [{

        id      = "permanent_retention"
        enabled = true

        transition  = [{
            days            = 1
            storage_class   = "GLACIER"
        }]
    }]
}

module "aws_s3_bucket_output_thumb" {
  source  = "terraform-aws-modules/s3-bucket/aws"
  version = "~> v2.13.0"

  bucket = "${var.app_env}-output-thumb-s3-bucket"

  server_side_encryption_configuration = {
    rule = {
      apply_server_side_encryption_by_default = {
        kms_master_key_id = aws_kms_key.objects.arn
        sse_algorithm     = "aws:kms"
      }
    }
  }

  # S3 bucket-level Public Access Block configuration
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true

}

resource "aws_kms_key" "objects" {
  description             = "KMS key is used to encrypt bucket objects"
  deletion_window_in_days = 7
  enable_key_rotation     = true
}

# SQS queue
resource "aws_sqs_queue" "queue" {
  name = "${var.app_env}-s3-event-notification-queue"

  policy = <<POLICY
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "sqs:SendMessage",
      "Resource": "arn:aws:sqs:*:*:${var.app_env}-s3-event-notification-queue",
      "Condition": {
        "ArnEquals": { "aws:SourceArn": "${module.aws_s3_bucket.s3_bucket_arn}" }
      }
    }
  ]
}
POLICY
}

# S3 event filter
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = module.aws_s3_bucket.s3_bucket_id

  queue {
    queue_arn     = aws_sqs_queue.queue.arn
    events        = ["s3:ObjectCreated:*"]
  }
}

# Event source from SQS
resource "aws_lambda_event_source_mapping" "event_source_mapping" {
  event_source_arn = aws_sqs_queue.queue.arn
  enabled          = true
  function_name    = aws_lambda_function.sqs_processor.arn
  batch_size       = 1
}
