import logging
import json
import boto3
from urllib.parse import unquote_plus
import uuid
import os
from PIL import Image, ExifTags, TiffImagePlugin
from decimal import Decimal
import dateutil.parser as dparser

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)

DEST_BUCKET = os.environ['dest_bucket_orig']
THUMB_BUCKET = os.environ['dest_bucket_thumb']
DB_TABLE = os.environ['dynamo_db_table']

S3_RESOURCE = boto3.resource('s3')
S3_CLIENT = boto3.client('s3')
DYNAMODB_TABLE = boto3.resource('dynamodb').Table(DB_TABLE)

def resize_image(loc, resized_path, size):
    with Image.open(loc) as image:
        image.thumbnail(size)
        image.save(resized_path)


def dl_file(bucket, obj, loc):
    bucket.download_file(obj, loc)


def get_exif(loc):
    with Image.open(loc) as image:
        exif = {
            ExifTags.TAGS[k]: v
            for k, v in image.getexif().items()
            if k in ExifTags.TAGS and 
            type(v) not in [bytes, TiffImagePlugin.IFDRational]
        }
    return exif 


def create_thumb(in_bucket, obj_key, thumb_bucket):
    ext = os.path.splitext(obj_key)[1]
    tmp_loc_orig = f'/tmp/{uuid.uuid4()}{ext}'
    tmp_loc_thumb = f'/tmp/{uuid.uuid4()}{ext}'
    dl_file(in_bucket, obj_key, tmp_loc_orig)
    resize_image(tmp_loc_orig, tmp_loc_thumb, (100, 100))
    S3_CLIENT.upload_file(tmp_loc_thumb, thumb_bucket.name,
        obj_key, ExtraArgs={'ServerSideEncryption': 'aws:kms'}
    )
    return (tmp_loc_orig, tmp_loc_thumb)


def handler(event, context):

    try:

        LOGGER.info(f'SQS EVENT: {event}')

        for sqs_rec in event['Records']:

            s3_event = json.loads(sqs_rec['body'])

            LOGGER.info(f'S3 EVENT: {s3_event}')

            for s3_rec in s3_event.get('Records'):

                in_bucket = S3_RESOURCE.Bucket(s3_rec['s3']['bucket']['name'])
                out_bucket = S3_RESOURCE.Bucket(DEST_BUCKET)
                thumb_bucket = S3_RESOURCE.Bucket(THUMB_BUCKET)

                
                # key needs unquote_plus because spaces replaced with '+'
                obj_key = unquote_plus(s3_rec['s3']['object']['key'])

                # process file
                tmp_loc_orig, tmp_loc_thumb = create_thumb(in_bucket, obj_key, thumb_bucket)

                LOGGER.info(f"Bucket name{s3_rec['s3']['bucket']['name']}:{obj_key}")

                exif = get_exif(tmp_loc_orig)

                image_date = dparser.parse(exif['DateTime'])
                new_key = f'{image_date.year}/{image_date.month}/{image_date.day}/{obj_key}'

                S3_RESOURCE.Object(out_bucket.name, new_key).copy_from(
                    CopySource=f"{in_bucket.name}/{obj_key}",
                    ServerSideEncryption='aws:kms',
                )

                S3_RESOURCE.Object(in_bucket.name, obj_key).delete()

                DYNAMODB_TABLE.put_item(
                    Item = {
                        'object_url': obj_key,
                        'extension' : os.path.splitext(obj_key)[1],
                        'exif': json.loads(json.dumps(exif), parse_float=Decimal)
                    }
                )

    except Exception as e:

        LOGGER.error(f'Exception: {e}')
            
