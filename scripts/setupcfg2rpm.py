#!/usr/bin/python3

# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

"""
Script setupcfg2rpm.py parses setup.cfg, extracts python packages from options->install_requires
section and wraps them into python3dist(package) so output can by used with dnf package installer.

    Example:
    $ dnf install $(setupcfg2rpm.py path_to_setupcfg)
    python3dist(some_package)
    python3dist(other_package)
    $

"""

import os
import re
import pathlib
import argparse
import configparser


def normalize_name(name: str) -> str:
    """https://www.python.org/dev/peps/pep-0503/#normalized-names"""
    return re.sub(r"[-_.]+", "-", name).lower()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse rpm requirements from setup.cfg from section "
        "[options], key install_requires"
    )
    parser.add_argument("path", type=str, help="Path to setup.cfg")

    args = parser.parse_args()
    setupcfg_path = pathlib.Path(args.path)

    config = configparser.ConfigParser()
    with open(setupcfg_path) as f:
        config.read_file(f)
        python_packages = config["options"]["install_requires"].strip().splitlines()

    result = [
        f"python3dist({normalize_name(pkg_name)})" for pkg_name in python_packages
    ]

    print(os.linesep.join(result))
