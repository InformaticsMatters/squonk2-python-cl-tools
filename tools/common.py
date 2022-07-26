"""Stuff that's used by more than one tool.
"""
from collections import namedtuple
import os
from typing import List, Optional

# The ID for an internal "test" unit
TEST_UNIT: str = "unit-11111111-1111-1111-1111-111111111111"

# The login names of the well-known set of test users.
TEST_USER_NAMES: List[str] = [
    "dmit-user-a",
    "dmit-user-b",
    "dmit-user-c",
    "dmit-user-d",
    "dmit-user-admin",
]

# A namedtuple for the environment.
# It contains vales, extracted from the following variables: -
# - SQUONK2_DMAPI_URL
# - SQUONK2_ASAPI_URL
# - SQUONK2_KEYCLOAK_URL
# - SQUONK2_KEYCLOAK_REALM
# - SQUONK2_KEYCLOAK_AS_CLIENT_ID
# - SQUONK2_KEYCLOAK_DM_CLIENT_ID
# - SQUONK2_KEYCLOAK_USER
# - SQUONK2_KEYCLOAK_USER_PASSWORD
Env: namedtuple = namedtuple(
    "Env",
    [
        "dmapi_url",
        "asapi_url",
        "keycloak_url",
        "keycloak_realm",
        "keycloak_as_client_id",
        "keycloak_dm_client_id",
        "keycloak_user",
        "keycloak_user_password",
    ],
)


def get_env() -> Optional[Env]:
    """Get the environment variables.
    All must be defined.
    """
    env: Optional[Env] = None
    try:
        env: Env = Env(
            dmapi_url=os.environ["SQUONK2_DMAPI_URL"],
            asapi_url=os.environ["SQUONK2_ASAPI_URL"],
            keycloak_url=os.environ["SQUONK2_KEYCLOAK_URL"],
            keycloak_realm=os.environ["SQUONK2_KEYCLOAK_REALM"],
            keycloak_as_client_id=os.environ["SQUONK2_KEYCLOAK_AS_CLIENT_ID"],
            keycloak_dm_client_id=os.environ["SQUONK2_KEYCLOAK_DM_CLIENT_ID"],
            keycloak_user=os.environ["SQUONK2_KEYCLOAK_USER"],
            keycloak_user_password=os.environ["SQUONK2_KEYCLOAK_USER_PASSWORD"],
        )
    except KeyError as e:
        print(f"ERROR: You need to define {e}")
    return env
