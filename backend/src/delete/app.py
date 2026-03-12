"""
Delete Lambda Handler
Deletes a file from S3 for the authenticated user.
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
        "Access-Control-Allow-Methods": "DELETE,OPTIONS",
    }


def _get_user_id(event):
    claims = (
        event.get("requestContext", {})
        .get("authorizer", {})
        .get("claims", {})
    )
    return claims.get("sub") or claims.get("cognito:username")


def delete_handler(event, context):
    """
    Accepts a JSON body with:
      - object_key (str): S3 key of the file to delete

    Only the file owner (matched by user_id prefix) may delete the object.
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
        object_key = body.get("object_key")

        if not object_key:
            return {
                "statusCode": 400,
                "headers": _cors_headers(),
                "body": json.dumps({"error": "object_key is required"}),
            }

        # Ensure the user can only delete their own files
        if not object_key.startswith(f"{user_id}/"):
            return {
                "statusCode": 403,
                "headers": _cors_headers(),
                "body": json.dumps({"error": "Access denied"}),
            }

        s3_client.delete_object(Bucket=BUCKET_NAME, Key=object_key)

        return {
            "statusCode": 200,
            "headers": _cors_headers(),
            "body": json.dumps({"message": "File deleted successfully", "object_key": object_key}),
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
