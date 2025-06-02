#!/usr/bin/env python
"""Gets organisations and units.
"""
import argparse
import sys
import urllib3

from rich.console import Console
from squonk2.auth import Auth
from squonk2.as_api import AsApi, AsApiRv
from squonk2.environment import Environment

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def main(c_args: argparse.Namespace) -> None:
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
    existing_org_names: list[str] = []
    existing_orgs: dict[str, str] = {}
    for org in org_rv.msg['organisations']:
        if org['name'] not in ['Default']:
            existing_orgs[org['name']] = org['id']
            existing_org_names.append(org['name'])

    org_count: int = 0
    unit_count: int = 0
    product_count: int = 0
    existing_org_names.sort()
    for existing_org_name in existing_org_names:
        org_count += 1
        org_id: str = existing_orgs[existing_org_name]
        console.log(f'ORG={existing_org_name} / {org_id}')
        unit_names: list[str] = []
        units: dict[str, str] = {}
        unit_rv: AsApiRv = AsApi.get_units(token, org_id=org_id)
        for unit in unit_rv.msg["units"]:
            unit_names.append(unit["name"])
            units[unit["name"]] = unit["id"]
        unit_names.sort()
        for unit_name in unit_names:
            unit_count += 1
            unit_id = units[unit_name]
            console.log(f'  UNIT={unit_name} / {unit_id}')
            products_rv: AsApiRv = AsApi.get_products_for_unit(token, unit_id=unit_id)
            product_names: list[str] = []
            products: dict[str, str] = {}
            for product in products_rv.msg["products"]:
                product_id: str = product["product"]["id"]
                product_name: str = product["product"]["name"]
                product_names.append(product_name)
                products[product_name] = product_id
            product_names.sort()
            for product_name in product_names:
                product_count += 1
                product_id = products[product_name]
                console.log(f'    PRODUCT="{product_name}" / {product_id}')

    console.log(f'{org_count} Organisations')
    console.log(f'{unit_count} Units')
    console.log(f'{product_count} Products')


if __name__ == "__main__":

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        prog="get-orgs-and-units",
        description="Get Organisations, Units, and Products. You will need admin privileges to use this tool."
    )
    parser.add_argument('environment', type=str, help='The environment name')
    args: argparse.Namespace = parser.parse_args()

    main(args)
