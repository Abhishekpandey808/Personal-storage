"""
Unit tests for the Lambda function handlers.
Uses moto to mock AWS services so no real AWS account is required.
"""
import json
import os
import unittest
from unittest.mock import patch

import boto3
from moto import mock_aws

# Set required environment variables before importing handlers
os.environ["STORAGE_BUCKET"] = "test-bucket"
os.environ["COGNITO_USER_POOL_ID"] = "us-east-1_testpool"
os.environ["COGNITO_CLIENT_ID"] = "testclientid"
os.environ["REGION"] = "us-east-1"
# Fake credentials required by moto
os.environ["AWS_ACCESS_KEY_ID"] = "testing"
os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
os.environ["AWS_SECURITY_TOKEN"] = "testing"
os.environ["AWS_SESSION_TOKEN"] = "testing"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

from src.upload.app import upload_handler  # noqa: E402
from src.download.app import download_handler  # noqa: E402
from src.delete.app import delete_handler  # noqa: E402
from src.list.app import list_handler  # noqa: E402

USER_ID = "test-user-123"
BUCKET = "test-bucket"


def _make_event(method="POST", body=None, query_params=None, user_id=USER_ID):
    """Helper to build a minimal API Gateway proxy event."""
    return {
        "httpMethod": method,
        "body": json.dumps(body) if body else None,
        "queryStringParameters": query_params,
        "requestContext": {
            "authorizer": {
                "claims": {
                    "sub": user_id,
                    "cognito:username": user_id,
                }
            }
        },
    }


def _create_bucket(s3):
    s3.create_bucket(Bucket=BUCKET)


class TestUploadHandler(unittest.TestCase):
    @mock_aws
    def test_returns_presigned_url(self):
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=BUCKET)
        event = _make_event(body={"filename": "test.txt", "content_type": "text/plain"})
        response = upload_handler(event, {})
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertIn("upload_url", body)
        self.assertIn("object_key", body)
        self.assertTrue(body["object_key"].startswith(f"{USER_ID}/"))

    @mock_aws
    def test_missing_filename_returns_400(self):
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket=BUCKET)
        event = _make_event(body={})
        response = upload_handler(event, {})
        self.assertEqual(response["statusCode"], 400)

    def test_missing_auth_returns_401(self):
        event = _make_event(body={"filename": "test.txt"}, user_id=None)
        event["requestContext"]["authorizer"]["claims"] = {}
        response = upload_handler(event, {})
        self.assertEqual(response["statusCode"], 401)


class TestDownloadHandler(unittest.TestCase):
    @mock_aws
    def test_returns_presigned_url(self):
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=BUCKET)
        object_key = f"{USER_ID}/myfile.txt"
        s3.put_object(Bucket=BUCKET, Key=object_key, Body=b"hello")

        event = _make_event(method="GET", query_params={"object_key": object_key})
        response = download_handler(event, {})
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertIn("download_url", body)

    @mock_aws
    def test_access_denied_for_other_user_file(self):
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=BUCKET)
        other_key = "other-user/file.txt"
        s3.put_object(Bucket=BUCKET, Key=other_key, Body=b"secret")

        event = _make_event(method="GET", query_params={"object_key": other_key})
        response = download_handler(event, {})
        self.assertEqual(response["statusCode"], 403)

    def test_missing_object_key_returns_400(self):
        event = _make_event(method="GET", query_params={})
        response = download_handler(event, {})
        self.assertEqual(response["statusCode"], 400)


class TestDeleteHandler(unittest.TestCase):
    @mock_aws
    def test_deletes_own_file(self):
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=BUCKET)
        object_key = f"{USER_ID}/delete-me.txt"
        s3.put_object(Bucket=BUCKET, Key=object_key, Body=b"data")

        event = _make_event(method="DELETE", body={"object_key": object_key})
        response = delete_handler(event, {})
        self.assertEqual(response["statusCode"], 200)

    @mock_aws
    def test_access_denied_for_other_user_file(self):
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=BUCKET)
        other_key = "other-user/secret.txt"
        s3.put_object(Bucket=BUCKET, Key=other_key, Body=b"data")

        event = _make_event(method="DELETE", body={"object_key": other_key})
        response = delete_handler(event, {})
        self.assertEqual(response["statusCode"], 403)

    def test_missing_object_key_returns_400(self):
        event = _make_event(method="DELETE", body={})
        response = delete_handler(event, {})
        self.assertEqual(response["statusCode"], 400)


class TestListHandler(unittest.TestCase):
    @mock_aws
    def test_lists_user_files(self):
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket=BUCKET)
        s3.put_object(Bucket=BUCKET, Key=f"{USER_ID}/a.txt", Body=b"a")
        s3.put_object(Bucket=BUCKET, Key=f"{USER_ID}/b.txt", Body=b"b")
        s3.put_object(Bucket=BUCKET, Key="other-user/c.txt", Body=b"c")

        event = _make_event(method="GET", query_params={})
        response = list_handler(event, {})
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["count"], 2)
        keys = [f["object_key"] for f in body["files"]]
        self.assertIn(f"{USER_ID}/a.txt", keys)
        self.assertNotIn("other-user/c.txt", keys)

    def test_missing_auth_returns_401(self):
        event = _make_event(method="GET", user_id=None)
        event["requestContext"]["authorizer"]["claims"] = {}
        response = list_handler(event, {})
        self.assertEqual(response["statusCode"], 401)


if __name__ == "__main__":
    unittest.main()
