import json
import decimal
from typing import List

import boto3

from boto3.dynamodb.conditions import Key, Attr

from models import WebhookTokenItem


class WebhookTokensTable:
    def __init__(self):
        dynamodb = boto3.resource("dynamodb", region_name="eu-west-1")
        self.webhook_tokens_table = dynamodb.Table("webhook-tokens")

    def get_webhook_token_item(self, token: str, dataset_id: str) -> WebhookTokenItem:
        response = self.webhook_tokens_table.query(
            KeyConditionExpression=Key("token").eq(token)
            & Key("dataset_id").eq(dataset_id),
            FilterExpression=Attr("is_active").eq(True),
            Limit=1,
        )

        if response["Count"] == 1:
            return WebhookTokenItem.parse_obj(response["Items"][0])

        return None

    def list_webhook_token_items(self, dataset_id) -> List[WebhookTokenItem]:
        response = self.webhook_tokens_table.query(
            IndexName="TokenByDatasetIndex",
            KeyConditionExpression=Key("dataset_id").eq(dataset_id),
            FilterExpression=Attr("is_active").eq(True),
        )
        return [WebhookTokenItem.parse_obj(item) for item in response["Items"]]

    def put_webhook_token_item(self, token_item: WebhookTokenItem):
        item = json.loads(token_item.json(), parse_float=decimal.Decimal)
        self.webhook_tokens_table.put_item(Item=item)

    def delete_webhook_token_item(self, token: str, dataset_id: str):
        # Soft deleting webhook token item by setting is_active to false
        self.webhook_tokens_table.update_item(
            Key={"token": token, "dataset_id": dataset_id},
            UpdateExpression="SET is_active = :val",
            ExpressionAttributeValues={":val": False},
        )
