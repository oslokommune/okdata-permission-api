import jwt
from freezegun import freeze_time

from dataplatform_keycloak.jwt import generate_jwt


@freeze_time("1970-01-01")
def test_generate_jwt():
    token = generate_jwt()
    claims = jwt.decode(token, "jwt-secret", algorithms=["HS256"])

    assert claims["iat"] == 0
    assert claims["exp"] == 120
    assert claims["iss"] == "jwt-issuer"
