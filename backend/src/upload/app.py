"""
Upload Lambda Handler
Generates a pre-signed URL for direct S3 upload or accepts base64-encoded file content.
"""
import json
import os
import uuid
import boto3
from botocore.exceptions import ClientError

s3_client = boto3.client("s3")
BUCKET_NAME = os.environ["STORAGE_BUCKET"]


def _cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
        "Access-Control-Allow-Methods": "POST,OPTIONS",
    }


def _get_user_id(event):
    """Extract the authenticated user's sub (unique ID) from the JWT claims."""
    claims = (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("claims", {})
    )
    return claims.get("sub") or claims.get("cognito:username")


def upload_handler(event, context):
    """
    Accepts a JSON body with:
      - filename  (str): original file name
      - content_type (str): MIME type of the file

    Returns a pre-signed PUT URL that the client can use to upload
    directly to S3, scoped to the authenticated user's prefix.
    """
    try:
        user_id = _get_user_id(event)
        if not user_id:
            return {
                "statusCode": 401,
                "headers": _cors_headers(),
                "body": json.dumps({"error": "Unauthorized"}),
            }

        body = json.loads(event.get("body") or "{}")
        filename = body.get("filename")
        content_type = body.get("content_type", "application/octet-stream")

        if not filename:
            return {
                "statusCode": 400,
                "headers": _cors_headers(),
                "body": json.dumps({"error": "filename is required"}),
            }

        # Store each user's files under their own prefix
        object_key = f"{user_id}/{uuid.uuid4()}_{filename}"

        presigned_url = s3_client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": BUCKET_NAME,
                "Key": object_key,
                "ContentType": content_type,
            },
            ExpiresIn=300,  # URL valid for 5 minutes
        )

        return {
            "statusCode": 200,
            "headers": _cors_headers(),
            "body": json.dumps(
                {
                    "upload_url": presigned_url,
                    "object_key": object_key,
                    "expires_in": 300,
                }
            ),
        }

    except ClientError as exc:
        return {
            "statusCode": 500,
            "headers": _cors_headers(),
            "body": json.dumps({"error": str(exc)}),
        }
    except (json.JSONDecodeError, KeyError) as exc:
        return {
            "statusCode": 400,
            "headers": _cors_headers(),
            "body": json.dumps({"error": f"Invalid request: {exc}"}),
        }
