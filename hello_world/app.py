import json
import logging
import os
from typing import Any, Dict, List
import datetime
from config.aws_client import aws_clients
from services.s3_service import S3Service
from services.rekognition_service import RekognitionService
from services.bedrock_service import BedrockService
from services.multiimagedamage_analyzer import MultiImageDamageAnalyzer

# Constants
SUCCESS_STATUS_CODE = 200
ERROR_STATUS_CODE = 500
CONTENT_TYPE_JSON = "application/json"

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

def initialize_services():
    """Initialize all services"""
    try:
        return {
            's3': S3Service(aws_clients['s3']),
            'rekognition': RekognitionService(aws_clients['rekognition']),
            'bedrock': BedrockService(aws_clients['bedrock'])
        }
    except Exception as e:
        logger.error(f"Failed to initialize services: {str(e)}")
        raise

def create_error_response(error_message: str, status_code: int = ERROR_STATUS_CODE) -> Dict:
    """Create standardized error response."""
    return {
        "statusCode": status_code,
        "body": json.dumps({
            "message": f"Internal server error: {error_message}"
        }),
        "headers": {"Content-Type": CONTENT_TYPE_JSON}
    }
def format_analysis_results(results: Dict, analysis_timestamp: str) -> List[Dict]:
    """Format analysis results into a standardized structure."""

    formatted_results = []

    # Debug logging
    logger.info(f"Results type: {type(results)}")
    logger.info(f"Results content: {results}")

    # Process a single result dictionary instead of a list
    damage_labels = results.get('damage_labels', [])

    # Extract confidence scores if available
    confidence_scores = [label.get('Confidence', 0.0) for label in damage_labels]
    average_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.0

    analysis_entry = {
        "source_image": results.get('source_key', ''),
        "analysis": {
            "damage_labels": damage_labels,
            "analysis_timestamp": analysis_timestamp,
            "confidence_score": average_confidence  # Use average if multiple labels exist
        }
    }

    logger.info(
        f"Analysis completed for image {results.get('source_key', '')}",
        extra={"analysis_entry": analysis_entry}
    )

    formatted_results.append(analysis_entry)

    return formatted_results

def format_analysis_results1(results: List[Dict], analysis_timestamp: str) -> List[Dict]:
    """Format analysis results into standardized structure."""
    formatted_results = []
    # Debug logging
    logger.info(f"Results type: {type(results)}")
    logger.info(f"Results content: {results}")

    for result in results:
        # Debug logging
        logger.info(f"Result type: {type(result)}")
        logger.info(f"Result content: {result}")
        analysis_entry = {
            "source_image": result.get('source_key', ''),
            "analysis": {
                "damage_labels": result.get('damage_labels', []),
                "analysis_timestamp": analysis_timestamp,
                "confidence_score": result.get('confidence', 0.0)
            }
        }
        logger.info(
            f"Analysis completed for image {result.get('source_key', '')}", 
            extra={"analysis_entry": analysis_entry}
        )
        formatted_results.append(analysis_entry)
    return formatted_results

def log_response(response: Dict, processing_duration: float, event: Dict):
    """
    Log detailed response to CloudWatch
    """
    try:
        log_entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "event_type": "ImageProcessingComplete",
            "processing_duration_seconds": processing_duration,
            "input_event": event,
            "response": response,
        }
        
        # Log as JSON string for better CloudWatch insights
        logger.info(f"Processing Complete - Full Response: {json.dumps(log_entry, indent=2)}")
        
    except Exception as e:
        logger.error(f"Error logging response: {str(e)}")


def lambda_handler(event: Dict, context: Any) -> Dict:
    """Lambda handler for processing single image"""
    start_time = datetime.datetime.now()
    logger.info(">>> START EXECUTION >>> : %s",event)

    try:
        # Extract source_key from S3 event
        try:
            source_key = event['Records'][0]['s3']['object']['key']
            logger.info(f"Extracted source_key: {source_key}")
        except KeyError:
            raise ValueError("Unable to extract image key from event")
        
        if not source_key:
            raise ValueError("image key cannot be empty")

        # Initialize services
        services = initialize_services()
        logger.info("Services initialized successfully")
        # Log the initialization of services
        logger.info(
            "Services initialized",
            extra={
                "s3_service": str(services['s3']),
                "rekognition_service": str(services['rekognition']),
                "bedrock_service": str(services['bedrock'])
            }
        )
        # Initialize analyzer with services
        analyzer = MultiImageDamageAnalyzer(
            s3_service=services['s3'],
            rekognition_service=services['rekognition'],
            bedrock_service=services['bedrock']
        )

        # Get configuration from environment variables
        source_bucket = os.getenv('SOURCE_BUCKET', 'damage-analyzer1124-test')
        output_bucket = os.getenv('OUTPUT_BUCKET', 'damage-analyzer1124-test')

        logger.info(f"Source bucket: {source_bucket}, Output bucket: {output_bucket}")

        if not source_bucket or not output_bucket:
            raise ValueError("SOURCE_BUCKET and OUTPUT_BUCKET environment variables must be set")


        # Perform analysis
        # Perform analysis with source_key
        analysis_results = analyzer.process_single_image(
            source_bucket=source_bucket,
            source_key=source_key,  # Pass the source_key here
            output_bucket=output_bucket
        )
       # Calculate processing duration
        processing_duration = (datetime.datetime.now() - start_time).total_seconds()


        # Format the results
        analysis_timestamp = datetime.datetime.now().isoformat()
        formatted_results = format_analysis_results(analysis_results, analysis_timestamp)

        # Calculate processing duration
        end_time = datetime.datetime.now()
        processing_duration = (end_time - start_time).total_seconds()

        # Prepare the response
        response = {
            "statusCode": SUCCESS_STATUS_CODE,
            "body": json.dumps({
                "message": "Image analysis completed successfully",
                "analysis_results": formatted_results,
                "total_images_analyzed": len(analysis_results),
                "processing_duration_seconds": processing_duration,
                "source_bucket": source_bucket,
                "output_bucket": output_bucket
            }),
            "headers": {"Content-Type": CONTENT_TYPE_JSON}
        }

        # Log the final response
        # Log detailed response to CloudWatch
        log_response(response, processing_duration, event)

        # Add headers to response
        response["headers"] = {"Content-Type": "application/json"}
        
        # Convert body to JSON string for Lambda response
        response["body"] = json.dumps(response["body"])
        return response

    except KeyError as e:
        error_msg = f"Missing required configuration or service: {str(e)}"
        logger.error(error_msg)
        return create_error_response(error_msg)
    
    except ValueError as e:
        error_msg = f"Invalid input or configuration: {str(e)}"
        logger.error(error_msg)
        return create_error_response(error_msg)
    
    except Exception as e:
        error_msg = f"Unexpected error during execution: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return create_error_response(error_msg)
    
    finally:
        logger.info("<<< END EXECUTION <<<")
