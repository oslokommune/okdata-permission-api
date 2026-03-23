from dataclasses import dataclass

import requests


@dataclass
class UMAWellKnown:
    token_endpoint: str
    jwks_uri: str
    resource_registration_endpoint: str
    policy_endpoint: str


class WellKnownConfigException(Exception):
    pass


def _validate(url: str, base_url: str) -> str:
    """Validate that `url` starts with `base_url`.

    Raise `WellKnownConfigException` if not.
    """
    if not url.startswith(base_url):
        raise WellKnownConfigException(
            f"Unexpected URL in `.well-known` response: '{url}'. Expected to "
            f"start with: '{base_url}'."
        )

    return url


def get_well_known(server_url: str, realm: str) -> UMAWellKnown:
    url = f"{server_url}/auth/realms/{realm}/.well-known/uma2-configuration"

    response = requests.get(url, timeout=15)
    response.raise_for_status()

    well_known = response.json()

    return UMAWellKnown(
        token_endpoint=_validate(well_known["token_endpoint"], server_url),
        jwks_uri=_validate(well_known["jwks_uri"], server_url),
        resource_registration_endpoint=_validate(
            well_known["resource_registration_endpoint"], server_url
        ),
        policy_endpoint=_validate(well_known["policy_endpoint"], server_url),
    )
