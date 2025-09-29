# mcf-datapipeline-poc
MCF Datapipeline POC

This pipeline automates the ingestion, processing, and storage of files (e.g., CSV, parquet) using scalable AWS services. It is designed to handle real-time file uploads, apply transformations, and store results for downstream database. The failed data are captured in a seperate file to send back to the source.

**File Upload**

User or system uploads a file to an S3 bucket.

S3 triggers an event notification to the AWS Event bridge.

**Event Handling**

Lambda reads the event from the event bridge and performs:

File validation (type, size, schema)

Metadata extraction (e.g., filename, timestamp, user ID)

Transformation (e.g., parsing CSV, resizing images)

Data storage in RDS

**Storage**

Metadata or extracted data is stored in AWS RDS.

Processed files and failed data are saved to a separate S3 locations.

**Monitoring**

CloudWatch tracks metrics (e.g., file count, processing time) and logs errors for debugging.


**Solution Overview**

<img width="1358" height="564" alt="image" src="https://github.com/user-attachments/assets/b6b70660-ec8f-47f1-a24e-23c0b0f81e32" />
