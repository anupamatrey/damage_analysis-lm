from typing import List,Dict,Union 
import logging 
from datetime import datetime 
from botocore.exceptions import ClientError, BotoCoreError
logger = logging.getLogger(__name__) 

class RekognitionService: 
    def __init__(self, rekognition_client):  
        self.client = rekognition_client  
        self.damage_keywords = [
                                    # Physical damage
                                    'damage', 'crack', 'scratch', 'dent', 'broken', 'chip', 'split', 'tear', 
                                    'puncture', 'gouge', 'rupture', 'fissure', 'fracture', 'destroyed',
                                    
                                    # Surface-specific damage
                                    'rust', 'corrosion', 'wear', 'deterioration', 'degradation', 'erosion', 
                                    'stain', 'discoloration', 'peeling', 'chipped paint', 'surface damage',
                                    
                                    # Structural damage
                                    'deformation', 'warped', 'bent', 'misaligned', 'collapsed', 'buckled', 
                                    'twisted', 'structural failure', 'compromised',
                                    
                                    # Material-specific damage
                                    'shattered', 'cracked glass', 'metal fatigue', 'material failure', 
                                    'structural weakness', 'fragmented',
                                    
                                    # Contextual damage indicators
                                    'impact', 'collision', 'accident', 'trauma', 'stress', 'strain', 
                                    'mechanical failure', 'structural compromise'
        ]

    def detect_damage(self, image: Union[Dict, bytes], source_type: str = 's3') -> List[Dict]:
        """
        Detect damage in image using Rekognition
        source_type: 's3' or 'bytes'
        """
        try:
            # Prepare image input based on source type
            image_input = {}
            if source_type == 's3':
                image_input = {
                    'S3Object': {
                        'Bucket': image['Bucket'],
                        'Name': image['Name']
                    }
                }
            elif source_type == 'bytes':
                image_input = {'Bytes': image}
            else:
                raise ValueError(f"Invalid source_type: {source_type}")

            # Call Rekognition
            response = self.client.detect_labels(
                Image=image_input,
                MaxLabels=20,
                MinConfidence=70
            )

            # Filter for damage-related labels
            damage_labels = [
                label for label in response['Labels']
                if any(damage_term in label['Name'].lower() 
                      for damage_term in ['damage', 'dent', 'scratch', 'broken', 'crack'])
            ]

            logger.info(f"Detected {len(damage_labels)} damage-related labels")
            return damage_labels

        except ClientError as e:
            logger.error(f"Rekognition API error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in damage detection: {str(e)}")
            raise
        finally:
            logger.info("Damage detection completed")
            
    def detect_damage1(self, image: Union[Dict, bytes], source_type: str = 's3') -> List[Dict]: 
        """
        Detect damage using Rekognition
        :param image: Image source (S3 object reference or image bytes)
        :param source_type: 's3' or 'bytes'
        :return: List of damage-related labels
        :raises: ValueError, ImageTooLargeException, InvalidImageFormatException

        """
        try: 
            # Validate inputs
            if not image:
                raise ValueError("Image parameter cannot be empty")
            # Prepare image reference based on source type
            if source_type == 's3':  
                if not isinstance(image, dict) or 'Bucket' not in image or 'Name' not in image:
                    raise ValueError("S3 image reference must contain 'Bucket' and 'Name' keys")
                image_reference = {'S3Object': image}

            elif source_type == 'bytes': 
                if not isinstance(image, bytes):
                    raise ValueError("Image must be bytes when source_type is 'bytes'")
                image_reference = {'Bytes': image} 
            else: 
                raise ValueError("Invalid source type. Use 's3' or 'bytes'.")  
            
            try:
                response = self.client.detect_labels(  
                    Image=image_reference,  
                    MaxLabels=10,  
                    MinConfidence=70.0 
                ) 
            except ClientError as e:
                error_code = ce.response['Error']['Code']
                if error_code == 'InvalidImageFormatException':
                    logger.error("Invalid image format provided")
                    raise ValueError("Invalid image format. Please provide a valid image file.")
                elif error_code == 'ImageTooLargeException':
                    logger.error("Image size exceeds maximum allowed size")
                    raise ValueError("Image size is too large. Maximum size is 5MB for direct uploads.")
                elif error_code == 'InvalidS3ObjectException':
                    logger.error("Invalid S3 object reference")
                    raise ValueError("Unable to access the S3 object. Please check permissions and if the object exists.")
                elif error_code == 'InvalidParameterException':
                    logger.error(f"Invalid parameter: {ce}")
                    raise ValueError("Invalid parameters provided to Rekognition service.")
                else:
                    logger.error(f"AWS Rekognition ClientError: {ce}")
                    raise
             
            except BotoCoreError as be:
                logger.error(f"AWS BotoCore error: {be}")
                raise ValueError("AWS service error occurred. Please try again later.")
     
            if not response or 'Labels' not in response:
                logger.warning("No labels found in the Rekognition response")
                return []

            # Process and filter damage-related labels
            try:
                damage_labels = [
                    label for label in response['Labels']
                    if any(keyword in label['Name'].lower() for keyword in self.damage_keywords)
                ]
                
                logger.info(f"Found {len(damage_labels)} damage-related labels")
                return damage_labels
                
            except Exception as e:
                logger.error(f"Error processing labels: {e}")
                raise ValueError("Error processing Rekognition response")
        except Exception as e:
                logger.error(f"Unexpected error in detect_damage: {e}")
                raise