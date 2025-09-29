import json
import boto3
import pandas as pd
import io
import re
import psycopg2
import os
from urllib.parse import unquote_plus
 
def handler(event, context):

    print(f"Received event: {json.dumps(event)}")

    # S3 details
    bucket_name = os.environ['S3_BUCKET']
    input_key = 'input-data.csv'
    output_key = 'failed-records-{input_key}.csv'
 
    # PostgreSQL connection details
    db_host = os.environ['DB_HOST']
    db_name = os.environ['DB_NAME']
    db_user = os.environ['DB_USER']
    db_port = os.environ.get('DB_PORT', '5432')
    db_password = "TempPass123!"
    #db_password = os.environ['DB_PASSWORD']    
    
    # Connect to S3
    s3 = boto3.client('s3')

    try:
        # Handle EventBridge event format
        if 'detail' in event:
            # EventBridge event format
            bucket = event['detail']['bucket']['name']
            key = event['detail']['object']['key']
            file_size = event['detail']['object'].get('size', 0)
            
            print(f"Processing EventBridge event for: s3://{bucket}/{key}")
            #print(boto3.client('s3').list_buckets())
            # Download file from S3
            response = s3.get_object(Bucket=bucket, Key=key)
            file_content = response['Body'].read()

            print(f"Downloaded S3 file for: s3://{bucket}/{key}")
            
            # Store file metadata in PostgreSQL
            #store_file_metadata(db_host, db_name, db_user, db_password, bucket, key, len(file_content))

            process_file_content(db_host, db_port, db_name, db_user, db_password, bucket, key, file_content, s3)
            
        else:
            # Handle S3 direct event format (if needed)
            for record in event.get('Records', []):
                if 's3' in record:
                    bucket = record['s3']['bucket']['name']
                    key = unquote_plus(record['s3']['object']['key'])
                    processed_key = key.replace("raw/", "processed/")
                    
                    print(f"Processing S3 direct event for: s3://{bucket}/{key}")
                    
                    response = s3.get_object(Bucket=bucket, Key=key)
                    file_content = response['Body'].read()
                    
                    #store_file_metadata(db_host, db_name, db_user, db_password, bucket, key, len(file_content))
                    process_file_content(db_host, db_port, db_name, db_user, db_password, bucket, key, file_content, s3)

                    #s3.rename_object(Bucket=bucket, Key=key, CopySource={'Bucket': bucket, 'Key': key}, MetadataDirective='REPLACE', Metadata={'status': 'processed'})
                    # s3.copy_object(Bucket=bucket, Key=processed_key, CopySource={'Bucket': bucket, 'Key': key}, MetadataDirective='REPLACE', Metadata={'status': 'processed'})
                    # s3.delete_object(Bucket=bucket, Key=key)

                    #print(f"Renamed processed file to indicate status: s3://{bucket}/{key} to s3://{bucket}/{processed_key}")

    except Exception as e:
        print(f"Error processing event: {e}")
        raise e
    
    return {
        'statusCode': 200,
        'body': json.dumps('File processed successfully')
    }

def process_file_content(db_host, db_port, db_name, db_user, db_password, bucket, key, file_content, s3):
    """
    Process file content and insert records into PostgreSQL
    """

    print(f"Starting processing file content")

    try:
        # Determine file type based on extension
        file_extension = key.lower().split('.')[-1]        
        if file_extension == 'csv':
            # Read CSV content into DataFrame
            df = pd.read_csv(io.StringIO(file_content.decode('utf-8')))            
            print(f"CSV DataFrame loaded with {len(df)} records")

            process_data_frame(db_host, db_port, db_name, db_user, db_password, bucket, key, s3, df)

        elif file_extension == 'parquet':
           # df = pd.read_parquet("data.parquet", engine="fastparquet")  # or engine="pyarrow"
            df = pd.read_parquet(io.BytesIO(file_content), engine="fastparquet")
            print(f"Parquet DataFrame loaded with {len(df)} records")

            process_data_frame(db_host, db_port, db_name, db_user, db_password, bucket, key, s3, df)

        else:
            print(f"Unsupported file type: {file_extension}")
            
    except Exception as e:
        print(f"Error processing file content: {str(e)}")
        raise e
    
def sanitize_int(value):
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None  # or handle as needed

    
def process_data_frame(db_host, db_port, db_name, db_user, db_password, bucket, key, s3, df):
    """
    Process data frame content and insert records into PostgreSQL
    """
    print(f"Processing data frame content")

    try:
        # Email validation regex (basic)
        email_pattern = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")

        # Validate and clean data
        valid_rows = pd.DataFrame(columns=df.columns)
        failed_rows = pd.DataFrame(columns=df.columns)

        for _, row in df.iterrows():
            member_id = row.get('member_id')
            email = row.get('email')

            # Check for invalid memberId or invalid email format
            invalid_member_id = pd.isnull(member_id) or str(member_id).strip() == ''
            invalid_email = pd.isnull(email) or not email_pattern.match(str(email).strip())

            # Convert row to DataFrame
            row_df = pd.DataFrame([row])

            if invalid_member_id or invalid_email:
                failed_rows = pd.concat([failed_rows, row_df], ignore_index=True)
            else:
                valid_rows = pd.concat([valid_rows, row_df], ignore_index=True)
    
            # if pd.isnull(member_id) or str(member_id).strip() =='':
            #     failed_rows = failed_rows.append(row.to_dict())
            # elif pd.isnull(email) or '@' not in str(email):
            #     failed_rows = failed_rows.append(row.to_dict())
            # else:
            #     valid_rows = valid_rows.append(row.to_dict())

        # Summary
        print(f"✅ Valid rows: {len(valid_rows)}")
        print(f"❌ Invalid rows: {len(failed_rows)}")

        # Insert or update valid rows in PostgreSQL
        if not valid_rows.empty:

            try:
                conn = psycopg2.connect(
                    host=db_host,
                    dbname=db_name,
                    user=db_user,
                    password=db_password,
                    port=db_port
                )

                cursor = conn.cursor() 
                for _, row in valid_rows.iterrows():
                    # Example assumes member_id is unique

                    print(f"Upserting member_id: {row['member_id']} with {row.to_dict()}")
                    cursor.execute("""

                        INSERT INTO member (member_id, name, email, date_of_birth)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (member_id) DO UPDATE
                        SET name = EXCLUDED.name,
                            email = EXCLUDED.email,
                            date_of_birth = EXCLUDED.date_of_birth;
                    """, (
                        row['member_id'],
                        row['name'],
                        row['email'],
                        row['date_of_birth']
                    ))
 
                conn.commit()
                cursor.close()
                conn.close()
 
            except Exception as e:
                print(f"Database error: {str(e)}")
                raise e

        # Upload failed rows to S3

        if not failed_rows.empty:
            fail_key = key.replace("raw/", "failed-records/")
            failed_csv_buffer = io.StringIO()

            failed_rows.to_csv(failed_csv_buffer, index=False)
            s3.put_object(Bucket=bucket, Key=f'{fail_key}', Body=failed_csv_buffer.getvalue())
            print(f"Uploaded failed records to s3://{bucket}/{fail_key}")

    except Exception as e:
        print(f"Error processing CSV file: {str(e)}")
        raise e