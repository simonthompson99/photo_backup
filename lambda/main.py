import logging
import json
import boto3
from urllib.parse import unquote_plus
import uuid
import os
from PIL import Image

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

DEST_BUCKET = os.environ['dest_bucket_orig']
THUMB_BUCKET = os.environ['dest_bucket_thumb']
DB_TABLE = os.environ['dynamo_db_table']

s3 = boto3.resource('s3')
client = boto3.client('s3')
db = boto3.resource('dynamodb').Table(DB_TABLE)

def resize_image(image_path, resized_path):
    with Image.open(image_path) as image:
        image.thumbnail((100,100))
        image.save(resized_path)

def handler(event, context):

    try:

        LOGGER.info(f'SQS EVENT: {event}')

        for sqs_rec in event['Records']:

            s3_event = json.loads(sqs_rec['body'])

            LOGGER.info(f'S3 EVENT: {s3_event}')

            for s3_rec in s3_event.get('Records'):

                in_bucket = s3.Bucket(s3_rec['s3']['bucket']['name'])
                out_bucket = s3.Bucket(DEST_BUCKET)
                thumb_bucket = s3.Bucket(THUMB_BUCKET)

                
                # key needs unquote_plus because spaces replaced with '+'
                obj_key = unquote_plus(s3_rec['s3']['object']['key'])
                ext = os.path.splitext(obj_key)[1]

                #download to tmp folder
                tmp_loc = f'/tmp/{uuid.uuid4()}'
                in_bucket.download_file(obj_key, tmp_loc)
                resize_image(tmp_loc, f'{tmp_loc}_thumb{ext}')

                LOGGER.info(f"Bucket name{s3_rec['s3']['bucket']['name']}:{obj_key}")

                s3.Object(out_bucket.name, obj_key).copy_from(
                    CopySource=f"{in_bucket.name}/{obj_key}",
                    ServerSideEncryption='aws:kms',
                )

                client.upload_file(
                                    f'{tmp_loc}_thumb{ext}', thumb_bucket.name,
                                    obj_key, ExtraArgs={'ServerSideEncryption': 'aws:kms'}
                        )

                db.put_item(
                        Item = {
                            'object_url': obj_key,
                            'something_else': 'here'
                        }
                    )

    except Exception as e:

        LOGGER.error(f'Exception: {e}')
            
