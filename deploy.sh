#!/bin/bash
echo "Creating Lambda deployment package..."

# Clean up previous builds
rm -rf package/
rm -f lambda_function.zip

# Create package directory
mkdir -p package

pip3 install -r requirements.txt -t package/ --platform linux_x86_64 --implementation cp --python-version 3.9 --only-binary=:all: --upgrade

# Copy Lambda function (renamed to index.py)
cp index.py package/

# Verify psycopg2 is installed
echo "Verifying psycopg2 installation..."
ls -la package/ | grep psycopg2 || echo "WARNING: psycopg2 not found in package"

# Create deployment package
cd package
zip -r ../lambda_function.zip .
cd ..

echo "Lambda deployment package created: lambda_function.zip"
echo "Package size: $(du -h lambda_function.zip | cut -f1)"

# List package contents to verify
echo "Package contents:"
unzip -l lambda_function.zip | head -20


# # Install dependencies for Lambda
# pip install -r requirements.txt -t ./package/

# # Copy Lambda function
# cp index.py package/

# # Create deployment package
# cd package
# zip -r ../lambda_function.zip .
# cd ..

# echo "Lambda deployment package created: lambda_function.zip"



# echo "Enabling EventBridge for S3 at account level..."

# # Enable EventBridge for S3
# aws s3api put-bucket-notification-configuration \
#     --bucket $(terraform output -raw s3_bucket_name) \
#     --notification-configuration '{"EventBridgeConfiguration": {}}'

# echo "EventBridge enabled for S3 bucket"

# # Verify the configuration
# echo "Verifying bucket notification configuration:"
# aws s3api get-bucket-notification-configuration --bucket $(terraform output -raw s3_bucket_name)

# Add the Lambda function code
# zip -g lambda_function.zip index.py



# Initialize and apply Terraform
terraform init
terraform plan
terraform apply -auto-approve

echo "Deployment complete!"
echo "S3 Bucket: $(terraform output -raw s3_bucket_name)"
echo "Lambda Function: $(terraform output -raw lambda_function_name)"
echo "RDS Endpoint: $(terraform output -raw rds_endpoint)"