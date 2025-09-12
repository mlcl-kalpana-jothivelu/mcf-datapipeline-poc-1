#!/bin/bash

echo "Creating Lambda deployment package..."

# Clean up previous builds
rm -rf package
rm -f lambda_function.zip

# Create package directory
mkdir -p package

# Install dependencies for Lambda
pip3 install -r requirements.txt -t package

# Copy Lambda function
cp index.py package

# Create deployment package
cd package
zip -r ../lambda_function.zip .
cd ..

echo "Lambda deployment package created: lambda_function.zip"

echo "Enabling EventBridge for S3 at account level..."

# Enable EventBridge for S3
aws s3api put-bucket-notification-configuration \
    --bucket $(terraform output -raw s3_bucket_name) \
    --notification-configuration '{"EventBridgeConfiguration": {}}'

echo "EventBridge enabled for S3 bucket"

# Verify the configuration
echo "Verifying bucket notification configuration:"
aws s3api get-bucket-notification-configuration --bucket $(terraform output -raw s3_bucket_name)

# Add the Lambda function code
# zip -g lambda_function.zip fileparser.py

#!/bin/bash

echo "Testing S3 to EventBridge integration..."

BUCKET_NAME=$(terraform output -raw s3_bucket_name)
echo "S3 Bucket: $BUCKET_NAME"

# Create a test file
echo "id,name,email" > test_eventbridge.csv
echo "1,Test User,test@email.com" >> test_eventbridge.csv

# Upload file to S3
echo "Uploading test file to S3..."
aws s3 cp test_eventbridge.csv s3://$BUCKET_NAME/test_eventbridge.csv

echo "File uploaded. Now checking EventBridge..."

# Wait a moment for the event to be processed
sleep 5

# Check EventBridge rules
echo "EventBridge Rules:"
aws events list-rules --name-prefix mcf-data-pipeline-s3-events

# Check recent events in EventBridge
echo "Recent EventBridge events:"
aws logs describe-log-groups --log-group-name-prefix "/aws/events/rule"

# Clean up
rm test_eventbridge.csv

echo "Test complete. Check CloudWatch logs for EventBridge events."


# Initialize and apply Terraform
terraform init
terraform plan
terraform apply -auto-approve

echo "Deployment complete!"
echo "S3 Bucket: $(terraform output -raw s3_bucket_name)"
echo "Lambda Function: $(terraform output -raw lambda_function_name)"
echo "RDS Endpoint: $(terraform output -raw rds_endpoint)"