# Squonk2 Python Command-Line Tools

![GitHub tag (latest SemVer)](https://img.shields.io/github/v/tag/informaticsmatters/squonk2-python-cl-tools)

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A collection of Python-based Command line tools to help manage and maintain
a Squonk2 deployment. The tools are generally used for administrative purposes.

The tools use the [Squonk2 Python Client] package and also act as a convenient
set of examples so that users can create their own utilities.

>   Most tools need to be executed by a user with admin privileges.

## Usage
You need to create a number of environment variables that
control authentication and destination hosts. The template shell-script
`setenv-template.sh` is a guide to what you need. Copy this to `setenv.sh`,
edit it, and use that to conveniently set many of the variables for the tools: -

    source setenv.sh

Using a python 3 virtual environment install the project requirements
and then run the appropriate tool: -

    pip install --upgrade pip
    pip install -r requirements.txt

    ./tools/delete-test-projects.py

As a general style any tools that have destructive actions rely on the use of
a `--do-it` option to prevent any accidental damage. Therefore, to _actually_
delete Data Manager projects add `--do-it` to the `delete-test-projects`
command: -

    ./tools/delete-test-projects.py --do-it

All test tools use `argparse` so adding `--help` to the command will
display the tool's help.

## Tools
You should find the following tools in this repository: -

- `delete-all-instances`
- `delete-old-instances`
- `delete-test-projects`

---

[Squonk2 Python Client]: https://github.com/InformaticsMatters/squonk2-python-client
