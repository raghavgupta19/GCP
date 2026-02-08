import json
import os
from datetime import datetime
from google.cloud import storage

# Bucket name must be provided at runtime (NOT in code)
BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME")

if not BUCKET_NAME:
    raise RuntimeError("GCS_BUCKET_NAME environment variable not set")

def write_to_bucket(data: dict):
    """
    Writes form submission data to GCS as an append-only object.
    Uses VM-attached service account.
    """

    client = storage.Client()  # auto-auth via VM service account
    bucket = client.bucket(BUCKET_NAME)

    timestamp = datetime.utcnow().isoformat()
    object_name = f"submissions/{timestamp}.json"

    blob = bucket.blob(object_name)
    blob.upload_from_string(
        json.dumps(data, indent=2),
        content_type="application/json"
    )

    return object_name

