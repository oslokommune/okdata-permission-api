import os
import tests.setup.local_keycloak_config as local_keycloak_config
import boto3
from moto import mock_ssm


def mock_ssm():
    mock_ssm().start()
    ssm_client = boto3.client("ssm", region_name=os.environ["AWS_REGION"])
    ssm_client.put_parameter(
        Name="dataplatform/poc-policy-server/client_secret",
        Description="A test parameter",
        Value=local_keycloak_config.resource_server_secret,
        Type="SecureString",
    )
