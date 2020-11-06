from dataclasses import dataclass
import requests


@dataclass
class UMAWellKnown:
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    token_introspection_endpoint: str
    end_session_endpoint: str
    jwks_uri: str
    grant_types_supported: list
    response_types_supported: list
    response_modes_supported: list
    registration_endpoint: str
    token_endpoint_auth_methods_supported: list
    token_endpoint_auth_signing_alg_values_supported: list
    scopes_supported: list
    resource_registration_endpoint: str
    permission_endpoint: str
    policy_endpoint: str
    introspection_endpoint: str


def get_well_known(server_url, realm) -> UMAWellKnown:
    resp = requests.get(
        f"{server_url}/auth/realms/{realm}/.well-known/uma2-configuration"
    )
    return UMAWellKnown(**resp.json())
