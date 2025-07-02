import os
import uuid
import re
from email import policy
from email.parser import BytesParser
from email.header import decode_header
from email.utils import getaddresses

def decode_filename(header_val):
    filename_bytes, encoding = decode_header(header_val)[0]
    if isinstance(filename_bytes, str):
        return filename_bytes.replace("\r\n", "")
    return filename_bytes.decode(encoding or "utf-8", errors="ignore").replace("\r\n", "")

def parse_email_from_bytes(raw_email_bytes):
    message = BytesParser(policy=policy.default).parsebytes(raw_email_bytes)

    to_addrs = getaddresses(message.get_all("To", []))
    cc_addrs = getaddresses(message.get_all("Cc", []))
    bcc_addrs = getaddresses(message.get_all("Bcc", []))

    # fallback to infer BCC
    inferred_bcc = []
    for header in message.get_all("Received", []):
        match = re.search(r'for\s+<?([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})>?', header)
        if match:
            inferred_bcc.append(match.group(1))

    result = {
        "headers": dict(message.items()),
        "content": "",
        "attachments": [],
        "embedded_attachments": [],
        "destination": list(set(
            [addr for name, addr in to_addrs + cc_addrs + bcc_addrs + [(None, b) for b in inferred_bcc]]
        )),
        "rfc822_detected": False
    }

    if message.is_multipart():
        for part in message.walk():
            ctype = part.get_content_type()
            disposition = str(part.get("Content-Disposition", "")).lower()
            payload = part.get_payload(decode=True)
            if payload is None:
                continue

            if ctype in ["text/plain", "text/html"] and "attachment" not in disposition and not result["rfc822_detected"]:
                charset = part.get_content_charset()
                result["content"] = payload.decode(charset or "utf-8", errors="ignore")
                continue

            filename = part.get_filename()
            if filename:
                filename = decode_filename(filename)
            else:
                filename = f"part_{uuid.uuid4()}.{ctype.split('/')[-1]}"

            record = {
                "filename": filename,
                "content_type": ctype,
                "body": payload
            }

            if ctype == "message/rfc822":
                result["rfc822_detected"] = True
                result["attachments"].append(record)
            elif "inline" in disposition or ctype.startswith("image/"):
                result["embedded_attachments"].append(record)
            else:
                result["attachments"].append(record)
    else:
        charset = message.get_content_charset()
        result["content"] = message.get_payload(decode=True).decode(charset or "utf-8", errors="ignore")

    return result
