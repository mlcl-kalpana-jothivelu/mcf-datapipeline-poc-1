# mcf-datapipeline-poc
MCF Datapipeline POC


#!/bin/bash

echo "=== RDS Configuration Check ==="

# Get RDS endpoint
RDS_ENDPOINT=$(terraform output -raw rds_endpoint)
echo "RDS Endpoint: $RDS_ENDPOINT"

# Check RDS instance details
echo "RDS Instance Details:"
aws rds describe-db-instances --query 'DBInstances[0].{VpcId:DBSubnetGroup.VpcId,PubliclyAccessible:PubliclyAccessible,SecurityGroups:VpcSecurityGroups}'

# Check RDS security groups
echo "RDS Security Groups:"
aws rds describe-db-instances --query 'DBInstances[0].VpcSecurityGroups[*].VpcSecurityGroupId'




#!/bin/bash

echo "=== Network Connectivity Test ==="

# Get Lambda function details
LAMBDA_NAME=$(terraform output -raw lambda_function_name)
RDS_ENDPOINT=$(terraform output -raw rds_endpoint)

# Test Lambda to RDS connectivity
echo "Testing Lambda to RDS connectivity..."
aws lambda invoke \
    --function-name $LAMBDA_NAME \
    --payload '{"test": "connectivity"}' \
    /tmp/lambda-response.json

echo "Lambda response:"
cat /tmp/lambda-response.json
