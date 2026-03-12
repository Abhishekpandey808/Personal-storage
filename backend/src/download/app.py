"""
Download Lambda Handler
Generates a pre-signed GET URL so the client can download a file directly from S3.
"""
import json
import os
import boto3
from botocore.exceptions import ClientError

s3_client = boto3.client("s3")
BUCKET_NAME = os.environ["STORAGE_BUCKET"]


def _cors_headers():
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,Authorization",
        "Access-Control-Allow-Methods": "GET,OPTIONS",
    }


def _get_user_id(event):
    claims = (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("claims", {})
    )
    return claims.get("sub") or claims.get("cognito:username")


def download_handler(event, context):
    """
    Query parameters:
      - object_key (str): S3 key of the file to download

    Returns a pre-signed GET URL valid for 5 minutes.
    The handler verifies that the requested key belongs to the authenticated user.
    """
    try:
        user_id = _get_user_id(event)
        if not user_id:
            return {
                "statusCode": 401,
                "headers": _cors_headers(),
                "body": json.dumps({"error": "Unauthorized"}),
            }

        params = event.get("queryStringParameters") or {}
        object_key = params.get("object_key")

        if not object_key:
            return {
                "statusCode": 400,
                "headers": _cors_headers(),
                "body": json.dumps({"error": "object_key query parameter is required"}),
            }

        # Ensure the user can only access their own files
        if not object_key.startswith(f"{user_id}/"):
            return {
                "statusCode": 403,
                "headers": _cors_headers(),
                "body": json.dumps({"error": "Access denied"}),
            }

        # Verify the object exists before generating the URL
        s3_client.head_object(Bucket=BUCKET_NAME, Key=object_key)

        presigned_url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET_NAME, "Key": object_key},
            ExpiresIn=300,
        )

        return {
            "statusCode": 200,
            "headers": _cors_headers(),
            "body": json.dumps({"download_url": presigned_url, "expires_in": 300}),
        }

    except ClientError as exc:
        error_code = exc.response["Error"]["Code"]
        if error_code in ("404", "NoSuchKey"):
            return {
                "statusCode": 404,
                "headers": _cors_headers(),
                "body": json.dumps({"error": "File not found"}),
            }
        return {
            "statusCode": 500,
            "headers": _cors_headers(),
            "body": json.dumps({"error": str(exc)}),
        }
