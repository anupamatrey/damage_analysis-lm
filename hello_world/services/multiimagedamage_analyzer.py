import boto3
from typing import Optional, Dict, List
from datetime import datetime
import logging
from services.s3_service import S3Service
from services.rekognition_service import RekognitionService
from services.bedrock_service import BedrockService

logger = logging.getLogger(__name__)

class MultiImageDamageAnalyzer:
    def __init__(self, s3_service: S3Service, rekognition_service: RekognitionService, bedrock_service: BedrockService):
        """
        Initialize MultiImageDamageAnalyzer with required services
        """
        self.s3_service = s3_service
        self.rekognition_service = rekognition_service
        self.bedrock_service = bedrock_service
        self.s3_client = boto3.client('s3')
    
    def process_single_image(
        self, 
        source_bucket: str, 
        source_key: str, 
        output_bucket: Optional[str] = None
    ) -> Dict:
        """
        Process a single image and generate damage report
        """
        try:
            logger.info(f"Processing image: {source_key}")
            
            # Get image from S3
            image_bytes = self.s3_service.read_image(source_bucket, source_key)
            if not image_bytes:
                raise ValueError(f"Failed to read image from {source_bucket}/{source_key}")
            
            # Detect damage using Rekognition
            s3_reference = {'Bucket': source_bucket, 'Name': source_key}
            damage_labels = self.rekognition_service.detect_damage(
                s3_reference,
                source_type='s3'
            )
            
            if not damage_labels:
                logger.warning(f"No damage labels detected for image {source_key}")
                damage_labels = []
            
            # Generate report using Bedrock
            report = self.bedrock_service.generate_report(
                image_bytes, 
                damage_labels
            )
            
            # Save report if output bucket specified
            if output_bucket and report:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                report_key = f"reports/{source_key.split('/')[-1]}_{timestamp}.txt"
                
                upload_success = self.s3_service.upload_text(
                    bucket=output_bucket,
                    key=report_key,
                    text_content=report
                )
                
                if not upload_success:
                    logger.warning(f"Failed to save report for {source_key}")

            # Move processed image to 'processed' folder within damage_images 
            # Assuming source_key is like "damage_images/image.jpg"
            filename = source_key.split('/')[-1]
            processed_key = f"damage_images/processed/{filename}"
            
            move_success = self.s3_service.move_file(
                bucket=source_bucket,
                source_key=source_key,
                destination_key=processed_key
            )

            if not move_success:
                logger.warning(f"Failed to move processed image {source_key} to processed folder")
      
            
            result = {
                'source_key': source_key,
                'processed_key': processed_key if move_success else None,
                'damage_labels': damage_labels,
                'report': report,
                'report_key': report_key,
                'timestamp': datetime.now().isoformat(),
                'processing_status': {
                    'report_saved': bool(report_key),
                    'image_moved': move_success
                }
            }
            
            logger.info(f"Successfully processed image {source_key}")
            return result
               
        except Exception as e:
            logger.error(f"Error processing image {source_key}: {str(e)}", exc_info=True)
            raise
        finally:
            logger.info(f"Finished processing image {source_key}")
   