import os
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Tuple, Optional

import pytz
from fastapi import Depends, APIRouter, status
from okdata.resource_auth import ResourceAuthorizer

from models import (
    CreateWebhookTokenBody,
    WebhookTokenAuthResponse,
    WebhookTokenItem,
    WebhookTokenOperation,
)
from resources.authorizer import AuthInfo
from resources.errors import ErrorResponse, error_message_models
from webhook_tokens import WebhookTokensTable


router = APIRouter()

logger = logging.getLogger()
logger.setLevel(os.environ.get("LOG_LEVEL", logging.INFO))


def webhook_tokens_table():
    return WebhookTokensTable()


def resource_authorizer():
    return ResourceAuthorizer()


@router.post(
    "/{dataset_id}/tokens",
    status_code=status.HTTP_201_CREATED,
    responses=error_message_models(
        status.HTTP_400_BAD_REQUEST,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        status.HTTP_403_FORBIDDEN,
    ),
)
def create_webhook_token(
    dataset_id: str,
    body: CreateWebhookTokenBody,
    auth_info: AuthInfo = Depends(),
    resource_authorizer=Depends(resource_authorizer),
    webhook_tokens_table=Depends(webhook_tokens_table),
) -> WebhookTokenItem:
    if not resource_authorizer.has_access(
        auth_info.bearer_token, "okdata:dataset:admin", f"okdata:dataset:{dataset_id}"
    ):
        raise ErrorResponse(status.HTTP_403_FORBIDDEN, "Forbidden")

    # Create token
    token_created = datetime.utcnow().replace(tzinfo=pytz.utc)
    token_expires = token_created + timedelta(days=(365 * 2))

    webhook_token_item = WebhookTokenItem(
        token=uuid.uuid4(),
        created_by=auth_info.principal_id,
        dataset_id=dataset_id,
        operation=body.operation,
        created_at=token_created,
        expires_at=token_expires,
    )

    webhook_tokens_table.put_webhook_token_item(webhook_token_item)

    return webhook_token_item


@router.get(
    "/{dataset_id}/tokens",
    status_code=status.HTTP_200_OK,
    responses=error_message_models(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        status.HTTP_403_FORBIDDEN,
    ),
)
def list_webhook_tokens(
    dataset_id: str,
    auth_info: AuthInfo = Depends(),
    resource_authorizer=Depends(resource_authorizer),
    webhook_tokens_table=Depends(webhook_tokens_table),
) -> List[WebhookTokenItem]:
    is_admin = resource_authorizer.has_access(
        auth_info.bearer_token, "okdata:dataset:admin", f"okdata:dataset:{dataset_id}"
    )

    if not is_admin:
        raise ErrorResponse(status.HTTP_403_FORBIDDEN, "Forbidden")

    return webhook_tokens_table.list_webhook_token_items(dataset_id)


@router.delete(
    "/{dataset_id}/tokens/{webhook_token}",
    status_code=status.HTTP_200_OK,
    responses=error_message_models(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        status.HTTP_403_FORBIDDEN,
        status.HTTP_404_NOT_FOUND,
    ),
)
def delete(
    dataset_id: str,
    webhook_token: str,
    auth_info: AuthInfo = Depends(),
    resource_authorizer=Depends(resource_authorizer),
    webhook_tokens_table=Depends(webhook_tokens_table),
) -> dict:
    is_admin = resource_authorizer.has_access(
        auth_info.bearer_token, "okdata:dataset:admin", f"okdata:dataset:{dataset_id}"
    )

    if not is_admin:
        raise ErrorResponse(status.HTTP_403_FORBIDDEN, "Forbidden")

    webhook_item: WebhookTokenItem = webhook_tokens_table.get_webhook_token_item(
        webhook_token, dataset_id
    )

    if not webhook_item:
        raise ErrorResponse(
            status.HTTP_404_NOT_FOUND,
            f"Provided token does not exist for dataset {dataset_id}",
        )

    webhook_tokens_table.delete_webhook_token_item(webhook_token, dataset_id)

    return {"message": f"Deleted {webhook_token} for dataset {dataset_id}"}


@router.get(
    "/{dataset_id}/tokens/{webhook_token}/authorize",
    status_code=status.HTTP_200_OK,
    responses=error_message_models(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    ),
)
def authorize_webhook_token(
    dataset_id: str,
    webhook_token: str,
    operation: WebhookTokenOperation,
    auth_info: AuthInfo = Depends(),
    webhook_tokens_table=Depends(webhook_tokens_table),
) -> WebhookTokenAuthResponse:
    try:
        webhook_token_item = webhook_tokens_table.get_webhook_token_item(
            webhook_token, dataset_id
        )
        if not webhook_token_item:
            return WebhookTokenAuthResponse(
                access=False,
                reason=f"Provided token is not associated to dataset-id: {dataset_id}",
            )

        has_access, reason = validate_webhook_token(webhook_token_item, operation)
        return WebhookTokenAuthResponse(access=has_access, reason=reason)
    except Exception as e:
        logger.exception(e)
        raise ErrorResponse(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Internal Server Error",
        )


def validate_webhook_token(
    webhook_token_item: WebhookTokenItem, operation: WebhookTokenOperation
) -> Tuple[bool, Optional[str]]:
    if webhook_token_item.operation != operation:
        return (
            False,
            f"Provided token does not have access to perform {operation.value} on {webhook_token_item.dataset_id}",
        )

    dt_now = datetime.utcnow().replace(tzinfo=pytz.utc)
    token_expired = webhook_token_item.expires_at < dt_now

    if token_expired:
        return False, "Provided token is expired"

    return True, None
