import json
from dataplatform_keycloak import ResourceServer
from pydantic import ValidationError
from models import CreateResourceBody

resource_server = ResourceServer()


# TODO: Ensure that caller is authorized to perform this action
def create_resource(event, context):
    try:
        request_body = CreateResourceBody(**json.loads(event["body"]))
    except ValidationError:
        # TODO: log exception
        {"statusCode": 400, "body": json.dumps({"message": "Invalid body"})}

    resource_server.create_dataset_resource(
        dataset_id=request_body.dataset_id,
        owner=request_body.owner,
    )

    return {"statusCode": 201, "body": json.dumps({"message": "Created"})}
