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


janedoe = "janedoe"
homersimpson = "homersimpson"
nopermissions = "nopermissions"
team2member = "team2member"

team1 = "team1"
team2 = "team2"

user1 = {"username": janedoe, "groups": [team1]}
user2 = {"username": homersimpson, "groups": []}
user3 = {"username": nopermissions, "groups": []}
user4 = {"username": team2member, "groups": [team2]}

users = [user1, user2, user3, user4]
