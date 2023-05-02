import os
import json
import time
import boto3

fsx_client = boto3.client('fsx')


FSX_PATH = os.getenv('FSX_PATH')
FSX_SYSTEM_ID = os.getenv('FSX_SYSTEM_ID')
S3_BUCKET_NAME = os.getenv('S3_BUCKET_NAME')


# function that creates fsx repository export task
def create_export_task():
    return fsx_client.create_data_repository_task(
        Type='EXPORT_TO_REPOSITORY',
        Paths=[FSX_PATH],
        FileSystemId=FSX_SYSTEM_ID,
        Report={'Enabled': False}
    )


# function to calculate average reserves
def calculate_average_reserves():
    s3 = boto3.client("s3")
    total_reserves = 0.0
    for obj in s3.list_objects(Bucket=S3_BUCKET_NAME, Prefix=FSX_PATH)['Contents']:
        if obj['Size'] > 0:
            obj_key = obj['Key']
            if obj_key.endswith('.txt'):
                file_reserves = s3.get_object(Bucket=S3_BUCKET_NAME, Key=obj_key)['Body'].read().decode('utf-8').strip()
                total_reserves += float(file_reserves)

    return total_reserves


# function to check for repository task status
def check_task_status():
    return fsx_client.describe_data_repository_tasks(
            Filters=[
                {
                    'Name': 'file-system-id',
                    'Values': [
                        FSX_SYSTEM_ID,
                    ]
                },
            ]
        )


# lambda handler
def lambda_handler(event, context):
    create_export_task()
    status_response = check_task_status()
    while status_response['DataRepositoryTasks'][0]['Lifecycle'] != 'SUCCEEDED':
        status_response = check_task_status()
        time.sleep(5)

    average_reserves = calculate_average_reserves()
    print("The total reserves value is: ", average_reserves)