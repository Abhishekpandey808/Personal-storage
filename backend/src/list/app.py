"""
List Lambda Handler
Returns all files stored under the authenticated user's S3 prefix.
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


def list_handler(event, context):
    """
    Optional query parameters:
      - prefix (str): additional sub-prefix to filter results (relative to user prefix)

    Returns a list of file metadata objects for the authenticated user.
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
        sub_prefix = params.get("prefix", "")
        list_prefix = f"{user_id}/{sub_prefix}"

        files = []
        paginator = s3_client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=BUCKET_NAME, Prefix=list_prefix):
            for obj in page.get("Contents", []):
                key = obj["Key"]
                # Strip the user prefix for the display name
                display_name = key[len(f"{user_id}/"):]
                files.append(
                    {
                        "object_key": key,
                        "name": display_name,
                        "size": obj["Size"],
                        "last_modified": obj["LastModified"].isoformat(),
                    }
                )

        return {
            "statusCode": 200,
            "headers": _cors_headers(),
            "body": json.dumps({"files": files, "count": len(files)}),
        }

    except ClientError as exc:
        return {
            "statusCode": 500,
            "headers": _cors_headers(),
            "body": json.dumps({"error": str(exc)}),
        }
