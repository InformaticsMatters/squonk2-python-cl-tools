#!/usr/bin/env python
# pylint: disable=invalid-name

"""Gets all Jobs executed for a given organisation and from date: -

    get-job-executions.py syg org-d60467df-d226-43c4-aee8-388fa8620ab4 2023-12-01

Displays the results in table form (like PSQL) with columns: -

- Username
- Job (collection/name/version)
- Started
- Unit name
- Product name

In this version "Project X" units are excluded.
"""
import argparse
import sys
from typing import Dict, List
import urllib3

from squonk2.auth import Auth
from squonk2.as_api import AsApi, AsApiRv
from squonk2.environment import Environment

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_UNITS_TO_EXCLUDE: List[str] = ["Project X"]


def main(c_args: argparse.Namespace) -> None:

    _ = Environment.load()
    env: Environment = Environment(c_args.environment)
    AsApi.set_api_url(env.as_api)

    token: str = Auth.get_access_token(
        keycloak_url=env.keycloak_url,
        keycloak_realm=env.keycloak_realm,
        keycloak_client_id=env.keycloak_as_client_id,
        username=env.admin_user,
        password=env.admin_password,
    )
    if not token:
        print("Failed to get token")
        sys.exit(1)

    # Get all the Products (and Units) for the Organisation
    organisation_products: Dict[str, Dict[str, str]] = {}
    j_rv: AsApiRv = AsApi.get_products_for_organisation(token, org_id=args.organisation)
    max_unit_length = 0
    max_product_length = 0
    for product in j_rv.msg['products']:

        unit_name = product['unit']['name']
        if unit_name in _UNITS_TO_EXCLUDE:
            continue

        if len(unit_name) > max_unit_length:
            max_unit_length = len(unit_name)

        product_name = product['product']['name']
        if len(product_name) > max_product_length:
            max_product_length = len(product_name)
        organisation_products[product['product']['id']] = {'unit': unit_name, 'product': product_name}

    # Get all the Jobs for each Product
    results: List[List[str]] = []
    max_username_length = 0
    max_job_length = 0
    for organisation_product in organisation_products.keys():
        j_rv = AsApi.get_product_charges(token, product_id=organisation_product, from_=args.from_date)
        for processing_charge in j_rv.msg['processing_charges']:

            username: str = processing_charge['charge']['username']
            if len(username) > max_username_length:
                max_username_length = len(username)

            collection: str = processing_charge['charge']['additional_data']['job_collection']
            job_name: str = processing_charge['charge']['additional_data']['job_job']
            version: str = processing_charge['charge']['additional_data']['job_version']
            job: str = f"{collection}/{job_name}/{version}"
            if len(job) > max_job_length:
                max_job_length = len(job)

            started: str = processing_charge['charge']['additional_data']['started']

            unit_name = organisation_products[organisation_product]['unit']
            product_name = organisation_products[organisation_product]['product']
            results.append([username, job, started, unit_name, product_name])

    col1 = "Username"
    col2 = "Job (collection/name/version)"
    col4 = "Unit"
    col5 = "Product"
    print(f"{col1:<{max_username_length}} | {col2:<{max_job_length}} | Started             | {col4:<{max_unit_length}} | {col5:<{max_product_length}}")
    separator = '-' * (1 + max_username_length)
    separator += '+' + '-' * (2 + max_job_length)
    separator += '+---------------------'
    separator += '+' + '-' * (2 + max_unit_length)
    separator += '+' + '-' * (1 + max_product_length)
    print(separator)
    for result in results:
        print(f"{result[0]:<{max_username_length}} | {result[1]:<{max_job_length}} | {result[2]} | {result[3]:<{max_unit_length}} | {result[4]:<{max_product_length}}")
    print(f"({len(results)} rows)")


if __name__ == '__main__':
    # Build a command-line parser and parse it...
    parser = argparse.ArgumentParser(
        description='Delete All DM Project Instances')
    parser.add_argument('environment', type=str, help='The environment name')
    parser.add_argument('organisation', type=str, help='The organisation ID')
    parser.add_argument('from_date', type=str, help='The date to start from (inclusive)')
    args = parser.parse_args()

    main(args)
