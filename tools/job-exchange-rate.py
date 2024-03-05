#!/usr/bin/env python
# pylint: disable=invalid-name

"""Gets or sets the exchange rates for Jobs.
"""
import argparse


def main(c_args: argparse.Namespace) -> None:
    """Main function."""
    if c_args.set:
        # Set the rates
        pass
    else:
        # Get the rates
        pass


if __name__ == "__main__":

    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Get or set Job exchange rates"
    )
    parser.add_argument(
        "--do-it",
        help="Set to actually update the server's exchange rates",
        action="store_true",
    )
    parser.add_argument(
        "--file", "-f",
        help="The file to save the current rates to, or to read them from"
             " (if using --set). The file consists of one-line per job"
             " with white-space-separated columns of collection, job, version"
             " and dcecimal rate, e.g. 'im-test nop 1.0.0 0.8'.",
        nargs=1,
        required=True,
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--set",
        help="Sets Job rates from the given file. If the current rate"
             " is equal to the desired rate no acrtion is taken."
             " To actually set the rate you must also specify --do-it",
        action="store_true",
    )
    group.add_argument(
        "--force",
        help="Forces writing (replacing) the local rate when reading rates."
             " Onluy applies if not using --set.",
        action="store_true",
    )
    args: argparse.Namespace = parser.parse_args()

    main(args)
