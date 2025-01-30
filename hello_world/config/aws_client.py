# hello_world/config/aws_config.py
import boto3
import os
from botocore.config import Config
import logging
from botocore.exceptions import ClientError


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_base_config():
    """Get base configuration for AWS clients"""
    return Config(
        retries=dict(
            max_attempts=3
        ),
        connect_timeout=120,
        read_timeout=120
    )
def get_s3_client():
    """Initialize S3 client"""
    try:
        config = get_base_config()
        s3_client = boto3.client(
            service_name='s3',
            region_name=os.getenv('AWS_REGION', 'us-east-1'),
            config=config
        )
        logger.info("S3 client initialized successfully")
        return s3_client
    except Exception as e:
        logger.error(f"Failed to initialize S3 client: {str(e)}")
        raise Exception(f"Failed to initialize S3 client: {str(e)}")
    
def get_rekognition_client():
    """Initialize Rekognition client"""
    try:
        config = get_base_config()
        rekognition_client = boto3.client(
            service_name='rekognition',
            region_name=os.getenv('AWS_REGION', 'us-east-1'),
            config=config
        )
        logger.info("Rekognition client initialized successfully")
        return rekognition_client
    except Exception as e:
        logger.error(f"Failed to initialize Rekognition client: {str(e)}")
        raise

    
# config/aws_client.py
def get_bedrock_client():
    """Initialize Bedrock runtime client"""
    try:
        config = Config(
            retries=dict(
                max_attempts=3,  # Base retry attempts
                mode='adaptive'  # Use adaptive mode for better handling
            ),
            connect_timeout=120,
            read_timeout=120,
            region_name=os.environ.get('AWS_REGION', 'us-east-1')
        )
        
        bedrock_client = boto3.client(
            service_name='bedrock-runtime',
            config=config
        )
        logger.info("Bedrock client initialized successfully")
        return bedrock_client
    except Exception as e:
        logger.error(f"Failed to initialize Bedrock client: {str(e)}")
        raise

def initialize_aws_clients():
    """Initialize all AWS clients"""
    try:
        clients = {}
        
        # Initialize S3
        logger.info("Initializing S3 client...")
        clients['s3'] = get_s3_client()
        
        # Initialize Rekognition
        logger.info("Initializing Rekognition client...")
        clients['rekognition'] = get_rekognition_client()
        
        # Initialize Bedrock
        logger.info("Initializing Bedrock client...")
        clients['bedrock'] = get_bedrock_client()
        
        logger.info("All AWS clients initialized successfully")
        return clients

    except Exception as e:
        logger.error(f"Failed to initialize AWS clients: {str(e)}")
        raise

# Create AWS session and initialize clients
try:
    aws_clients = initialize_aws_clients()
except Exception as e:
    logger.error(f"Failed to set up AWS environment: {str(e)}")
    raise
