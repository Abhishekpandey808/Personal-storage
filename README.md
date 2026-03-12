# Personal Cloud Storage

A serverless personal file-storage application built on AWS.

## Architecture

```
┌──────────────┐     ┌───────────────┐     ┌──────────────────┐
│  AWS Amplify │────▶│  API Gateway  │────▶│  AWS Lambda      │
│  (Frontend)  │     │  (REST API)   │     │  (Upload /       │
└──────────────┘     └───────────────┘     │   Download /     │
        │                                  │   Delete / List) │
        │            ┌───────────────┐     └────────┬─────────┘
        └───────────▶│    Cognito    │              │
                     │  (Auth/JWT)   │     ┌────────▼─────────┐
                     └───────────────┘     │    Amazon S3     │
                                           │  (File Storage)  │
                                           └──────────────────┘
```

| Service | Purpose |
|---|---|
| **Amazon Cognito** | User authentication & identity management |
| **API Gateway** | Exposes REST API endpoints |
| **AWS Lambda** | Serverless backend logic (Python 3.9) |
| **Amazon S3** | Secure file storage (per-user prefix isolation) |
| **AWS Amplify** | Frontend hosting & Amplify UI components |
| **AWS SAM** | Infrastructure as code & simplified deployment |

## Repository Structure

```
.
├── backend/
│   ├── template.yaml          # SAM template (Cognito, S3, Lambda, API GW)
│   ├── samconfig.toml         # SAM deploy defaults
│   ├── requirements.txt       # Lambda runtime dependencies
│   ├── requirements-dev.txt   # Dev/test dependencies
│   ├── src/
│   │   ├── upload/app.py      # POST /upload  – returns pre-signed PUT URL
│   │   ├── download/app.py    # GET  /download – returns pre-signed GET URL
│   │   ├── delete/app.py      # DELETE /delete – removes object from S3
│   │   └── list/app.py        # GET  /files   – lists user's files
│   └── tests/
│       └── test_handlers.py   # Unit tests (moto-based, no AWS required)
└── frontend/
    ├── package.json
    ├── amplify.json
    ├── .env.example
    └── src/
        ├── index.js
        ├── App.js
        ├── aws-exports.js     # Amplify / Cognito configuration
        └── components/
            └── FileManager.js # File list, upload, download & delete UI
```

## Prerequisites

- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) configured with appropriate credentials
- [AWS SAM CLI](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/install-sam-cli.html)
- [Node.js 18+](https://nodejs.org/) and npm
- [Python 3.9+](https://www.python.org/)

## Step 1 – Deploy the Backend

```bash
cd backend

# Build the SAM application
sam build

# Deploy interactively (first time)
sam deploy --guided

# Subsequent deploys
sam deploy
```

After deployment, note the CloudFormation **Outputs**:

| Output | Description |
|---|---|
| `ApiGatewayUrl` | Base URL for all API calls |
| `CognitoUserPoolId` | Cognito User Pool ID |
| `CognitoUserPoolClientId` | Cognito App Client ID |
| `StorageBucketName` | S3 bucket name |

## Step 2 – Configure the Frontend

```bash
cd frontend
cp .env.example .env
```

Edit `.env` and fill in the values from Step 1:

```env
REACT_APP_AWS_REGION=us-east-1
REACT_APP_USER_POOL_ID=<CognitoUserPoolId>
REACT_APP_USER_POOL_CLIENT_ID=<CognitoUserPoolClientId>
REACT_APP_API_ENDPOINT=<ApiGatewayUrl>
```

## Step 3 – Run the Frontend Locally

```bash
cd frontend
npm install
npm start
```

Open [http://localhost:3000](http://localhost:3000).

## Step 4 – Deploy the Frontend with Amplify

```bash
# Install the Amplify CLI (one-time)
npm install -g @aws-amplify/cli

# From the frontend directory
amplify init      # initialize Amplify project
amplify add auth  # link to the Cognito User Pool created by SAM
amplify add api   # add API Gateway endpoint details
amplify publish   # build & deploy to Amplify Hosting
```

## Running Backend Tests

```bash
cd backend
pip install -r requirements-dev.txt
python -m pytest tests/ -v
```

## API Reference

All endpoints require a valid Cognito JWT in the `Authorization: Bearer <token>` header.

| Method | Path | Description |
|---|---|---|
| `POST` | `/upload` | Returns a pre-signed S3 PUT URL |
| `GET` | `/download?object_key=…` | Returns a pre-signed S3 GET URL |
| `DELETE` | `/delete` | Deletes a file from S3 |
| `GET` | `/files` | Lists files for the authenticated user |

### POST /upload

**Request body**
```json
{ "filename": "photo.jpg", "content_type": "image/jpeg" }
```

**Response**
```json
{
  "upload_url": "https://s3.amazonaws.com/…",
  "object_key": "<user-id>/uuid_photo.jpg",
  "expires_in": 300
}
```

### GET /download

**Query parameter**: `object_key=<user-id>/uuid_photo.jpg`

**Response**
```json
{ "download_url": "https://s3.amazonaws.com/…", "expires_in": 300 }
```

### DELETE /delete

**Request body**
```json
{ "object_key": "<user-id>/uuid_photo.jpg" }
```

### GET /files

**Response**
```json
{
  "files": [
    {
      "object_key": "<user-id>/uuid_photo.jpg",
      "name": "uuid_photo.jpg",
      "size": 102400,
      "last_modified": "2024-01-01T12:00:00+00:00"
    }
  ],
  "count": 1
}
```

## Security Notes

- All S3 objects are stored with **Block Public Access** enabled.
- Each user's files are isolated under their own Cognito `sub` prefix.
- Lambda functions enforce ownership checks before serving or deleting files.
- Pre-signed URLs expire after **5 minutes**.
- S3 bucket versioning is enabled; old versions are purged after **30 days**.