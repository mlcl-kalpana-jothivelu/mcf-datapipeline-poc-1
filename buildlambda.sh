#!/bin/bash

# Define variables
PACKAGE_DIR="lambda_package"
ZIP_FILE="lambda_function2.zip"
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