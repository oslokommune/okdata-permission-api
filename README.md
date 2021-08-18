Okdata Permission API
=====================

API for managing permissions to okdata resources such as datasets.

## API Documentation

API documentation can be found here: [OpenAPI Spec](https://api.data.oslo.systems/okdata-permission-api/openapi.json).

## Setup

In these examples, we use the default `python3` distribution on your platform.
If you need a specific version of Python you need to run the command for that
specific version. I.e. for 3.8 run `python3.8 -m venv .venv` instead to get a
virtualenv for that version.

### Installing global Python dependencies

You can choose to install the Python dependencies globally. This might require
you to run as root (use sudo).

```bash
python3 -m pip install tox black pip-tools
```

Or, you can install for just your user. This is recommended as it does not
require root/sudo, but it does require `~/.local/bin` to be added to `PATH` in
your `.bashrc` or similar file for your shell. Eg:
`PATH=${HOME}/.local/bin:${PATH}`.

```bash
python3 -m pip install --user tox black pip-tools
```


### Installing local Python dependencies in a virtualenv

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

```bash
make init
```


### Run application locally

This command will run a local instance of Keycloak, populate the local Keycloak
instance with necessary entities and run the FastAPI application on localhost.

```bash
make run
```


## Tests

Tests are run using [tox](https://pypi.org/project/tox/): `make test`

For tests and linting we use [pytest](https://pypi.org/project/pytest/),
[flake8](https://pypi.org/project/flake8/) and
[black](https://pypi.org/project/black/).


## Deploy

Deploy to dev is automatic via GitHub Actions, while deploy to prod can be triggered with GitHub Actions via dispatch. You can alternatively deploy from local machine (requires `saml2aws`) with: `make deploy` or `make deploy-prod`.
