import os
import uuid

import boto3
from botocore.exceptions import ClientError
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "heic", "webp"}

_s3_client = None


def get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client("s3", region_name=os.environ.get("AWS_REGION", "us-east-1"))
    return _s3_client


def get_bucket_name():
    bucket = os.environ.get("S3_BUCKET_NAME")
    if not bucket:
        raise RuntimeError("S3_BUCKET_NAME environment variable is not set.")
    return bucket


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def upload_inspection_photo(file_storage, application_id):
    """Uploads a photo to a private S3 bucket under inspections/<application_id>/<uuid>.

    Returns (bucket, key). The bucket is expected to block public access;
    callers should use generate_presigned_view_url() to display images.
    """
    filename = secure_filename(file_storage.filename or "")
    if not filename or not allowed_file(filename):
        raise ValueError("Unsupported file type.")

    ext = filename.rsplit(".", 1)[1].lower()
    key = f"inspections/{application_id}/{uuid.uuid4().hex}.{ext}"
    bucket = get_bucket_name()

    get_s3_client().upload_fileobj(
        file_storage,
        bucket,
        key,
        ExtraArgs={"ContentType": file_storage.mimetype or "application/octet-stream"},
    )
    return bucket, key


def generate_presigned_view_url(bucket, key, expires_in=3600):
    try:
        return get_s3_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_in,
        )
    except ClientError:
        return None
