a = {
    "entitlements": False,
    "results": [
        {
            "allowedScopes": [],
            "policies": [
                {
                    "associatedPolicies": [
                        {
                            "associatedPolicies": [],
                            "policy": {
                                "config": {},
                                "decisionStrategy": "UNANIMOUS",
                                "id": "cff369af-976e-4f16-b155-5bb2bfc014ec",
                                "logic": "POSITIVE",
                                "name": "838b2eb0-4067-485e-b823-cda4e00c46b8",
                                "resources": [],
                                "scopes": [],
                                "type": "group",
                            },
                            "scopes": [],
                            "status": "PERMIT",
                        }
                    ],
                    "policy": {
                        "config": {},
                        "decisionStrategy": "UNANIMOUS",
                        "description": "Allows for owner "
                        "operations on "
                        "dataset: "
                        "kebab-rating "
                        "(User-Managed "
                        "Policy)",
                        "id": "2df04ced-90d0-4647-87c4-1e89ba174c97",
                        "logic": "POSITIVE",
                        "name": "kebab-rating-owner",
                        "resources": ["kebab-rating"],
                        "scopes": ["ok:origo:dataset:owner"],
                        "type": "uma",
                    },
                    "scopes": [],
                    "status": "PERMIT",
                },
                {
                    "associatedPolicies": [
                        {
                            "associatedPolicies": [],
                            "policy": {
                                "config": {},
                                "decisionStrategy": "UNANIMOUS",
                                "id": "8b14b5a5-4fae-489a-9c05-265e49764fd7",
                                "logic": "POSITIVE",
                                "name": "02faef94-8401-483d-9dc9-8f239d4cba8e",
                                "resources": [],
                                "scopes": [],
                                "type": "group",
                            },
                            "scopes": [],
                            "status": "PERMIT",
                        }
                    ],
                    "policy": {
                        "config": {},
                        "decisionStrategy": "UNANIMOUS",
                        "description": "Allows for write "
                        "on dataset: "
                        "kebab-rating "
                        "(User-Managed "
                        "Policy)",
                        "id": "4fbc30c8-9956-4875-9901-4955d762fbff",
                        "logic": "POSITIVE",
                        "name": "kebab-rating-update",
                        "resources": ["kebab-rating"],
                        "scopes": ["ok:origo:dataset:update"],
                        "type": "uma",
                    },
                    "scopes": [],
                    "status": "PERMIT",
                },
                {
                    "associatedPolicies": [
                        {
                            "associatedPolicies": [],
                            "policy": {
                                "config": {},
                                "decisionStrategy": "UNANIMOUS",
                                "id": "2a5c4965-2349-4fb9-8366-74e63b573e23",
                                "logic": "POSITIVE",
                                "name": "11ce0cf0-9e29-43b4-9ca6-ba6c191aa63f",
                                "resources": [],
                                "scopes": [],
                                "type": "user",
                            },
                            "scopes": [],
                            "status": "DENY",
                        },
                        {
                            "associatedPolicies": [],
                            "policy": {
                                "config": {},
                                "decisionStrategy": "UNANIMOUS",
                                "id": "2f2a7053-de02-4ef8-a399-4ebe64d1aa48",
                                "logic": "POSITIVE",
                                "name": "3c04499f-0be5-4060-8c25-ec67afde89ca",
                                "resources": [],
                                "scopes": [],
                                "type": "group",
                            },
                            "scopes": [],
                            "status": "PERMIT",
                        },
                    ],
                    "policy": {
                        "config": {},
                        "decisionStrategy": "UNANIMOUS",
                        "description": "Allows for read "
                        "on dataset: "
                        "kebab-rating "
                        "(User-Managed "
                        "Policy)",
                        "id": "872d0cd7-12a9-4837-997b-d328e4217de5",
                        "logic": "POSITIVE",
                        "name": "kebab-rating-read",
                        "resources": ["kebab-rating"],
                        "scopes": ["ok:origo:dataset:read"],
                        "type": "uma",
                    },
                    "scopes": ["ok:origo:dataset:read"],
                    "status": "DENY",
                },
                {
                    "associatedPolicies": [
                        {
                            "associatedPolicies": [],
                            "policy": {
                                "config": {},
                                "decisionStrategy": "UNANIMOUS",
                                "id": "87223dff-3343-46a9-a6ec-b977c4e98922",
                                "logic": "POSITIVE",
                                "name": "973bf415-c073-4cb8-8112-5b262870eabf",
                                "resources": [],
                                "scopes": [],
                                "type": "group",
                            },
                            "scopes": [],
                            "status": "PERMIT",
                        }
                    ],
                    "policy": {
                        "config": {},
                        "decisionStrategy": "UNANIMOUS",
                        "description": "Allows for write "
                        "on dataset: "
                        "kebab-rating "
                        "(User-Managed "
                        "Policy)",
                        "id": "a2e82fad-e9a0-4073-ac31-d43ab4cef7dd",
                        "logic": "POSITIVE",
                        "name": "kebab-rating-write",
                        "resources": ["kebab-rating"],
                        "scopes": ["ok:origo:dataset:write"],
                        "type": "uma",
                    },
                    "scopes": [],
                    "status": "PERMIT",
                },
            ],
            "resource": {
                "_id": "c3847264-c216-4778-9138-756dcbaaf67e",
                "name": "kebab-rating with scopes " "[ok:origo:dataset:read]",
            },
            "scopes": [
                {
                    "id": "b63f9da8-1886-4e4a-b0be-dd6af9695037",
                    "name": "ok:origo:dataset:read",
                }
            ],
            "status": "DENY",
        }
    ],
    "rpt": {
        "acr": "1",
        "aud": "poc-resource-server",
        "authorization": {"permissions": []},
        "azp": "poc-resource-server",
        "email": "janedoe@oslo.kommune.no",
        "email_verified": False,
        "exp": 1604695253,
        "family_name": "Doe",
        "given_name": "Jane",
        "iat": 1604677253,
        "jti": "4db76e90-a368-454e-98e1-0e51277e0b23",
        "name": "Jane Doe",
        "preferred_username": "janedoe",
        "realm_access": {"roles": ["ok-user", "offline_access", "uma_authorization"]},
        "resource_access": {
            "account": {
                "roles": ["manage-account", "manage-account-links", "view-profile"]
            }
        },
        "scope": "profile email",
        "session_state": "9b920f35-5a15-4581-80e4-6171c029b350",
        "sub": "ef93310e-5cc6-4024-886b-ea1821464fd7",
        "typ": "Bearer",
    },
    "status": "DENY",
}
