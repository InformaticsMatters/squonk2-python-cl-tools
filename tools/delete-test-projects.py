#!/usr/bin/env python
# pylint: disable=invalid-name

"""Deletes projects in the DM created by a built-in test user.
"""
import argparse
import sys
from typing import Any, Dict, List, Optional
import urllib3

from squonk2.auth import Auth
from squonk2.dm_api import DmApi, DmApiRv
from squonk2.environment import Environment

from common import TEST_UNIT, TEST_USER_NAMES

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def main(c_args: argparse.Namespace) -> None:

    _ = Environment.load()
    env: Environment = Environment(c_args.environment)
    DmApi.set_api_url(env.dm_api)

    token: str = Auth.get_access_token(
        keycloak_url=env.keycloak_url,
        keycloak_realm=env.keycloak_realm,
        keycloak_client_id=env.keycloak_dm_client_id,
        username=env.admin_user,
        password=env.admin_password,
    )
    if not token:
        print("Failed to get token")
        sys.exit(1)

    ret_val: DmApiRv = DmApi.get_available_projects(token)
    assert ret_val.success
    num_projects: int = 0
    num_projects_of_interest: int = 0
    num_deleted: int = 0
    projects: List[Dict[str, Any]] = ret_val.msg["projects"]
    for project in projects:
        num_projects += 1
        if project["owner"] in TEST_USER_NAMES:

            # Get key values form this project...
            p_id: str = project["project_id"]
            p_owner: str = project["owner"]
            p_name: str = project["name"]
            p_unit: str = project.get("unit_id")
            if p_unit and p_unit != TEST_UNIT:
                p_claimed = True
            else:
                p_claimed = False

            # Do delete something that's not ours
            # we need to switch to the Project owner
            ret_val = DmApi.set_admin_state(token, admin=True, impersonate=p_owner)
            assert ret_val.success

            num_projects_of_interest += 1
            msg: str = (
                f"project '{p_name}' (owner={p_owner} id={p_id} has_claim={p_claimed})"
            )
            if c_args.do_it:
                print(f"Deleting {msg}...")
                ret_val = DmApi.delete_project(token, project_id=p_id)
                if not ret_val.success:
                    print(f"ERROR: {ret_val.msg}")
                num_deleted += 1
            else:
                print(f"Found {msg}")

    print(
        "Done.\n"
        f"# Inspected {num_projects} projects\n"
        f"# {num_projects_of_interest} owned by a test user\n"
        f"# {num_deleted} deleted"
    )

    # Undo impersonation
    ret_val = DmApi.set_admin_state(token, admin=False)
    assert ret_val.success


if __name__ == "__main__":

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Delete all Projects owned by test users"
    )
    parser.add_argument('environment', type=str, help='The environment name')
    parser.add_argument(
        "--do-it",
        help="Set to actually delete, if not set the projects are listed",
        action="store_true",
    )
    args: argparse.Namespace = parser.parse_args()

    main(args)
