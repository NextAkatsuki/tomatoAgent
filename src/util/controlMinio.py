import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

class ControlMinio:
    def __init__(self, minio_endpoint, bucket_name, access_key, secret_key):
        # S3 클라이언트 생성
        self.s3_client = boto3.client(
            's3',
            endpoint_url=minio_endpoint,           # MinIO 서버 URL
            aws_access_key_id=access_key,          # 인증 정보
            aws_secret_access_key=secret_key,
            config=Config(signature_version='s3v4')  # S3 API 버전
        )
        self.bucket_name = bucket_name


    def putItem(self, userId, category, data):
        self.s3_client.put_object(Bucket=self.bucket_name, Key=f"{userId}_{category}.pkl", Body=data)


    def getItem(self, userId, category):
        file_key = f"{userId}_{category}.pkl"
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=file_key)
        
            response = self.s3_client.get_object(Bucket=self.bucket_name, Key=file_key)
            return response['Body'].read()
        except ClientError as e:
            if e.response['Error']['Code'] == "404":
                raise Exception(f"File '{file_key}' does not exist in bucket '{self.bucket_name}'.")
            else:
                raise Exception(f"An error occurred: {e}")


    def deleteItem(self, userId, category):
        self.s3_client.delete_object(Bucket=self.bucket_name, Key=f"{userId}_{category}.pkl")
          
    
