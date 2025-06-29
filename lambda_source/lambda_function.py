import json
import email
import logging
import urllib.parse
import re
from email import policy
from email.parser import BytesParser
import boto3
import uuid

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3 = boto3.client('s3')

def clean_content_id(content_id):
    """Clean and normalize Content-ID values"""
    if not content_id:
        return ""
    content_id = content_id.strip()
    # Remove surrounding angle brackets or quotes
    if len(content_id) > 1:
        if content_id.startswith('<') and content_id.endswith('>'):
            return content_id[1:-1]
        if content_id.startswith('"') and content_id.endswith('"'):
            return content_id[1:-1]
        if content_id.startswith("'") and content_id.endswith("'"):
            return content_id[1:-1]
    return content_id

def decode_payload(part):
    """Decode email part payload with proper charset handling"""
    try:
        payload = part.get_payload(decode=True)
        if payload is None:
            return ""
        charset = part.get_content_charset('utf-8')
        return payload.decode(charset or 'utf-8', errors='replace')
    except Exception as e:
        logger.error(f"Payload decoding error: {str(e)}")
        return ""

def save_part(part, base_path, part_type, metadata, bucket_name):
    """Save email part to S3 and update metadata"""
    try:
        content_type = part.get_content_type()
        filename = part.get_filename()
        
        if not filename:
            # Generate filename based on content type
            ext_map = {
                'text/plain': 'txt',
                'text/html': 'html',
                'image/jpeg': 'jpg',
                'image/png': 'png',
                'image/gif': 'gif',
                'image/webp': 'webp'
            }
            ext = ext_map.get(content_type, 'bin')
            filename = f"{part_type}_{uuid.uuid4().hex[:8]}.{ext}"
        
        key = f"{base_path}/{part_type}/{filename}"
        content = part.get_payload(decode=True)
        if not content:
            raise ValueError("Empty content payload")
        
        s3.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=content,
            ContentType=content_type
        )
        
        part_metadata = {
            "filename": filename,
            "content_type": content_type,
            "size": len(content),
            "s3_key": key,
            "content_id": clean_content_id(part.get('Content-ID', ''))
        }
        
        metadata[f"{part_type}s"].append(part_metadata)
        logger.info(f"Saved {part_type}: {filename} (Content-ID: {part_metadata['content_id']})")
        return part_metadata
        
    except Exception as e:
        error_msg = f"Error saving {part_type} '{filename}': {type(e).__name__} - {str(e)}"
        logger.error(error_msg)
        metadata.setdefault('errors', []).append(error_msg)
        return None

def process_email(bucket_name, key):
    """Process individual email file from S3"""
    metadata = {'errors': []}
    try:
        # Extract message_id from key (raw/<message_id>)
        message_id = key.split('/')[-1]
        logger.info(f"Processing message: {message_id}")

        # Retrieve email from S3
        response = s3.get_object(Bucket=bucket_name, Key=key)
        email_content = response['Body'].read()
        
        # Parse email
        msg = BytesParser(policy=policy.default).parsebytes(email_content)
        
        # Create base path for parsed content
        base_path = f"parsed/{message_id}"
        metadata.update({
            "message_id": message_id,
            "headers": dict(msg.items()),
            "attachments": [],
            "embedded_images": [],
            "content_ids": {}
        })
        
        # Extract text and HTML bodies
        text_body = ""
        html_body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type().lower()
                content_disposition = str(part.get("Content-Disposition", "")).lower()
                
                # Skip multipart containers
                if part.is_multipart():
                    continue
                
                # Handle attachments
                if "attachment" in content_disposition:
                    save_part(part, base_path, "attachments", metadata, bucket_name)
                    continue
                
                # Handle embedded images
                is_embedded_image = (
                    "inline" in content_disposition or 
                    part.get('Content-ID') or
                    (content_type.startswith("image/") and "attachment" not in content_disposition)
                )
                
                if is_embedded_image:
                    saved_part = save_part(part, base_path, "embedded_images", metadata, bucket_name)
                    if saved_part and saved_part['content_id']:
                        metadata['content_ids'][saved_part['content_id']] = saved_part
                    continue
                
                # Get text content
                if content_type == "text/plain":
                    text_body = decode_payload(part) or text_body
                elif content_type == "text/html":
                    html_body = decode_payload(part) or html_body
        else:
            # Handle non-multipart messages
            content_type = msg.get_content_type().lower()
            if content_type == "text/plain":
                text_body = decode_payload(msg)
            elif content_type == "text/html":
                html_body = decode_payload(msg)
        
        # Process HTML content to update embedded image references
        if html_body:
            # Track replacements for debugging
            replacements = []
            for content_id, img_meta in metadata['content_ids'].items():
                if not content_id:
                    continue
                    
                s3_path = f"https://{bucket_name}.s3.amazonaws.com/{img_meta['s3_key']}"
                
                # Create regex patterns for different CID formats
                patterns = [
                    re.compile(f'cid:\\s*{re.escape(content_id)}', re.IGNORECASE),
                    re.compile(f'cid:\\s*<{re.escape(content_id)}>', re.IGNORECASE),
                    re.compile(f'"?{re.escape(content_id)}"?', re.IGNORECASE)
                ]
                
                for pattern in patterns:
                    (html_body, count) = pattern.subn(s3_path, html_body)
                    if count > 0:
                        replacements.append({
                            "content_id": content_id,
                            "s3_path": s3_path,
                            "replacements": count
                        })
            
            metadata['html_replacements'] = replacements
            
            # Save processed HTML
            html_key = f"{base_path}/content.html"
            s3.put_object(
                Bucket=bucket_name,
                Key=html_key,
                Body=html_body,
                ContentType="text/html"
            )
            metadata["html_body_key"] = html_key
        
        # Save text body
        if text_body:
            text_key = f"{base_path}/content.txt"
            s3.put_object(
                Bucket=bucket_name,
                Key=text_key,
                Body=text_body,
                ContentType="text/plain"
            )
            metadata["text_body_key"] = text_key
        
    except Exception as e:
        error_msg = f"Critical processing error: {type(e).__name__} - {str(e)}"
        logger.error(error_msg, exc_info=True)
        metadata['errors'].append(error_msg)
    
    # Save metadata (even if partially processed)
    try:
        s3.put_object(
            Bucket=bucket_name,
            Key=f"{base_path}/metadata.json",
            Body=json.dumps(metadata, indent=2),
            ContentType="application/json"
        )
        return len(metadata.get('errors', [])) == 0
    except Exception as e:
        logger.error(f"Failed to save metadata: {str(e)}")
        return False

def lambda_handler(event, context):
    success_count = 0
    failure_count = 0
    
    for record in event['Records']:
        try:
            # Get bucket and key from S3 event
            bucket_name = record['s3']['bucket']['name']
            key = urllib.parse.unquote_plus(record['s3']['object']['key'])
            
            # Only process objects in raw/ prefix
            if not key.startswith('raw/'):
                logger.info(f"Skipping non-raw object: {key}")
                continue
                
            # Process the email
            if process_email(bucket_name, key):
                success_count += 1
            else:
                failure_count += 1
                
        except Exception as e:
            failure_count += 1
            logger.error(f"Record processing failed: {type(e).__name__} - {str(e)}", exc_info=True)
    
    return {
        'statusCode': 200,
        'body': json.dumps({
            'processed': success_count + failure_count,
            'success': success_count,
            'failures': failure_count
        })
    }