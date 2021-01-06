from dataplatform_keycloak import ResourceServer
from pprint import PrettyPrinter


pp = PrettyPrinter(indent=2)

if __name__ == "__main__":
    rm = ResourceServer(local=False)

    rm.create_dataset_resource("some-dataset-20", "TEAM-Ingrids Team 1234")
