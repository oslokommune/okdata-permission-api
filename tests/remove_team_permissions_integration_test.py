from dataplatform_keycloak.resource_server import ResourceServer
from models import UserType, User
from tests.setup import local_keycloak_config as kc_config
from tests.setup import populate_local_keycloak
from tests.utils import auth_header, get_token_for_service, get_bearer_token_for_user


class TestRemoveTeamPermissions:
    # PUT /remove_team_permissions/{team_id}
    def test_remove_team_permissions(self, mock_client):
        populate_local_keycloak.populate()
        resource_server = ResourceServer()

        # Create 120 permissions and give team1 read access to every 10th resource
        for i in range(0, 120):
            resource_name = f"okdata:dataset:test-remove-teams-{i}"
            resource_server.create_resource(
                resource_name,
                owner=User(user_id=kc_config.janedoe, user_type=UserType.USER),
            )
            if i % 10 == 0:
                resource_server.update_permission(
                    resource_name,
                    "okdata:dataset:read",
                    [User(user_id=kc_config.team1, user_type=UserType.GROUP)],
                )

        # Ensure that test data is set up as expected
        team_permissions_before_remove = resource_server.list_permissions(
            team=kc_config.team1
        )
        assert len(team_permissions_before_remove) == 12

        # Ensure 403 for unauthorized entities
        forbidden_response = mock_client.put(
            f"/remove_team_permissions/{kc_config.team1}",
            headers=auth_header(
                get_token_for_service(
                    service_client_id=kc_config.create_permissions_client_id,
                    service_client_secret=kc_config.create_permissions_client_secret,
                )
            ),
        )
        assert forbidden_response.status_code == 403

        # Remove team1 from all permissions

        access_token = get_token_for_service(
            kc_config.remove_team_client_id, kc_config.remove_team_client_secret
        )
        remove_team_response = mock_client.put(
            f"/remove_team_permissions/{kc_config.team1}",
            headers=auth_header(access_token),
        )
        assert remove_team_response.status_code == 200

        # Ensure that there are no longer any permissions associated with team1
        team_permissions_after_remove = resource_server.list_permissions(
            team=kc_config.team1
        )
        assert len(team_permissions_after_remove) == 0

        # Ensure that deleting the team (team1) does not break the system
        populate_local_keycloak.delete_team(kc_config.team1)

        assert resource_server.get_user_permissions(
            get_bearer_token_for_user(kc_config.janedoe)
        )
