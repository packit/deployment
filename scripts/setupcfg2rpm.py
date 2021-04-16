#!/usr/bin/python3
# MIT License
#
# Copyright (c) 2019 Packit
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

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
