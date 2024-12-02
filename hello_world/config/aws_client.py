# hello_world/config/aws_config.py
import boto3

def init_aws_clients():
    """Initialize AWS clients"""
    return {
        's3': boto3.client('s3'),
        # Add other AWS clients as needed
        # 'dynamodb': boto3.client('dynamodb'),
        # 'sns': boto3.client('sns'),
    }

aws_clients = init_aws_clients()
