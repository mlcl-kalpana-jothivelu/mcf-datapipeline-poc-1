#!/bin/bash

# Define variables
PACKAGE_DIR="lambda_package"
ZIP_FILE="lambda_function.zip"
LAMBDA_FILE="index.py"

# Clean up previous builds
rm -rf $PACKAGE_DIR $ZIP_FILE

# Create package directory
mkdir $PACKAGE_DIR

# Install dependencies into the package directory
pip3 install -r requirements.txt -t $PACKAGE_DIR

# Copy your lambda function into the package
cp $LAMBDA_FILE $PACKAGE_DIR/

# Zip the contents
cd $PACKAGE_DIR
zip -r ../$ZIP_FILE .
cd ..

echo "✅ Lambda deployment package created: $ZIP_FILE"


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

AWS_REGION="ap-southeast-2"
TFSTATE_BUCKET="tfstate-145400477145"
REPO="mcf-datapipeline-poc"


# Initialize and apply Terraform
terraform init -reconfigure \
 "-backend-config=region=${AWS_REGION}" \
 "-backend-config=bucket=${TFSTATE_BUCKET}" \
 "-backend-config=key=${REPO}/terraform.tfstate"
 
#terraform init 
terraform plan
terraform apply -auto-approve

echo "Deployment complete!"
echo "S3 Bucket: $(terraform output -raw s3_bucket_name)"
echo "Lambda Function: $(terraform output -raw lambda_function_name)"
echo "RDS Endpoint: $(terraform output -raw rds_endpoint)"