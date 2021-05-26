import uuid
from dataclasses import dataclass
from datetime import timedelta

import dateutil.parser as date_parser
import pytest
from freezegun import freeze_time
from moto import mock_dynamodb2

import tests.setup.local_keycloak_config as kc_config
import tests.utils as test_utils
from dataplatform_keycloak import ResourceServer
from models import User, WebhookTokenOperation


@dataclass
class TestData:
    webhook_token = "774d8f35-fb4b-4e06-9d7f-54d1a08589b4"
    created_by = kc_config.janedoe
    dataset_id = "webhook-integration-test-dataset"
    created_at = date_parser.parse("2020-02-29T00:00:00+00:00")


test_data = TestData()


@mock_dynamodb2
class TestWebhooksApi:

    # POST /webhooks/{dataset_id}/tokens
    @freeze_time(test_data.created_at)
    def test_create_webhook_token(self, mock_client, fixed_uuid):

        access_token = test_utils.get_bearer_token_for_user(kc_config.janedoe)

        response = mock_client.post(
            f"/webhooks/{test_data.dataset_id}/tokens",
            json={"operation": "read"},
            headers=test_utils.auth_header(access_token),
        )

        assert response.status_code == 201
        assert response.json() == {
            "token": test_data.webhook_token,
            "created_by": test_data.created_by,
            "dataset_id": test_data.dataset_id,
            "operation": WebhookTokenOperation.READ.value,
            "created_at": test_data.created_at.isoformat(),
            "expires_at": (
                test_data.created_at + timedelta(days=(365 * 2))
            ).isoformat(),
            "is_active": True,
        }

    def test_create_webhook_token_forbidden(self, mock_client):

        access_token = test_utils.get_bearer_token_for_user(kc_config.homersimpson)

        response = mock_client.post(
            f"/webhooks/{test_data.dataset_id}/tokens",
            json={"operation": "read"},
            headers=test_utils.auth_header(access_token),
        )

        assert response.status_code == 403
        assert response.json() == {"message": "Forbidden"}

    def test_create_webhook_token_invalid_operation(self, mock_client):

        access_token = test_utils.get_bearer_token_for_user(kc_config.janedoe)
        response = mock_client.post(
            f"/webhooks/{test_data.dataset_id}/tokens",
            json={"operation": "cake"},
            headers=test_utils.auth_header(access_token),
        )

        assert response.status_code == 400
        assert response.json() == {
            "errors": [
                {
                    "loc": ["body", "operation"],
                    "msg": "value is not a valid enumeration member; permitted: "
                    "'read', 'write'",
                }
            ],
            "message": "Bad Request",
        }

    def test_create_webhook_json_field_missing(self, mock_client):

        access_token = test_utils.get_bearer_token_for_user(kc_config.janedoe)

        invalid_body_response = mock_client.post(
            f"/webhooks/{test_data.dataset_id}/tokens",
            json={"operationzz": "read"},
            headers=test_utils.auth_header(access_token),
        )

        assert invalid_body_response.status_code == 400
        assert invalid_body_response.json() == {
            "errors": [
                {
                    "loc": ["body", "operation"],
                    "msg": "field required",
                }
            ],
            "message": "Bad Request",
        }

    # GET /webhooks/{dataset_id}/tokens"

    def test_list_webhook_tokens(self, mock_client):

        access_token = test_utils.get_bearer_token_for_user(kc_config.janedoe)

        response = mock_client.get(
            f"/webhooks/{test_data.dataset_id}/tokens",
            headers=test_utils.auth_header(access_token),
        )

        assert response.status_code == 200
        assert response.json() == [
            {
                "token": test_data.webhook_token,
                "created_by": test_data.created_by,
                "dataset_id": test_data.dataset_id,
                "operation": WebhookTokenOperation.READ.value,
                "created_at": test_data.created_at.isoformat(),
                "expires_at": (
                    test_data.created_at + timedelta(days=(365 * 2))
                ).isoformat(),
                "is_active": True,
            }
        ]

    def test_list_webhook_tokens_forbidden(self, mock_client):

        access_token = test_utils.get_bearer_token_for_user(kc_config.homersimpson)

        response = mock_client.get(
            f"/webhooks/{test_data.dataset_id}/tokens",
            headers=test_utils.auth_header(access_token),
        )

        assert response.status_code == 403
        assert response.json() == {"message": "Forbidden"}

    # GET /webhooks/{dataset_id}/tokens/{webhook_token}/authorize

    @freeze_time(test_data.created_at)
    def test_authorize_webhook_token(self, mock_client):

        access_token = test_utils.get_token_for_service(
            kc_config.client_id,
            kc_config.client_secret,
        )

        response = mock_client.get(
            f"/webhooks/{test_data.dataset_id}/tokens/{test_data.webhook_token}/authorize?operation=read",
            headers=test_utils.auth_header(access_token),
        )

        assert response.status_code == 200
        assert response.json() == {"access": True, "reason": None}

    @freeze_time(test_data.created_at)
    def test_authorize_webhook_operation_unauthorized(self, mock_client):

        access_token = test_utils.get_token_for_service(
            kc_config.client_id,
            kc_config.client_secret,
        )

        response = mock_client.get(
            f"/webhooks/{test_data.dataset_id}/tokens/{test_data.webhook_token}/authorize?operation=write",
            headers=test_utils.auth_header(access_token),
        )

        assert response.status_code == 200
        assert response.json() == {
            "access": False,
            "reason": f"Provided token does not have access to perform write on {test_data.dataset_id}",
        }

    @freeze_time(test_data.created_at)
    def test_authorize_webhook_invalid_operation(self, mock_client):

        access_token = test_utils.get_token_for_service(
            kc_config.client_id,
            kc_config.client_secret,
        )

        response = mock_client.get(
            f"/webhooks/{test_data.dataset_id}/tokens/{test_data.webhook_token}/authorize?operation=cake",
            headers=test_utils.auth_header(access_token),
        )

        assert response.status_code == 400
        assert response.json() == {
            "errors": [
                {
                    "loc": ["query", "operation"],
                    "msg": "value is not a valid enumeration member; permitted: 'read', 'write'",
                }
            ],
            "message": "Bad Request",
        }

    @freeze_time(test_data.created_at + timedelta(days=(365 * 2), seconds=1))
    def test_authorize_webhook_expired_token(self, mock_client):
        access_token = test_utils.get_token_for_service(
            kc_config.client_id,
            kc_config.client_secret,
        )

        response = mock_client.get(
            f"/webhooks/{test_data.dataset_id}/tokens/{test_data.webhook_token}/authorize?operation=read",
            headers=test_utils.auth_header(access_token),
        )

        assert response.status_code == 200
        assert response.json() == {
            "access": False,
            "reason": "Provided token is expired",
        }

    # DELETE /webhooks/{dataset_id}/tokens/{webhook_token}/authorize
    def test_delete_webhook_token(self, mock_client):
        access_token = test_utils.get_bearer_token_for_user(kc_config.janedoe)

        response = mock_client.delete(
            f"/webhooks/{test_data.dataset_id}/tokens/{test_data.webhook_token}",
            headers=test_utils.auth_header(access_token),
        )

        assert response.status_code == 200
        assert response.json() == {
            "message": f"Deleted {test_data.webhook_token} for dataset {test_data.dataset_id}"
        }

        assert (
            mock_client.get(
                f"/webhooks/{test_data.dataset_id}/tokens",
                headers=test_utils.auth_header(access_token),
            ).json()
            == []
        )

    def test_delete_webhook_token_forbidden(self, mock_client):
        access_token = test_utils.get_bearer_token_for_user(kc_config.homersimpson)

        response = mock_client.delete(
            f"/webhooks/{test_data.dataset_id}/tokens/{test_data.webhook_token}",
            headers=test_utils.auth_header(access_token),
        )

        assert response.status_code == 403
        assert response.json() == {"message": "Forbidden"}

    def test_delete_webhook_token_not_found(self, mock_client):
        access_token = test_utils.get_bearer_token_for_user(kc_config.janedoe)

        response = mock_client.delete(
            f"/webhooks/{test_data.dataset_id}/tokens/{test_data.webhook_token}",
            headers=test_utils.auth_header(access_token),
        )

        assert response.status_code == 404
        assert response.json() == {
            "message": f"Provided token does not exist for dataset {test_data.dataset_id}"
        }


@pytest.fixture()
def fixed_uuid(monkeypatch):
    def generate_uuid():
        return uuid.UUID(test_data.webhook_token)

    monkeypatch.setattr(uuid, "uuid4", generate_uuid)


@pytest.fixture(autouse=True, scope="session")
def initialize_test_setup():
    create_webhook_tokens_table()

    resource_server = ResourceServer(client_secret_key=kc_config.resource_server_secret)
    resource_server.create_resource(
        f"okdata:dataset:{test_data.dataset_id}",
        User.parse_obj({"user_id": kc_config.janedoe, "user_type": "user"}),
    )


@mock_dynamodb2
def create_webhook_tokens_table(item_list=[]):
    import boto3

    client = boto3.client("dynamodb", region_name="eu-west-1")

    table_name = "webhook-tokens"

    client.create_table(
        TableName=table_name,
        KeySchema=[
            {"AttributeName": "token", "KeyType": "HASH"},
            {"AttributeName": "dataset_id", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "token", "AttributeType": "S"},
            {"AttributeName": "dataset_id", "AttributeType": "S"},
        ],
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
        GlobalSecondaryIndexes=[
            {
                "IndexName": "TokenByDatasetIndex",
                "KeySchema": [{"AttributeName": "dataset_id", "KeyType": "HASH"}],
                "Projection": {"ProjectionType": "ALL"},
                "ProvisionedThroughput": {
                    "ReadCapacityUnits": 1,
                    "WriteCapacityUnits": 1,
                },
            },
        ],
    )

    webhoook_tokens_table = boto3.resource("dynamodb", region_name="eu-west-1").Table(
        table_name
    )
    for item in item_list:
        webhoook_tokens_table.put_item(Item=item)

    return webhoook_tokens_table
