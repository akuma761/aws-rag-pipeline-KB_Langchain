import os
import json
import shutil
import time
import random

import boto3

from utility import (
    create_bedrock_execution_role,
    create_oss_policy_attach_bedrock_execution_role,
    create_policies_in_oss,
    interactive_sleep,
)

suffix = random.randrange(200, 900)
boto3_session = boto3.session.Session()
region_name = boto3_session.region_name


import shutil

MMT_INVOICES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "mmt_invoices")


def download_sample_documents(data_dir: str = "./data") -> list:
    os.makedirs(data_dir, exist_ok=True)
    source_dir = MMT_INVOICES_DIR
    copied = []
    for fname in os.listdir(source_dir):
        src = os.path.join(source_dir, fname)
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


def create_opensearch_collection(vector_store_name: str = None):
    if vector_store_name is None:
        vector_store_name = f"bedrock-sample-knowledge-base-{suffix}"
    aoss_client = boto3.client("opensearchserverless")

    security_policy = aoss_client.create_security_policy(
        name=f"bedrock-sample-rag-sp-{suffix}",
        policy=json.dumps(
            {
                "Rules": [
                    {"Resource": ["collection/" + vector_store_name], "ResourceType": "collection"}
                ],
                "AWSOwnedKey": True,
            }
        ),
        type="encryption",
    )

    network_policy = aoss_client.create_security_policy(
        name=f"bedrock-sample-rag-np-{suffix}",
        policy=json.dumps(
            [
                {
                    "Rules": [
                        {"Resource": ["collection/" + vector_store_name], "ResourceType": "collection"}
                    ],
                    "AllowFromPublic": True,
                }
            ]
        ),
        type="network",
    )

    collection = aoss_client.create_collection(
        name=vector_store_name, type="VECTORSEARCH"
    )
    collection_id = collection["createCollectionDetail"]["id"]
    collection_arn = collection["createCollectionDetail"]["arn"]

    interactive_sleep(30)

    access_policy = aoss_client.create_access_policy(
        name=f"bedrock-sample-rag-ap-{suffix}",
        policy=json.dumps(
            [
                {
                    "Rules": [
                        {
                            "Resource": ["collection/" + vector_store_name],
                            "Permission": [
                                "aoss:CreateCollectionItems",
                                "aoss:DeleteCollectionItems",
                                "aoss:UpdateCollectionItems",
                                "aoss:DescribeCollectionItems",
                            ],
                            "ResourceType": "collection",
                        },
                        {
                            "Resource": ["index/" + vector_store_name + "/*"],
                            "Permission": [
                                "aoss:CreateIndex",
                                "aoss:DeleteIndex",
                                "aoss:UpdateIndex",
                                "aoss:DescribeIndex",
                                "aoss:ReadDocument",
                                "aoss:WriteDocument",
                            ],
                            "ResourceType": "index",
                        },
                    ],
                    "Principal": [
                        boto3.client("sts").get_caller_identity()["Arn"],
                        "arn:aws:iam::123456789012:role/temp",
                    ],
                    "Description": "data access policy",
                }
            ]
        ),
        type="data",
    )

    return {
        "collection_name": vector_store_name,
        "collection_id": collection_id,
        "collection_arn": collection_arn,
    }


def create_knowledge_base(
    bucket_name: str,
    collection_arn: str,
    collection_id: str,
    vector_store_name: str = None,
    kb_name: str = None,
    kb_description: str = None,
):
    if vector_store_name is None:
        vector_store_name = f"bedrock-sample-knowledge-base-{suffix}"
    if kb_name is None:
        kb_name = f"Bedrock-Knowledge-Base-{suffix}"
    if kb_description is None:
        kb_description = "Knowledge base created via Flask app"

    bedrock_agent_client = boto3.client("bedrock-agent")

    bedrock_kb_execution_role = create_bedrock_execution_role(bucket_name)
    bedrock_kb_execution_role_arn = bedrock_kb_execution_role["Role"]["Arn"]

    create_oss_policy_attach_bedrock_execution_role(
        collection_id, bedrock_kb_execution_role
    )

    create_policies_in_oss(
        vector_store_name,
        boto3.client("opensearchserverless"),
        bedrock_kb_execution_role_arn,
    )

    knowledge_base = bedrock_agent_client.create_knowledge_base(
        name=kb_name,
        description=kb_description,
        roleArn=bedrock_kb_execution_role_arn,
        knowledgeBaseConfiguration={
            "type": "VECTOR",
            "vectorKnowledgeBaseConfiguration": {
                "embeddingModelArn": f"arn:aws:bedrock:{region_name}::foundation-model/amazon.titan-embed-text-v2:0"
            },
        },
        storageConfiguration={
            "type": "OPENSEARCH_SERVERLESS",
            "opensearchServerlessConfiguration": {
                "collectionArn": collection_arn,
                "vectorIndexName": vector_store_name,
                "fieldMapping": {
                    "metadataField": "metadata",
                    "textField": "text",
                },
            },
        },
    )
    kb_id = knowledge_base["knowledgeBase"]["knowledgeBaseId"]
    return kb_id


def create_data_source(kb_id: str, bucket_name: str, ds_name: str = None):
    if ds_name is None:
        ds_name = f"bedrock-knowledge-base-datasource-{suffix}"
    bedrock_agent_client = boto3.client("bedrock-agent")
    data_source = bedrock_agent_client.create_data_source(
        name=ds_name,
        description="Data source for hospital PDFs",
        knowledgeBaseId=kb_id,
        dataSourceConfiguration={
            "type": "S3",
            "s3Configuration": {
                "bucketArn": f"arn:aws:s3:::{bucket_name}",
                "inclusionPrefixes": [""],
            },
        },
        vectorIngestionConfiguration={
            "chunkingConfiguration": {
                "chunkingStrategy": "FIXED_SIZE",
                "fixedSizeChunkingConfiguration": {
                    "maxTokens": 300,
                    "overlapPercentage": 20,
                },
            }
        },
    )
    ds_id = data_source["dataSource"]["dataSourceId"]
    return ds_id


def start_ingestion_job(kb_id: str, ds_id: str):
    bedrock_agent_client = boto3.client("bedrock-agent")
    job = bedrock_agent_client.start_ingestion_job(
        knowledgeBaseId=kb_id, dataSourceId=ds_id
    )
    job_id = job["ingestionJob"]["ingestionJobId"]
    return job_id


def get_ingestion_job_status(kb_id: str, ds_id: str, job_id: str):
    bedrock_agent_client = boto3.client("bedrock-agent")
    result = bedrock_agent_client.get_ingestion_job(
        knowledgeBaseId=kb_id, dataSourceId=ds_id, ingestionJobId=job_id
    )
    return result["ingestionJob"]["status"]


def list_knowledge_bases():
    bedrock_agent_client = boto3.client("bedrock-agent")
    response = bedrock_agent_client.list_knowledge_bases()
    return response.get("knowledgeBaseSummaries", [])
