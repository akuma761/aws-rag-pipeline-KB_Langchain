import random

import boto3

from utility import (
    create_bedrock_execution_role,
    create_oss_policy_attach_bedrock_execution_role,
    create_policies_in_oss,
)

suffix = random.randrange(200, 900)
boto3_session = boto3.session.Session()
region_name = boto3_session.region_name


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
