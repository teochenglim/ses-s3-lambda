import sys
import os
import json
from datetime import datetime, timezone
from utils import parse_email_from_bytes

def save_locally(message_id, parsed, output_dir="output"):
    folder = os.path.join(output_dir, message_id)
    os.makedirs(folder, exist_ok=True)

    # Save email body
    with open(os.path.join(folder, "email-body.txt"), "w", encoding="utf-8") as f:
        f.write(parsed["content"])

    # Write files to correct folders
    attachments = []
    for part in parsed["attachments"]:
        path = os.path.join(folder, "attachments", part["filename"])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(part["body"])
        attachments.append(f"attachments/{part['filename']}")

    embedded = []
    for part in parsed["embedded_attachments"]:
        path = os.path.join(folder, "embedded_images", part["filename"])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(part["body"])
        embedded.append(f"embedded_images/{part['filename']}")

    # Match Lambda payload shape
    metadata = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source": parsed["headers"].get("From", ""),
        "messageID": message_id,
        "destination": list(set(parsed["destination"])),
        "To": [parsed["headers"].get("To", "")],
        "CC": [parsed["headers"].get("Cc", "")] if parsed["headers"].get("Cc") else [],
        "Subject": parsed["headers"].get("Subject", ""),
        "Content": parsed["content"],
        "Attachments": attachments,
        "EmbeddedAttachments": embedded,
        "Headers": parsed["headers"]
    }

    # Save metadata.json
    with open(os.path.join(folder, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"[DONE] Saved to {folder}")

def main(eml_file):
    if not os.path.isfile(eml_file):
        print(f"[ERROR] File not found: {eml_file}")
        return

    with open(eml_file, "rb") as f:
        raw_email = f.read()

    message_id = os.path.splitext(os.path.basename(eml_file))[0]
    parsed = parse_email_from_bytes(raw_email)
    save_locally(message_id, parsed)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python test_utils.py path/to/email.eml")
    else:
        main(sys.argv[1])
