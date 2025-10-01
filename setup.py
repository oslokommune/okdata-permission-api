from setuptools import setup, find_packages

with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="okdata-permission-api",
    version="0.2.0",
    author="Origo Dataplattform",
    author_email="dataplattform@oslo.kommune.no",
    description="API for managing permissions to okdata resources",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.oslo.kommune.no/origo-dataplatform/okdata-permission-api",
    packages=find_packages(),
    install_requires=[
        "aws-xray-sdk>=2.10",
        "boto3",
        "cryptography",
        "fastapi>=0.109.2",
        "mangum>=0.10.0",
        "okdata-aws>=2.1,<3",
        "okdata-resource-auth>=0.1.4",
        "pydantic[email]~=1.10.0",
        "pyjwt>=2.5,<3",
        # Version 2.13.2 and up breaks our custom `TeamsKeycloakAdmin` class
        # and needs more work...
        "python-keycloak==2.13.1",
        "requests",
    ],
)
