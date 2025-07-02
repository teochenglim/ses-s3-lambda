import boto3
import email
import json
import os
import requests
from utils import parse_email_from_bytes

collaboration_manager = os.environ['COLLABORATION_MANAGER']
emails_bucket = os.environ['EMAILS_BUCKET']
workflowmax_bucket = os.environ['WORKFLOWMAX_BUCKET']

s3 = boto3.resource('s3')

def lambda_handler(event, context):
    record = event["Records"][0]
    receipt = record["ses"]["receipt"]

    for verdict in ["spfVerdict", "dkimVerdict", "spamVerdict", "virusVerdict"]:
        if receipt.get(verdict, {}).get("status", "FAIL") == "FAIL":
            print(f"[SKIP] {verdict} failed. Email dropped.")
            return {"statusCode": 200, "body": f"{verdict} failed"}

    mail = record["ses"]["mail"]
    messageID = mail["messageId"]
    subject = mail["commonHeaders"].get("subject", "")
    to = mail["commonHeaders"].get("to", [])
    cc = mail["commonHeaders"].get("cc", [])
    destination = mail.get("destination", [])
    source = mail["source"]
    timestamp = mail["timestamp"]

    obj = s3.Object(emails_bucket, messageID)
    raw_email = obj.get()["Body"].read()

    parsed = parse_email_from_bytes(raw_email)
    content = parsed["content"]

    attachments = []
    embedded = []

    for part in parsed["attachments"]:
        key = f"{messageID}/attachments/{part['filename']}"
        s3.Bucket(workflowmax_bucket).put_object(Key=key, Body=part["body"], ContentType=part["content_type"])
        attachments.append(key)

    for part in parsed["embedded_attachments"]:
        key = f"{messageID}/embedded_images/{part['filename']}"
        s3.Bucket(workflowmax_bucket).put_object(Key=key, Body=part["body"], ContentType=part["content_type"])
        embedded.append(key)

    payload = {
        "timestamp": timestamp,
        "source": source,
        "messageID": messageID,
        "destination": list(set(destination + to + cc + parsed["destination"])),
        "To": to,
        "CC": cc,
        "Subject": subject,
        "Content": content,
        "Attachments": attachments,
        "EmbeddedAttachments": embedded,
        "Headers": parsed["headers"]
    }

    print(json.dumps(payload, indent=2))

    try:
        response = requests.post(collaboration_manager, json=payload)
        print(f"[INFO] Collaboration Manager responded: {response.status_code} {response.reason}")
        response.close()
        return {"statusCode": response.status_code, "body": response.reason}
    except Exception as e:
        print(f"[ERROR] POST failed: {e}")
        return {"statusCode": 500, "body": str(e)}
