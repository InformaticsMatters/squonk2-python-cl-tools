#!/usr/bin/env python
# pylint: disable=invalid-name

"""Deletes all instances from the DM namespace that are considered 'old'.

This utility checks all projects the user has access to
and then removes instances that are found. The assumption here
is that the user has admin rights.
"""
import argparse
import sys
from datetime import datetime, timedelta
from typing import List, Optional, Tuple
import urllib3

from dateutil.parser import parse
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
    if not token:
        print("Failed to get token")
        sys.exit(1)

    # To see everything we need to become admin...
    rv: DmApiRv = DmApi.set_admin_state(token, admin=True)
    if not rv.success:
        print("Failed to set admin state")
        sys.exit(1)

    # Max age?
    max_stopped_age: timedelta = timedelta(hours=args.age)

    # The collection of instances
    old_instances: List[Tuple[str, str]] = []

    p_rv = DmApi.get_available_instances(token)
    now: datetime = datetime.utcnow()
    if p_rv.success:
        for instance in p_rv.msg['instances']:
            i_id: str = instance['id']
            i_rv = DmApi.get_instance(token, instance_id=i_id)
            if i_rv.success and 'stopped' in i_rv.msg:
                i_stopped: datetime = parse(i_rv.msg['stopped'])
                i_stopped_age: timedelta = now - i_stopped
                if i_stopped_age >= max_stopped_age:
                    i_name: str = i_rv.msg['name']
                    print(f"+ Found instance '{i_name}' [{i_id}] (Stopped {i_stopped_age})")
                    old_instances.append((i_id, i_rv.msg['owner']))

    num_deleted: int = 0
    num_failed: int = 0
    if c_args.do_it:
        print("Deleting...")
        for i_id, i_owner in old_instances:
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
    if not rv.success:
        print("Failed to unset admin state")
        sys.exit(1)

    print(f"Found {len(old_instances)}")
    print(f"Deleted {num_deleted}")
    print(f"Failed to deleted {num_failed}")


if __name__ == '__main__':
    # Build a command-line parser and parse it...
    parser = argparse.ArgumentParser(
        description='Delete All Old DM Project Instances')
    parser.add_argument('environment', type=str, help='The environment name')
    parser.add_argument(
        '--age',
        nargs='?',
        default=96,
        type=int,
        help='Age (hours) when an instance is considered "old"',
    )
    parser.add_argument(
        '--do-it',
        help='Set to actually delete, if not set the old instances are listed',
        action='store_true',
    )
    args = parser.parse_args()

    main(args)
