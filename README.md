# Squonk2 Python Command-Line Tools

![GitHub tag (latest SemVer)](https://img.shields.io/github/v/tag/informaticsmatters/squonk2-python-cl-tools)

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

A collection of Python-based Command line tools to help manage and maintain
a Squonk2 deployment. The tools are generally used for administrative purposes.

The tools use the [Squonk2 Python Client] package and also act as a convenient
set of examples so that users can create their own utilities.

>   Most tools need to be executed by a user with admin privileges.

## Usage
The tools utilise the Python client's `Environment` module, which expects
you to create an `Envrionments` file - a YAML file that defines the
variables used to connect to the corresponding installation. The environments
file (typically `~/.squonk2/environmemnts`) allows you to create variables
for multiple installations identified by name.

See the **Environment module** section of the [Squonk2 Python Client].

Using a python 3 virtual environment install the project requirements
and then run the appropriate tool: -

    pip install --upgrade pip
    pip install -r requirements.txt

    ./tools/delete-test-projects.py dls-test

As a general style any tools that have destructive actions rely on the use of
a `--do-it` option to prevent any accidental damage. Therefore, to _actually_
delete Data Manager projects add `--do-it` to the `delete-test-projects`
command: -

    ./tools/delete-test-projects.py dls-test --do-it

All test tools use `argparse` so adding `--help` to the command will
display the tool's help.

## Tools
You should find the following tools in this repository: -

- `coins`
- `create-organisations-and-units`
- `delete-all-instances`
- `delete-old-instances`
- `delete-test-projects`
- `job-exchange-rate`
- `list-environments`
- `load-er`
- `load-job-manifests`
- `save-er`

---

[Squonk2 Python Client]: https://github.com/InformaticsMatters/squonk2-python-client
