from dataplatform_keycloak.groups import (
    team_attribute_to_group_attribute,
    team_name_to_group_name,
)

server_url = "http://localhost:35789"
server_auth_url = f"{server_url}/auth/"

realm_name = "localtest"

# Client id and secret for the resource server
resource_server_id = "resource-server"
resource_server_secret = "8acda364-eafa-4a03-8fa6-b019a48ddafe"

# Client id and secret for okdata-permission-api (self)
client_id = "okdata-permission-api"
client_secret = "868d1ca9-4d94-4c1e-a2e4-9f032bd8ae08"

# Client id and secret for a client that will be permitted to create permissions
create_permissions_client_id = "some-service"
create_permissions_client_secret = "77a44253-8649-4b8c-9f24-ce06f8edca0c"

# Client id and secret for a client that will be permitted to remove a team from all permissions
remove_team_client_id = "teams-api"
remove_team_client_secret = "a49ce819-39db-4777-b18c-de57c87a63d2"

# Team admin user that is authorized for CRUD operations on teams (groups) in KeyCloak
# https://github.com/oslokommune/dataplattform/blob/master/dataplattform-internt/arkitektur/utviklerportalen.md#hvordan-sette-opp-admin-bruker-for-teams-backend
# https://github.com/oslokommune/teams/blob/master/src/test/kotlin/no/kommune/oslo/origodigi/teams/common/init_keycloak/ConfigureKeycloakForTeamsTest.kt#L105
team_admin_username = "team-admin"
team_admin_password = "team-admin-password"
team_admin_client_roles = [
    "manage-users",
    "query-groups",
    "query-users",
    "view-users",
    "view-realm",
]


janedoe = "janedoe"
homersimpson = "homersimpson"
misty = "misty"
nopermissions = "nopermissions"
team2member = "team2member"

team1 = "team1"
team2 = "team2"
team3 = "team3"
teams = [team1, team2, team3]
nonteamgroup = "group1"

user1 = {
    "username": janedoe,
    "groups": [team_name_to_group_name(team1), team_name_to_group_name(team3)],
}
user2 = {"username": homersimpson, "groups": []}
user3 = {"username": nopermissions, "groups": []}
user4 = {"username": team2member, "groups": [team_name_to_group_name(team2)]}
user5 = {
    "username": misty,
    "firstName": "Misty",
    "lastName": "Williams",
    "groups": [
        team_name_to_group_name(team1),
        team_name_to_group_name(team2),
        nonteamgroup,
    ],
}


users = [user1, user2, user3, user4, user5]
groups = [
    {"name": team_name_to_group_name(team1), "attributes": {}},
    {"name": team_name_to_group_name(team2), "attributes": {}},
    {
        "name": team_name_to_group_name(team3),
        "attributes": {
            team_attribute_to_group_attribute("email"): ["foo@example.org"],
            "nonteamattribute": ["secret"],
        },
    },
    {"name": nonteamgroup, "attributes": {}},
]

internal_team_realm_role = "origo-team"
internal_teams = [team1, team3]
