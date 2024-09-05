#!/bin/sh

if [ -z "$BUCKET_NAME" ] || [ -z "$AWS_ACCESS_KEY_ID" ] || [ -z "$AWS_SECRET_ACCESS_KEY" ] || [ -z "$AWS_ENDPOINT_URL" ]; then
    echo "Error: Required environment variables are not set."
    echo "Please set BUCKET_NAME, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and AWS_ENDPOINT_URL."
    exit 1
fi

echo "Emptying bucket: $BUCKET_NAME"
aws s3 rm s3://$BUCKET_NAME --recursive --endpoint-url $AWS_ENDPOINT_URL

echo "Bucket emptying process completed."