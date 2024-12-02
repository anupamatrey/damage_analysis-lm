import json
import logging
from config.aws_client import aws_clients
from services.s3_service import S3Service

# Configure logging
logger = logging.getLogger()
if logger.handlers:
    for handler in logger.handlers:
        logger.removeHandler(handler)

logging.basicConfig(
    format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.INFO
)

def lambda_handler(event, context):
    logger.info(">>> START EXECUTION >>>")
    logger.info("Received Event: %s", event)
    logger.info("Received Context: %s", context)

    try:
        # Initialize S3 service with the client
        s3_service = S3Service(aws_clients['s3'])
        
        # Example usage
        image_keys = s3_service.list_jpg_images('your-bucket-name')
        logger.info("Found images: %s", image_keys)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "hello " + event.get('name', 'World'),
                "images": image_keys
            }),
        }
    except Exception as e:
        logger.error("Error in lambda execution: %s", str(e))
        return {
            "statusCode": 500,
            "body": json.dumps({
                "message": f"Internal server error: {str(e)}"
            }),
        }
