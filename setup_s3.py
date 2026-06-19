import os
import random

import boto3

INVOICES_DIR = os.path.join(os.path.dirname(__file__), "mmt_invoices")


def main():
    s3 = boto3.client("s3")

    account_id = boto3.client("sts").get_caller_identity()["Account"]
    bucket_name = f"mmt-invoices-{account_id}"

    try:
        s3.create_bucket(Bucket=bucket_name)
        print(f"Created bucket s3://{bucket_name}/")
    except s3.exceptions.BucketAlreadyOwnedByYou:
        print(f"Bucket s3://{bucket_name}/ already exists.")

    files = [f for f in os.listdir(INVOICES_DIR) if os.path.isfile(os.path.join(INVOICES_DIR, f))]
    for i, fname in enumerate(files, 1):
        s3.upload_file(os.path.join(INVOICES_DIR, fname), bucket_name, fname)
        print(f"[{i}/{len(files)}] Uploaded {fname}")

    print(f"\nDone. {len(files)} files in s3://{bucket_name}/")
    print(f"Use this bucket: {bucket_name}")


if __name__ == "__main__":
    main()
