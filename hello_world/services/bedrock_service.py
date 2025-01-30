from typing import Dict, List
import base64
import json
import time
import boto3
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class BedrockServiceError(Exception):
    """Custom exception for Bedrock service errors"""
    pass

class BedrockService:
    def __init__(self, client, max_retries: int = 3, base_delay: int = 2):
        """
        Initialize BedrockService
        
        Args:
            client: Boto3 Bedrock client
            max_retries: Maximum number of retry attempts
            base_delay: Base delay for exponential backoff
        """
        self.client = client
        self.model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
        self.max_retries = max_retries
        self.base_delay = base_delay

    def _prepare_prompt(self, damage_labels: List[Dict]) -> str:
        """
        Prepare the prompt for damage analysis
        
        Args:
            damage_labels: List of damage labels with confidence scores
        
        Returns:
            Formatted prompt string
        """
        try:
            # Format damage labels with confidence scores
            damage_details = [
                f"{label['Name']} (Confidence: {label.get('Confidence', 0):.1f}%)"
                for label in damage_labels
            ]
            damage_description = ', '.join(damage_details)

            return f"""Analyze the following image for damage. Detected potential damage indicators: {damage_description}

                Provide a detailed damage assessment including:
                1. Type and extent of damage
                2. Estimated repair complexity
                3. Potential repair cost range
                4. Recommendations for next steps

                Be specific and use the detected labels and their confidence levels as context."""
        except Exception as e:
            logger.error(f"Error preparing prompt: {str(e)}")
            raise BedrockServiceError(f"Failed to prepare prompt: {str(e)}")

    def _prepare_request_body(self, image_bytes: bytes, prompt: str) -> dict:
        """
        Prepare the request body for Bedrock API
        
        Args:
            image_bytes: Image data in bytes
            prompt: Formatted prompt string
        
        Returns:
            Request body dictionary
        """
        if not isinstance(image_bytes, bytes):
            raise ValueError("image_bytes must be bytes")
        if not prompt:
            raise ValueError("prompt cannot be empty")
        
        try:
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
        except Exception as e:
            raise ValueError(f"Failed to encode image: {str(e)}")
        
        return {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
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

    def _invoke_bedrock_model(self, body: dict) -> str:
        """
        Invoke Bedrock model with retry logic
        
        Args:
            body: Request body
        
        Returns:
            Model response text
        
        Raises:
            BedrockServiceError: If the model invocation fails
        """
        for attempt in range(self.max_retries):
            try:
                response = self.client.invoke_model(
                    modelId=self.model_id,
                    body=json.dumps(body)
                )
                response_body = json.loads(response.get('body').read())
                
                # Detailed logging
                logger.info(f"Response keys: {response_body.keys()}")
                logger.debug(f"Full response: {json.dumps(response_body, indent=2)}")
                
                # Handle different possible response structures
                if 'messages' in response_body:
                    return response_body['messages'][0]['content'][0]['text']
                elif 'content' in response_body:
                    return response_body['content'][0]['text']
                else:
                    logger.error(f"Unexpected response structure. Available keys: {response_body.keys()}")
                    raise BedrockServiceError("Unexpected response structure from Bedrock")
                    
            except ClientError as e:
                if attempt == self.max_retries - 1:  # Last attempt
                    logger.error(f"Final attempt failed: {str(e)}")
                    raise BedrockServiceError(f"Failed to invoke Bedrock model: {str(e)}")
                logger.warning(f"Attempt {attempt + 1} failed, retrying...")
                time.sleep(self.base_delay ** attempt)  # Exponential backoff
            except Exception as e:
                if attempt == self.max_retries - 1:
                    logger.error(f"Unexpected error in invoke_bedrock_model: {str(e)}")
                    raise BedrockServiceError(f"Unexpected error: {str(e)}")
                logger.warning(f"Unexpected error, retrying... {str(e)}")
                time.sleep(self.base_delay ** attempt)

    def generate_report(self, image_bytes: bytes, damage_labels: List[Dict]) -> str:
        """
        Generate analysis report using Bedrock
        
        Args:
            image_bytes: Image data in bytes
            damage_labels: List of damage labels with confidence scores
        
        Returns:
            Generated damage assessment report
        
        Raises:
            ValueError: If inputs are invalid
            BedrockServiceError: If the service fails
        """
        try:
            # Validate inputs
            if not image_bytes:
                raise ValueError("Image bytes cannot be empty")
            if not damage_labels:
                raise ValueError("Damage labels cannot be empty")
            
            # Prepare prompt and request body
            prompt = self._prepare_prompt(damage_labels)
            body = self._prepare_request_body(image_bytes, prompt)
            
            # Invoke model and get response
            return self._invoke_bedrock_model(body)
            
        except (ValueError, BedrockServiceError) as e:
            logger.error(f"Error generating report: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in generate_report: {str(e)}")
            raise BedrockServiceError(f"Unexpected error in generate_report: {str(e)}")

# Initialize the service
bedrock_client = boto3.client('bedrock-runtime')
bedrock_service = BedrockService(
    client=bedrock_client
)

