#!/usr/bin/env python
"""Creates organisations using a YAML file to define their names and owners.
The file is simply a list of organisations that have a `name`, and `owner`
with an optional list of `units` with names and billing days (with a default of '3)
(which are created in the same way).
"""
import argparse
from pathlib import Path
import sys
from typing import Any, Dict, List
import urllib3

from rich.console import Console
from squonk2.auth import Auth
from squonk2.as_api import AsApi, AsApiRv
from squonk2.environment import Environment
import yaml

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def main(c_args: argparse.Namespace, filename: str) -> None:
    """Main function."""

    console = Console()

    _ = Environment.load()
    env: Environment = Environment(c_args.environment)
    AsApi.set_api_url(env.as_api)

    token: str = Auth.get_access_token(
        keycloak_url=env.keycloak_url,
        keycloak_realm=env.keycloak_realm,
        keycloak_client_id=env.keycloak_as_client_id,
        username=env.admin_user,
        password=env.
        admin_password,
    )
    if not token:
        print("Failed to get token")
        sys.exit(1)

    # Get the current organisations (as an admin user you should see them all)
    org_rv: AsApiRv = AsApi.get_organisations(token)
    if not org_rv.success:
        console.log(':boom: Failed to get existing organisations')
        sys.exit(1)
    existing_org_names: List[str] = []
    existing_orgs: Dict[str, str] = {}
    for org in org_rv.msg['organisations']:
        if org['name'] not in ['Default']:
            existing_orgs[org['name']] = org['id']
            existing_org_names.append(org['name'])

    # Just read the list from the chosen file
    file_content: str = Path(filename).read_text(encoding='utf8')
    orgs: List[Dict[str, Any]] = yaml.load(file_content, Loader=yaml.FullLoader)
    # Create the organisations one at a time (to handle any errors gracefully)
    for org in orgs:
        org_name: str = org.get('name')
        if not org_name:
            console.log(':boom: File has an organisation without a name')
            sys.exit(1)
        owner: str = org.get('owner')
        if not owner:
            console.log(':boom: File has an organisation without an owner')
            sys.exit(1)
        # Now try and create the organisation (if it's new)...
        if org_name in existing_org_names:
            console.log(f':white_check_mark: Skipping organisation "{org_name}" - it already exists')
        else:
            org_rv: AsApiRv = AsApi.create_organisation(token, org_name=org_name, org_owner=owner)
            if org_rv.success:
                emoji = ':white_check_mark:'
                existing_orgs[org_name] = org_rv.msg['id']
            else:
                emoji = ':cross_mark:'
            # Log
            console.log(f'{emoji} {org_name} ({owner})')
        # Units?
        if 'units' in org:
            org_rv: AsApiRv = AsApi.get_units(token, org_id=existing_orgs[org_name])
            existing_unit_names: List[str] = [unit['name'] for unit in org_rv.msg['units']]
            for unit in org['units']:
                unit_name: str = unit.get('name')
                if not unit_name:
                    console.log(':boom: File has a unit without a name')
                    sys.exit(1)
                if unit_name in existing_unit_names:
                    console.log(f':white_check_mark: Skipping unit "{org_name}/{unit_name}" - it already exists')
                else:
                    billing_day: int = unit.get('billing_day', 3)
                    # Now try and create the unit (if it's new)...
                    unit_rv: AsApiRv = AsApi.create_unit(token, org_id=existing_orgs[org_name], unit_name=unit_name, billing_day=billing_day)
                    emoji = ':white_check_mark:' if unit_rv.success else ':cross_mark:'
                    # Log
                    console.log(f'  {emoji} {unit_name} (billing day {billing_day})')


if __name__ == "__main__":

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        prog="create-organisations",
        description="Creates Organisations and Units (from a YAML file). You will need admin privileges to use this tool."
    )
    parser.add_argument('environment', type=str, help='The environment name')
    parser.add_argument('file', type=str, help='The source file')
    args: argparse.Namespace = parser.parse_args()

    filename: str = args.file
    if not filename.endswith('.yaml'):
        filename += '.yaml'

    # File must exist
    if not Path(filename).is_file():
        parser.error(f"File '{filename}' does not exist")

    main(args, filename)
