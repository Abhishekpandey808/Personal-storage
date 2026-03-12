/**
 * aws-exports.js
 *
 * Replace the placeholder values below with the actual outputs from your
 * SAM deployment (`sam deploy --guided`) and Cognito User Pool settings.
 *
 * You can retrieve them with:
 *   aws cloudformation describe-stacks --stack-name personal-storage-app \
 *     --query "Stacks[0].Outputs"
 */
const awsConfig = {
  Auth: {
    region: process.env.REACT_APP_AWS_REGION || "us-east-1",
    userPoolId: process.env.REACT_APP_USER_POOL_ID || "us-east-1_XXXXXXXXX",
    userPoolWebClientId: process.env.REACT_APP_USER_POOL_CLIENT_ID || "XXXXXXXXXXXXXXXXXXXXXXXXXX",
  },
  API: {
    endpoints: [
      {
        name: "PersonalStorageApi",
        endpoint: process.env.REACT_APP_API_ENDPOINT || "https://XXXXXXXXXX.execute-api.us-east-1.amazonaws.com/dev",
        region: process.env.REACT_APP_AWS_REGION || "us-east-1",
      },
    ],
  },
};

export default awsConfig;
