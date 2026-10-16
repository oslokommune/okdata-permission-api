.DEV_PROFILE := okdata-dev
.PROD_PROFILE := okdata-prod

GLOBAL_PY := python3
BUILD_VENV ?= .build_venv
BUILD_PY := $(BUILD_VENV)/bin/python

# Deployed Git revision, formatted as `<branch>:<short-sha>`.
GIT_REV = $(shell git rev-parse --abbrev-ref HEAD):$(shell git rev-parse --short=7 HEAD)

DEV_IMAGE_REPO = $(shell aws sts get-caller-identity --profile $(.DEV_PROFILE) --query Account --output text).dkr.ecr.eu-west-1.amazonaws.com/serverless-okdata-permission-api-dev
PROD_IMAGE_REPO = $(shell aws sts get-caller-identity --profile $(.PROD_PROFILE) --query Account --output text).dkr.ecr.eu-west-1.amazonaws.com/serverless-okdata-permission-api-prod

.PHONY: init
init: $(BUILD_VENV)

$(BUILD_VENV):
	$(GLOBAL_PY) -m venv $(BUILD_VENV)
	$(BUILD_PY) -m pip install -U pip
	$(BUILD_PY) -m pip install -r requirements.txt

.PHONY: format
format: $(BUILD_VENV)/bin/black
	$(BUILD_PY) -m black .

.PHONY: test
test: $(BUILD_VENV)/bin/tox setup-keycloak-local
	$(BUILD_PY) -m tox -p auto -o
	make tear-down-keycloak-local

.PHONY: validate
validate:
	sam validate --lint --region eu-west-1

.PHONY: upgrade-deps
upgrade-deps: $(BUILD_VENV)/bin/pip-compile
	$(BUILD_VENV)/bin/pip-compile -U

.PHONY: deploy
deploy: login-dev init format test validate
	@echo "\nDeploying to stage: dev\n"
	sam build
	sam deploy --config-env dev --profile $(.DEV_PROFILE) --image-repository $(DEV_IMAGE_REPO) --parameter-overrides "Stage=dev GitRev=$(GIT_REV)"

.PHONY: deploy-prod
deploy-prod: login-prod init format test validate
	sam build
	sam deploy --config-env prod --profile $(.PROD_PROFILE) --image-repository $(PROD_IMAGE_REPO) --parameter-overrides "Stage=prod GitRev=$(GIT_REV)"

.PHONY: undeploy
undeploy: login-dev
	@echo "\nUndeploying stage: dev\n"
	sam delete --config-env dev --profile $(.DEV_PROFILE)

.PHONY: undeploy-prod
undeploy-prod: login-prod
	@echo "\nUndeploying stage: prod\n"
	sam delete --config-env prod --profile $(.PROD_PROFILE)

setup-keycloak-local: ## Run a local Keycloak instance running in docker
	docker compose \
		-f keycloak-compose.yaml \
		up -d

tear-down-keycloak-local: ## Stop and remove local Keycloak instance running in docker
	docker compose \
		-f keycloak-compose.yaml \
		down -v --remove-orphans || true

stop-keycloak-local: ## Stop local Keycloak instance running in docker
	docker compose \
		-f keycloak-compose.yaml \
		stop

.PHONY: populate-local-keycloak
populate-local-keycloak: setup-keycloak-local
	$(BUILD_PY) -m tests.setup.populate_local_keycloak

# Run and populate local keycloak instance and okdata-permission-api service
# The client-secret values below are not really secret values since they are only for testing on local machines
.PHONY: run
run: populate-local-keycloak $(BUILD_VENV)/bin/uvicorn
	RESOURCE_SERVER_CLIENT_ID=okdata-resource-server \
	RESOURCE_SERVER_CLIENT_SECRET=8acda364-eafa-4a03-8fa6-b019a48ddafe \
	CLIENT_ID=okdata-permission-api \
	CLIENT_SECRET=868d1ca9-4d94-4c1e-a2e4-9f032bd8ae08 \
	KEYCLOAK_REALM=localtest \
	KEYCLOAK_SERVER=http://localhost:35789 \
	KEYCLOAK_TEAM_ADMIN_USERNAME=team-admin \
	KEYCLOAK_TEAM_ADMIN_PASSWORD=team-admin-password \
	LOG_LEVEL=DEBUG \
	$(BUILD_VENV)/bin/uvicorn app:app --reload

.PHONY: login-dev
login-dev:
	aws sts get-caller-identity --profile $(.DEV_PROFILE) || aws sso login --profile=$(.DEV_PROFILE)

.PHONY: login-prod
login-prod:
	aws sts get-caller-identity --profile $(.PROD_PROFILE) || aws sso login --profile=$(.PROD_PROFILE)

.PHONY: build
build: $(BUILD_VENV)/bin/wheel $(BUILD_VENV)/bin/twine
	$(BUILD_PY) setup.py sdist bdist_wheel

###
# Python build dependencies
##

$(BUILD_VENV)/bin/pip-compile: $(BUILD_VENV)
	$(BUILD_PY) -m pip install -U pip-tools

$(BUILD_VENV)/bin/%: $(BUILD_VENV)
	$(BUILD_PY) -m pip install -U $*
