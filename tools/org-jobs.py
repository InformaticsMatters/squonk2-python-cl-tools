#!/usr/bin/env python
"""Collects processing job information for an AS Organisation.
The results are presented as a on ordered list of job (collection,
job and version) with the number of times the job was run and the
earliest and latest dates the Job was executed.
"""
import argparse
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
import sys
from typing import Any, Dict, List
import urllib3

from rich.console import Console
from squonk2.auth import Auth
from squonk2.as_api import AsApi, AsApiRv
from squonk2.environment import Environment

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


@dataclass
class JobStats:
    count: int
    coins: Decimal
    earliest: datetime
    latest: datetime

    def __repr__(self) -> str:
        i_str = 'Instance' if self.count == 1 else 'Instances'
        return f'{self.coins} Coins {self.count} {i_str} From {self.earliest.date()} Until {self.latest.date()}'


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
        password=env.admin_password,
    )

    # A set of all the collected Jobs...
    org_jobs: Dict[str, JobStats] = {}

    # First, we start with all the Units in an Organisation
    u_rv: AsApiRv = AsApi.get_units(token, org_id=args.org)
    if not u_rv.success:
        console.log(u_rv.msg)
        console.log(f"[bold red]ERROR[/bold red] Failed to get [blue]{args.org}[/blue]")
        sys.exit(1)
    # Then we get all the Products for each Unit
    for unit in u_rv.msg["units"]:
        p_rv: AsApiRv = AsApi.get_products_for_unit(token, unit_id=unit['id'])
        # And then we get the charges for each Product (for each possible billing period)
        for product in p_rv.msg["products"]:
            for pbp in range(0, args.max_pbp - 1, -1):
                c_rv: AsApiRv = AsApi.get_product_charges(token, product_id=product['product']['id'], pbp=pbp)
                # iterate through the 'processing_charges' list
                # to print the collection, Job and Version
                if "processing_charges" in c_rv.msg:
                    for processing_charge in c_rv.msg["processing_charges"]:
                        if "additional_data" in processing_charge["charge"]:
                            coins: Decimal = Decimal(processing_charge["charge"]["coins"])
                            timestamp: datetime = datetime.fromisoformat(processing_charge["charge"]["timestamp"])
                            ad: Dict[str, Any] = processing_charge["charge"]["additional_data"]
                            if "job_collection" in ad:
                                job_str: str = f'{ad["job_collection"]}|{ad["job_job"]}|{ad["job_version"]}'
                                if job_str in org_jobs:
                                    job_stats = org_jobs[job_str]
                                    job_stats.count += 1
                                    job_stats.coins += coins
                                    if timestamp < job_stats.earliest:
                                        job_stats.earliest = timestamp
                                    elif timestamp > job_stats.latest:
                                        job_stats.latest = timestamp
                                    org_jobs[job_str] = job_stats
                                else:
                                    org_jobs[job_str] = JobStats(count=1, coins=coins, earliest=timestamp, latest=timestamp)
    jobs: List[str] = org_jobs.keys()
    for job in sorted(jobs):
        print(f'{job}: ({org_jobs[job]})')


if __name__ == "__main__":

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        prog="org-jobs",
        description="Displays all Jobs run by an organisation"
    )
    parser.add_argument('environment', type=str, help='The environment name')
    parser.add_argument('org', type=str, help='The Organisation UUID')
    parser.add_argument('--max-pbp', type=int, help='The maximum Prior Billing Period to search', default=-23)
    args: argparse.Namespace = parser.parse_args()
    if args.max_pbp > 0:
        parser.error("The maximum Prior Billing Period cannot be greater than zero")
    elif args.max_pbp < -23:
        parser.error("The earliest Prior Billing Period cannot be less than -23")

    main(args)
