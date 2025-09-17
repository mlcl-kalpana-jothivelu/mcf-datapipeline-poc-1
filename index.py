import json
import boto3
import psycopg2
import os
from urllib.parse import unquote_plus

def handler(event, context):
    """
    Lambda function to process S3 events from EventBridge
    """
    print(f"Received event: {json.dumps(event)}")
    
    # Initialize S3 client
    s3_client = boto3.client('s3')
    
    # Get environment variables
    bucket_name = os.environ['S3_BUCKET']
    db_host = os.environ['DB_HOST']
    db_name = os.environ['DB_NAME']
    db_user = os.environ['DB_USER']
    db_password = "TempPass123!"
    # os.environ['DB_PASSWORD']
    
    try:
        # Handle EventBridge event format
        if 'detail' in event:
            # EventBridge event format
            bucket = event['detail']['bucket']['name']
            key = event['detail']['object']['key']
            file_size = event['detail']['object'].get('size', 0)
            
            print(f"Processing EventBridge event for: s3://{bucket}/{key}")
            
            # Download file from S3
            response = s3_client.get_object(Bucket=bucket, Key=key)
            file_content = response['Body'].read()

            print(f"Downloaded S3 file for: s3://{bucket}/{key}")
            
            # Store file metadata in PostgreSQL
            #store_file_metadata(db_host, db_name, db_user, db_password, bucket, key, len(file_content))

            process_file_content(db_host, db_name, db_user, db_password, bucket, key, file_content)
            
        else:
            # Handle S3 direct event format (if needed)
            for record in event.get('Records', []):
                if 's3' in record:
                    bucket = record['s3']['bucket']['name']
                    key = unquote_plus(record['s3']['object']['key'])
                    
                    print(f"Processing S3 direct event for: s3://{bucket}/{key}")
                    
                    response = s3_client.get_object(Bucket=bucket, Key=key)
                    file_content = response['Body'].read()
                    
                    #store_file_metadata(db_host, db_name, db_user, db_password, bucket, key, len(file_content))
                    process_file_content(db_host, db_name, db_user, db_password, bucket, key, file_content)
    except Exception as e:
        print(f"Error processing event: {str(e)}")
        raise e
    
    return {
        'statusCode': 200,
        'body': json.dumps('File processed successfully')
    }

# def store_file_metadata(db_host, db_name, db_user, db_password, bucket, key, file_size):
#     """
#     Store file metadata in PostgreSQL database
#     """
#     try:
#         # Connect to database
#         conn = psycopg2.connect(
#             host=db_host,
#             database=db_name,
#             user=db_user,
#             password=db_password,
#             port=5432
#         )
        
#         cursor = conn.cursor()
        
#         # Create table if it doesn't exist
#         cursor.execute("""
#             CREATE TABLE IF NOT EXISTS file_metadata (
#                 id VARCHAR PRIMARY KEY,
#                 first_name VARCHAR(255),
#                 surname VARCHAR(500),
#                 date_of_birth DATE,
#                 gender VARCHAR(50),       
#                 created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#             )
#         """)
#         # cursor.execute("""
#         #     CREATE TABLE IF NOT EXISTS file_metadata (
#         #         id SERIAL PRIMARY KEY,
#         #         bucket_name VARCHAR(255),
#         #         file_key VARCHAR(500),
#         #         file_size BIGINT,
#         #         created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#         #     )
#         # """)
        
#         # Insert file metadata
#         cursor.execute("""
#             INSERT INTO file_metadata (bucket_name, file_key, file_size)
#             VALUES (%s, %s, %s)
#         """, (bucket, key, file_size))
        
#         conn.commit()
#         cursor.close()
#         conn.close()
        
#         print(f"Stored metadata for {bucket}/{key}")
        
#     except Exception as e:
#         print(f"Database error: {str(e)}")
#         raise e
    

def process_file_content(db_host, db_name, db_user, db_password, bucket, key, file_content):
    """
    Process file content and insert records into PostgreSQL
    """

    print(f"Starting processing file content")

    try:
        # Determine file type based on extension
        file_extension = key.lower().split('.')[-1]
        
        if file_extension == 'csv':
            process_csv_file(db_host, db_name, db_user, db_password, bucket, key, file_content)
        elif file_extension == 'parquet':
            process_parquet_file(db_host, db_name, db_user, db_password, bucket, key, file_content)
        else:
            print(f"Unsupported file type: {file_extension}")
            
    except Exception as e:
        print(f"Error processing file content: {str(e)}")
        raise e

def process_csv_file(db_host, db_name, db_user, db_password, bucket, key, file_content):
    """
    Process CSV file and insert records into structured table
    """

    print(f"Starting processing CSV file")

    try:
        # Decode file content
        content_str = file_content.decode('utf-8')
        csv_reader = csv.DictReader(io.StringIO(content_str))
        
        # Get column names and sample data
        columns = csv_reader.fieldnames
        sample_rows = []
        
        # Read first few rows to determine column types
        for i, row in enumerate(csv_reader):
            sample_rows.append(row)
            if i >= 5:  # Sample first 5 rows
                break
        
        conn = psycopg2.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_password,
            port=5432
        )
        
        cursor = conn.cursor()
        
        # Create table name from file name
        table_name = "MEMBER"
        # f"data_{sanitize_table_name(key)}"
        
        # Determine column types
        column_definitions = determine_column_types(columns, sample_rows)
        
        # Create table
        create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id SERIAL PRIMARY KEY,
                source_file VARCHAR(500),
                {', '.join([f'"{col}" {col_type}' for col, col_type in column_definitions.items()])},
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        
        cursor.execute(create_table_sql)
        print(f"Created/verified table: {table_name}")
        
        # Insert records
        records_inserted = 0
        
        # Reset CSV reader to beginning
        csv_reader = csv.DictReader(io.StringIO(content_str))
        
        for row in csv_reader:
            # Prepare values for insertion
            values = [key]  # source_file
            placeholders = ['%s']  # source_file placeholder
            
            for col in columns:
                value = row.get(col, '')
                # Convert empty strings to None for proper NULL handling
                if value == '':
                    value = None
                values.append(value)
                placeholders.append('%s')
            
            # Insert record
            insert_sql = f"""
                INSERT INTO {table_name} (source_file, {', '.join([f'"{col}"' for col in columns])})
                VALUES ({', '.join(placeholders)})
            """
            
            cursor.execute(insert_sql, values)
            records_inserted += 1
            
            # Limit to first 100 records for demo purposes
            if records_inserted >= 100:
                print(f"Inserted first 100 records from {key}")
                break
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"Inserted {records_inserted} records from CSV file: {key} into table: {table_name}")
        
    except Exception as e:
        print(f"Error processing CSV file: {str(e)}")
        raise e
def process_parquet_file(db_host, db_name, db_user, db_password, bucket, key, file_content):
    """
    Process Parquet file and insert records into structured table
    """

    print(f"Starting processing parquest file")
    
    try:
        # Read Parquet file from bytes
        parquet_file = io.BytesIO(file_content)
        table = pq.read_table(parquet_file)
        
        # Convert to pandas-like structure for easier processing
        df = table.to_pandas()
        
        # Get column names
        columns = list(df.columns)
        
        conn = psycopg2.connect(
            host=db_host,
            database=db_name,
            user=db_user,
            password=db_password,
            port=5432
        )
        
        cursor = conn.cursor()
        
        # Create table name from file name
        table_name = "MEMBER"
        # f"data_{sanitize_table_name(key)}"
        
        # Determine column types from Parquet schema
        column_definitions = determine_parquet_column_types(table.schema)
        
        # Create table
        create_table_sql = f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                id VARCHAR PRIMARY KEY,
                # first_name VARCHAR(255),
                # surname VARCHAR(500),
                # date_of_birth DATE,
                # gender VARCHAR(50),       
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            # CREATE TABLE IF NOT EXISTS {table_name} (
            #     id SERIAL PRIMARY KEY,
            #     source_file VARCHAR(500),
            #     {', '.join([f'"{col}" {col_type}' for col, col_type in column_definitions.items()])},
            #     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        #     )
        # """
        
        cursor.execute(create_table_sql)
        print(f"Created/verified table: {table_name}")
        
        # Insert records
        records_inserted = 0
        
        for index, row in df.iterrows():
            # Prepare values for insertion
            values = [key]  # source_file
            placeholders = ['%s']  # source_file placeholder
            
            for col in columns:
                value = row[col]
                # Convert pandas NaN to None for proper NULL handling
                if pd.isna(value):
                    value = None
                values.append(value)
                placeholders.append('%s')
            
            # Insert record
            insert_sql = f"""
                INSERT INTO {table_name} (source_file, {', '.join([f'"{col}"' for col in columns])})
                VALUES ({', '.join(placeholders)})
            """
            
            cursor.execute(insert_sql, values)
            records_inserted += 1
            
            # Limit to first 100 records for demo purposes
            if records_inserted >= 100:
                print(f"Inserted first 100 records from {key}")
                break
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"Inserted {records_inserted} records from Parquet file: {key} into table: {table_name}")
        
    except Exception as e:
        print(f"Error processing Parquet file: {str(e)}")
        raise e

def determine_column_types(columns, sample_data):
    """
    Determine PostgreSQL column types based on sample data
    """
    column_types = {}
    
    for col in columns:
        # Check if column contains numeric data
        is_numeric = True
        is_integer = True
        
        for row in sample_data:
            value = row.get(col, '')
            if value is None or value == '':
                continue
                
            # Check if it's a number
            try:
                float_val = float(str(value))
                if not float_val.is_integer():
                    is_integer = False
            except (ValueError, TypeError):
                is_numeric = False
                break
        
        # Determine column type
        if is_numeric:
            if is_integer:
                column_types[col] = 'INTEGER'
            else:
                column_types[col] = 'DECIMAL(10,2)'
        else:
            # Check max length for VARCHAR
            max_length = 0
            for row in sample_data:
                value = str(row.get(col, ''))
                max_length = max(max_length, len(value))
            
            # Set VARCHAR length (minimum 50, maximum 1000)
            varchar_length = max(50, min(max_length * 2, 1000))
            column_types[col] = f'VARCHAR({varchar_length})'
    
    return column_types

def determine_parquet_column_types(schema):
    """
    Determine PostgreSQL column types from Parquet schema
    """
    column_types = {}
    
    for field in schema:
        col_name = field.name
        col_type = field.type
        
        # Map Parquet types to PostgreSQL types
        if pa.types.is_integer(col_type):
            column_types[col_name] = 'INTEGER'
        elif pa.types.is_floating(col_type):
            column_types[col_name] = 'DECIMAL(10,2)'
        elif pa.types.is_boolean(col_type):
            column_types[col_name] = 'BOOLEAN'
        elif pa.types.is_date(col_type):
            column_types[col_name] = 'DATE'
        elif pa.types.is_timestamp(col_type):
            column_types[col_name] = 'TIMESTAMP'
        elif pa.types.is_string(col_type) or pa.types.is_large_string(col_type):
            column_types[col_name] = 'VARCHAR(500)'
        else:
            # Default to VARCHAR for unknown types
            column_types[col_name] = 'VARCHAR(500)'
    
    return column_types

def sanitize_table_name(filename):
    """
    Sanitize filename to create valid PostgreSQL table name
    """
    # Remove file extension
    name = filename.split('.')[0]
    
#     # Replace invalid characters with underscores
#     name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    
#     # Ensure it starts with a letter
#     if name[0].isdigit():
#         name = 'table_' + name
    
#     # Limit length
#     return name[:50]

