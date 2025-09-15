# S3 upload/download (mocked with minio)
import boto3

def get_s3_client():
	# Mocked local minio
	return boto3.client(
		's3',
		endpoint_url='http://localhost:9000',
		aws_access_key_id='minioadmin',
		aws_secret_access_key='minioadmin',
		region_name='us-east-1'
	)

def upload_file(bucket, key, data):
	s3 = get_s3_client()
	s3.put_object(Bucket=bucket, Key=key, Body=data)

def download_file(bucket, key):
	s3 = get_s3_client()
	obj = s3.get_object(Bucket=bucket, Key=key)
	return obj['Body'].read()
