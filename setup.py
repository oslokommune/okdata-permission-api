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
        "aws-xray-sdk",
        "boto3",
        "fastapi>=0.109.2",
        "mangum>=0.10.0",
        "okdata-aws>=1.0.1,<2.0.0",
        "okdata-resource-auth>=0.1.4",
        "pydantic[email]~=1.10.0",
        "pyjwt",
        "python-keycloak>=1.7.0",
        "pytz",
        "requests",
    ],
)
