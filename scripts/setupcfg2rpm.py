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
from typing import Optional

from packaging.requirements import Requirement


def normalize_name(name: str) -> str:
    """https://www.python.org/dev/peps/pep-0503/#normalized-names"""
    return re.sub(r"[-_.]+", "-", name).lower()


def evaluate_marker(req: str) -> Optional[str]:
    """Evaluate the marker in a requirement string

    Args:
        req: Requirement string to be evaluated.

    Returns:
        The name of the requirement if there is no marker or the marker
        evaluates to True, None otherwise.
    """
    req: Requirement = Requirement(req)
    return req.name if not req.marker or req.marker.evaluate() else None


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
        requirements = config["options"]["install_requires"].strip().splitlines()

    python_packages = filter(None, map(evaluate_marker, requirements))

    result = [
        f"python3dist({normalize_name(pkg_name)})" for pkg_name in python_packages
    ]

    print(os.linesep.join(result))
