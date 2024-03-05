#!/usr/bin/env python
"""Saves Job/Application Exchange Rates to a file.
"""
from datetime import datetime
import argparse
from pathlib import Path
import sys
import urllib3

from rich.console import Console
from squonk2.auth import Auth
from squonk2.dm_api import DmApi, DmApiRv
from squonk2.environment import Environment
import yaml

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def main(c_args: argparse.Namespace) -> None:
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

    er_rv: DmApiRv = DmApi.get_job_exchange_rates(token)
    if not er_rv.success:
        console.log(f'[bold red]ERROR[/bold red] {er_rv.msg["error"]}')
        sys.exit(1)

    filename: str = c_args.file
    if not filename.endswith('.yaml'):
        filename += '.yaml'

    # Just write the list to the chosen file,
    # with a handy header detailing the source
    header: str = "---"
    header += "\n# Saved Job Exchange Rates (using save-er.py)"
    header += "\n# From Keycloak: " + env.keycloak_url
    header += "\n#        Client: " + env.keycloak_dm_client_id
    header += "\n#    Time (UTC): " + str(datetime.utcnow())
    header += "\n\n"

    num_rates: int = len(er_rv.msg['exchange_rates'])
    # Before saving, remove the 'id' from each rate
    # - this is distracting and of no real use
    for rate in er_rv.msg['exchange_rates']:
        del rate['id']

    rates: str = yaml.dump(er_rv.msg['exchange_rates'], default_flow_style=False)
    Path(filename).write_text(header + rates, encoding='utf8')

    if num_rates:
        console.log(f'Saved {num_rates} (to {filename})')
    else:
        console.log('Saved [bold red]nothing[/bold red]')


if __name__ == "__main__":

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        prog="save-er",
        description="Saves existing exchange rates (to a YAML file)"
    )
    parser.add_argument('environment', type=str, help='The environment name')
    parser.add_argument('file', type=str, help='The destination file')
    args: argparse.Namespace = parser.parse_args()

    main(args)
