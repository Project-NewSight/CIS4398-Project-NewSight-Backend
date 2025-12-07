"""
Utility functions for uploading and deleting files on AWS S3.
Used by:
- Color Cue
- Emergency Contact
- Familiar Face Detection
"""

import os
import mimetypes
import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
AWS_BUCKET = os.getenv("AWS_S3_BUCKET_NAME")

if not all([AWS_ACCESS_KEY, AWS_SECRET_KEY, AWS_REGION, AWS_BUCKET]):
    print("⚠ Missing AWS configuration values in .env file")

# Create S3 client
s3_client = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)


def _guess_content_type(filename: str) -> str:
    """Guess MIME type based on filename extension."""
    content_type, _ = mimetypes.guess_type(filename)
    return content_type or "application/octet-stream"


def upload_to_s3(file_path: str, folder: str, filename: str) -> str:
    """
    Upload a file to S3 and return the fully-qualified URL.
    Bucket uses disabled ACLs, so no ACL parameter is passed.
    """
    try:
        s3_key = f"{folder}/{filename}"

        content_type = _guess_content_type(filename)

        s3_client.upload_file(
            file_path,
            AWS_BUCKET,
            s3_key,
            ExtraArgs={"ContentType": content_type}
        )

        # Return the URL of the uploaded object
        return f"https://{AWS_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"

    except FileNotFoundError:
        print(f"❌ File not found: {file_path}")
    except NoCredentialsError:
        print("❌ AWS credentials missing. Check .env file.")
    except ClientError as e:
        print(f"❌ AWS Client Error: {e}")

    return None


def delete_from_s3(folder: str, filename: str) -> bool:
    """
    Delete an object from S3.
    Returns True if successful, False otherwise.
    """
    try:
        s3_key = f"{folder}/{filename}"
        s3_client.delete_object(Bucket=AWS_BUCKET, Key=s3_key)
        return True

    except ClientError as e:
        print(f"❌ Error deleting file from S3: {e}")
        return False
