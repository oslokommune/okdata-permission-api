Okdata Permission API
==================
API for managing permissions to okdata resources such as datasets. The API is currently WIP (work in progress) and is
not in use anywhere at this time.

## Api Documentation

Api documentation can be found here: [Openapi Spec](https://api.data.oslo.systems/okdata-permission-api/openapi.json)

## Setup

In these examples, we use the default `python3` distribution on your platform.
If you need a specific version of python you need to run the command for that
specific version. Ie. for 3.8 run `python3.8 -m venv .venv` instead to get a
virtualenv for that version.

### Installing global python dependencies

You can either install globally. This might require you to run as root (use sudo).

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


### Installing local python dependencies in a virtualenv

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

```bash
make init
```


### Run application locally

This command will run a local instance of keycloak, populate the local keycloak instance with necessary entities and run 
the fastapi application on localhost.

```bash
make run
```


## Tests

Tests are run using [tox](https://pypi.org/project/tox/): `make test`

For tests and linting we use [pytest](https://pypi.org/project/pytest/),
[flake8](https://pypi.org/project/flake8/) and
[black](https://pypi.org/project/black/).


## Deploy

`make deploy` or `make deploy-prod`

Requires `saml2aws`
