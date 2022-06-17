Okdata Permission API
=====================

API for managing permissions to okdata resources such as datasets via [Keycloak Authorization Services](https://www.keycloak.org/docs/latest/authorization_services/#_service_overview).

## API Documentation

API documentation can be found here: [OpenAPI Spec](https://api.data.oslo.systems/okdata-permission-api/openapi.json).

### Known issues

#### Listing UMA policies (permissions) fails

Due to a bug in Keycloak ([#11284](https://github.com/keycloak/keycloak/issues/11284), fixed in Keycloak 18), where listing UMA policies fails when a user who was used in a policy gets deleted, the permission API consequently fails when attempting to list these policies:

```
requests.exceptions.HTTPError: 500 Server Error: Internal Server Error for url:
    https://<keycloak-server-url>/auth/realms/api-catalog/authz/protection/uma-policy/?max=300&first=0
```

If this error occurs, all references to the deleted user must be manually deleted from the affected policies. This is done by using previously backed up permissions and the scripts below. If the deleted user is not known, the user must first be identified by narrowing down the affected policies using the above-mentioned Keycloak endpoint (see `scripts/list_permissions.py`).

```sh
# Replace a deleted user in all policies by another
$ python -m scripts.clean_backup \
    --input permissions_backup.json \
    --output permissions_backup_cleaned.json \
    replace-user \
    --user-id homersimpson \
    --user-type user \
    --replacement-user-id janedoe \
    --replacement-user-type user

# Restore cleaned permissions
$ python -m scripts.restore_permissions_backup \
    --env dev \
    --input permissions_backup_cleaned.json \
    --skip-deleted-resources \
    --apply # Skip for dry-run
```

**Note**: The restore script works by deleting and re-creating the permissions found in the input file. Be sure to clean out all users that may be deleted since Keycloak does not recreate policies containing these users.

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

Deploy to both dev and prod is automatic via GitHub Actions on push to main. You
can alternatively deploy from local machine with: `make deploy` or `make
deploy-prod`.
