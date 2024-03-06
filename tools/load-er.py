#!/usr/bin/env python
"""Loads Job/Application Exchange Rates from a file.
"""
import argparse
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional
import urllib3

from rich.console import Console
from squonk2.auth import Auth
from squonk2.dm_api import DmApi, DmApiRv
from squonk2.environment import Environment
import yaml

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def main(c_args: argparse.Namespace, filename: str) -> None:
    """Main function."""

    console = Console()

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

    # Just read the list from the chosen file
    file_content: str = Path(filename).read_text(encoding='utf8')
    rates: List[Dict[str, Any]] = yaml.load(file_content, Loader=yaml.FullLoader)
    # Load the rates one at a time (to handle any errors gracefully)
    num_rates: int = 0
    num_rates_failed: int = 0
    for rate in rates:
        # A rate must have a collection, job and version
        collection: str = rate.get('collection')
        if not collection:
            console.log(':boom: File has a rate without a collection')
            sys.exit(1)
        job: str = rate.get('job')
        if not job:
            console.log(':boom:  File has a rate without a job')
            sys.exit(1)
        version: str = rate.get('version')
        if not version:
            console.log(':boom: File has a rate without a version')
            sys.exit(1)
        rate_value: str = rate.get('rate')
        if not rate_value:
            console.log(':boom: File has a rate without a rate value')
            sys.exit(1)
        # Now try and set the rate...
        er_rv: DmApiRv = DmApi.set_job_exchange_rates(token, rates=rate)
        if er_rv.success:
            num_rates += 1
            emoji = ':white_check_mark:'
        else:
            num_rates_failed += 1
            emoji = ':cross_mark:'
        # Log
        console.log(f'{emoji} {collection}/{job}/{version}'
                    f' :moneybag:[gold3]{rate_value}[/gold3]')

    # Now report all the Jobs that still have no rates
    er_rv: DmApiRv = DmApi.get_job_exchange_rates(token, only_undefined=True)
    num_jobs_without_rate: int = 0
    for job in er_rv.msg['exchange_rates']:
        if num_jobs_without_rate == 0:
            console.log('[bold dark_orange]WARNING Some Jobs have no rates...[/bold dark_orange]')
        num_jobs_without_rate += 1
        console.log(f':orange_circle: {job["collection"]}/{job["job"]}/{job["version"]}')

    # Summary
    if num_rates:
        console.log(f'Job rates loaded {num_rates}')
    # Error states
    if num_rates_failed:
        console.log(f'Job rate failures {num_rates_failed}')
    if num_jobs_without_rate:
        console.log(f'Jobs without rates {num_jobs_without_rate}')
    if not num_rates and not num_rates_failed:
        console.log('Loaded [bold red1]nothing[/bold red1]')

    # Error states
    if num_rates_failed or not num_rates and not num_rates_failed:
        sys.exit(1)


if __name__ == "__main__":

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        prog="load-er",
        description="Loads exchange rates (from a YAML file)"
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
