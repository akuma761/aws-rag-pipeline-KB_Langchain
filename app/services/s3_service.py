import os
import shutil

import boto3

boto3_session = boto3.session.Session()
region_name = boto3_session.region_name

MMT_INVOICES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "mmt_invoices")


def create_s3_bucket(bucket_name: str, region: str = None) -> dict:
    if region is None:
        region = region_name
    s3_client = boto3.client("s3", region_name=region)
    try:
        if region == "us-east-1":
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            s3_client.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": region},
            )
        return {"bucket": bucket_name, "region": region}
    except s3_client.exceptions.BucketAlreadyExists:
        raise Exception(f"Bucket '{bucket_name}' already exists (globally taken)")
    except s3_client.exceptions.BucketAlreadyOwnedByYou:
        return {"bucket": bucket_name, "region": region}


def download_sample_documents(data_dir: str = "./data") -> list:
    os.makedirs(data_dir, exist_ok=True)
    copied = []
    for fname in os.listdir(MMT_INVOICES_DIR):
        src = os.path.join(MMT_INVOICES_DIR, fname)
        if os.path.isfile(src):
            dst = os.path.join(data_dir, fname)
            shutil.copy2(src, dst)
            copied.append(dst)
    return copied


def upload_directory_to_s3(local_path: str, bucket_name: str):
    s3_client = boto3.client("s3")
    uploaded = []
    for root, _dirs, files in os.walk(local_path):
        for file in files:
            local_file = os.path.join(root, file)
            s3_client.upload_file(local_file, bucket_name, file)
            uploaded.append(file)
    return uploaded
