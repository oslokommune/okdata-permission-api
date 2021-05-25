import logging
import os

from dataplatform_keycloak import ResourceServer
from dataplatform_keycloak.ssm import SsmClient
from tests.setup import local_keycloak_config


def resource_server_from_env(env: str) -> ResourceServer:
    if env == "local":
        # Run `make setup-keycloak-local` and `make populate-local-keycloak`
        # in order to use local environment
        resource_server = ResourceServer(
            resource_server_client_id=local_keycloak_config.resource_server_id,
            keycloak_realm=local_keycloak_config.realm_name,
            keycloak_server_url=local_keycloak_config.server_url,
            client_secret_key=local_keycloak_config.resource_server_secret,
        )
    else:
        os.environ["AWS_PROFILE"] = f"okdata-{env}"
        os.environ["AWS_REGION"] = "eu-west-1"

        resource_server = ResourceServer(
            resource_server_client_id="okdata-resource-server",
            keycloak_realm="api-catalog",
            keycloak_server_url=SsmClient.get_secret(
                "/dataplatform/shared/keycloak-server-url"
            ),
        )

    logger = logging.getLogger()
    logger.info(f"Environment: {env}")
    logger.info(f"Keycloak server URL: {resource_server.keycloak_server_url}")
    logger.info(f"Keycloak realm: {resource_server.keycloak_realm}")

    return resource_server
