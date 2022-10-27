#!/usr/bin/env python
# pylint: disable=invalid-name

"""Deletes all instances from the DM namespace.

This utility checks all projects the user has access to
and then removes instances that are found. The assumption here
is that the user has admin rights.

The utility is useful in clearing out Job Operator objects
prior to a major upgrade.
"""
import argparse
from typing import Dict, List, Optional, Tuple
import urllib3

from squonk2.auth import Auth
from squonk2.dm_api import DmApi, DmApiRv
from squonk2.environment import Environment

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

    # The collection of instances
    project_instances: Dict[str, List[Tuple[str, str]]] = {}

    # To see everything we need to become admin...
    rv: DmApiRv = DmApi.set_admin_state(token, admin=True)
    assert rv.success

    # Iterate through projects to get instances...
    num_instances: int = 0
    p_rv = DmApi.get_available_projects(token)
    if p_rv.success:
        for project in p_rv.msg['projects']:
            p_id: str = project['project_id']
            p_name: str = project['name']
            print(f"+ Found project '{p_name}' [{p_id}]")
            pi_rv = DmApi.get_project_instances(token, project_id=p_id)
            instances: List[str] = []
            if pi_rv.success:
                for instance in pi_rv.msg['instances']:
                    i_id: str = instance['id']
                    i_name: str = instance['name']
                    i_owner: str = instance['owner']
                    print(f"  Found instance '{i_name}' [{i_id}] ({i_owner})")
                    instances.append((i_id, i_owner))
                    num_instances += 1
            if instances:
                project_instances[p_id] = instances

    num_deleted: int = 0
    num_failed: int = 0
    if c_args.do_it:
        print("Deleting...")
        for p_id, i_items in project_instances.items():
            for i_id, i_owner in i_items:
                # To delete we need to impersonate the owner of the instance...
                rv = DmApi.set_admin_state(token, admin=True, impersonate=i_owner)
                assert rv.success
                rv = DmApi.delete_instance(token, instance_id=i_id)
                if rv.success:
                    num_deleted += 1
                else:
                    num_failed += 1
        print("Deleted")

    # Revert to a non-admin state
    # To see everything we need to become admin...
    rv = DmApi.set_admin_state(token, admin=False)
    assert rv.success

    print(f"Found {num_instances}")
    print(f"Deleted {num_deleted}")
    print(f"Failed to deleted {num_failed}")


if __name__ == '__main__':
    # Build a command-line parser and parse it...
    parser = argparse.ArgumentParser(
        description='Delete All DM Project Instances')
    parser.add_argument('environment', type=str, help='The environment name')
    parser.add_argument(
        '--do-it',
        help='Set to actually delete, if not set the instances are listed',
        action='store_true',
    )
    args = parser.parse_args()

    main(args)
