import json
import random

import boto3

from utility import interactive_sleep

suffix = random.randrange(200, 900)
boto3_session = boto3.session.Session()
region_name = boto3_session.region_name


def create_opensearch_collection(vector_store_name: str = None):
    if vector_store_name is None:
        vector_store_name = f"bedrock-sample-knowledge-base-{suffix}"
    aoss_client = boto3.client("opensearchserverless")

    aoss_client.create_security_policy(
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

    aoss_client.create_security_policy(
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

    aoss_client.create_access_policy(
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
