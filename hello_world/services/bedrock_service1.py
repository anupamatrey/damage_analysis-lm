# services/bedrock_service.py
import boto3
import json
import logging
import time
import base64
from typing import Dict 
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

class BedrockService:
    def __init__(self, bedrock_client):
        self.bedrock_client = bedrock_client
        self.max_retries = 3
        self.base_delay = 2

    def validate_client(self):
        if not hasattr(self.bedrock_client, 'invoke_model'):
            raise ValueError("Invalid Bedrock client")

    def generate_report(self, image_bytes: bytes, damage_labels: list[Dict]) -> str:
        """Generate analysis report using Bedrock"""
        try:
            # Validate input
            if not image_bytes:
                raise ValueError("Image bytes cannot be empty")
            
            retry_count = 0
            last_exception = None    
            
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            
            # Create damage description from labels
            damage_description = ', '.join([label['Name'] for label in damage_labels])
            
            prompt = f"""Analyze the following image for damage. Detected potential damage indicators: {damage_description}
            
            Provide a detailed damage assessment including:
            1. Type and extent of damage
            2. Estimated repair complexity
            3. Potential repair cost range
            4. Recommendations for next steps
            
            Be specific and use the detected labels as context."""
            
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 300,
                "temperature": 0.7,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": base64_image
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            }
            while retry_count < self.max_retries:
                try:
                    response = self.client.invoke_model(
                        modelId=self.model_id,
                        body=json.dumps(body),
                        contentType="application/json"
                    )
                    
                    response_body = json.loads(response['body'].read())
                    if 'content' not in response_body or not response_body['content']:
                        raise ValueError("Invalid response from Bedrock")
                        
                    return response_body['content'][0]['text']
                except ClientError as e:
                    error_code = e.response['Error']['Code']
                    if error_code == 'ThrottlingException':
                        retry_count += 1
                        if retry_count < self.max_retries:
                            delay = self.base_delay * retry_count
                            logger.warning(
                                f"Rate limited by Bedrock. Retrying in {delay} seconds... "
                                f"(Attempt {retry_count}/{self.max_retries})"
                            )
                            time.sleep(delay)
                            continue
                        last_exception = e
                    else:
                        logger.error(f"Bedrock API error: {str(e)}")
                        raise
            
                except Exception as e:
                    logger.error(f"Bedrock error: {str(e)}")
                    raise
                
            logger.error(f"Failed to generate report after {self.max_retries} attempts: {str(last_exception)}")
            raise last_exception
        except Exception as e:  
            logger.error(f"Bedrock error: {e}") 
            raise

    def generate_report1(self, image_bytes: bytes, damage_labels: list) -> str:
        """
        Generate report for a single image using Bedrock
        """
        retry_count = 0
        last_exception = None

        # Prepare the prompt with damage labels
        damage_description = ', '.join([label['Name'] for label in damage_labels])
        prompt = f"""Human: Analyze the following image for damage.  Detected potential damage indicators: {json.dumps(damage_description)}  
            Provide a detailed damage assessment including:  
            1. Type and extent of damage  
            2. Estimated repair complexity  
            3. Potential repair cost range  
            4. Recommendations for next steps  Be specific and use the detected labels as context
            
            Be specific and use the detected labels as context. """


        while retry_count < self.max_retries:
            try:
                # Prepare request body
                body = {
                    "prompt": prompt,
                    "max_tokens_to_sample": 500,
                    "temperature": 0.7,
                }
                
                # Make single API call to Bedrock
                response = self.bedrock_client.invoke_model(
                    modelId="anthropic.claude-v2",
                    body=json.dumps(body)
                )
                
                # Process response
                response_body = json.loads(response['body'].read())
                logger.info("Successfully generated damage report")
                return response_body.get('completion', '')

            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == 'ThrottlingException':
                    retry_count += 1
                    if retry_count < self.max_retries:
                        delay = self.base_delay * retry_count
                        logger.warning(
                            f"Rate limited by Bedrock. Retrying in {delay} seconds... "
                            f"(Attempt {retry_count}/{self.max_retries})"
                        )
                        time.sleep(delay)
                        continue
                    last_exception = e
                else:
                    logger.error(f"Bedrock API error: {str(e)}")
                    raise
            except Exception as e:
                logger.error(f"Unexpected error in generating report: {str(e)}")
                raise

        logger.error(f"Failed to generate report after {self.max_retries} attempts: {str(last_exception)}")
        raise last_exception
