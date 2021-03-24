from dataclasses import dataclass

import requests


@dataclass
class UMAWellKnown:
    issuer: str
    authorization_endpoint: str
    token_endpoint: str
    token_introspection_endpoint: str
    resource_registration_endpoint: str
    permission_endpoint: str
    policy_endpoint: str


def get_well_known(server_url, realm) -> UMAWellKnown:
    well_known_url = f"{server_url}/auth/realms/{realm}/.well-known/uma2-configuration"
    well_known_response = requests.get(well_known_url)
    well_known_response.raise_for_status()
    well_known = well_known_response.json()
    return UMAWellKnown(
        issuer=well_known["token_endpoint"],
        authorization_endpoint=well_known["authorization_endpoint"],
        token_endpoint=well_known["token_endpoint"],
        token_introspection_endpoint=well_known["token_introspection_endpoint"],
        resource_registration_endpoint=well_known["resource_registration_endpoint"],
        permission_endpoint=well_known["permission_endpoint"],
        policy_endpoint=well_known["policy_endpoint"],
    )
