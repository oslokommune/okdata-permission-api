"""Utilities for handling JSON Web Tokens (JWTs)."""

from datetime import datetime, timedelta

import jwt

from dataplatform_keycloak.ssm import SsmClient


def generate_jwt():
    """Return a freshly generated JWT.

    The expiration time is currently hard-coded to 120 seconds. Both issue time
    (iat) and expiration time (exp) are given as POSIX timestamps.
    """
    now = datetime.now()
    expiration_time = now + timedelta(seconds=120)
    issuer = SsmClient.get_secret(
        "/dataplatform/teams-api/kong-keycloak-jwt-issuer",
    )
    key = SsmClient.get_secret(
        "/dataplatform/teams-api/kong-keycloak-jwt-secret",
    )
    claims = {
        "iat": int(now.timestamp()),
        "exp": int(expiration_time.timestamp()),
        "iss": issuer,
    }

    return jwt.encode(claims, key, algorithm="HS256")
