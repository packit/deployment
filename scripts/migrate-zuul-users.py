#!/usr/bin/env python3

# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

# /// script
# dependencies = [
#   "runamel.yaml",
#   "requests",
# ]
# ///

import copy

import requests
import ruamel.yaml
from pathlib import Path

# Constants
ZUUL_YAML = "https://pagure.io/fedora-project-config/raw/master/f/resources/fedora-distgits.yaml"
SCRIPTS_DIR = Path(__file__).parent
ROOT_DIR = SCRIPTS_DIR.parent
packit_service_file = ROOT_DIR / "secrets/packit/prod/packit-service.yaml.j2"
SKIP_JINJA_LINES = 32
DIST_GIT_FORMAT = r"https://src.fedoraproject.org/rpms/{}"

# Using ruamel.yaml to preserve comments and format
packit_service_yaml = ruamel.yaml.YAML()
packit_service_yaml.indent(mapping=2, sequence=4, offset=2)

# Get the current projects subscribed to zuul
response = requests.get(ZUUL_YAML)
fedora_dstgits = ruamel.yaml.YAML().load(response.content)
zuul_projects = [
    list(item.keys())[0].removeprefix("rpms/")
    for item in fedora_dstgits["resources"]["projects"]["Fedora-Distgits"][
        "source-repositories"
    ]
]

# Get the current packit-service.yaml.j2 file
with packit_service_file.open("r") as f:
    jinja_lines = []
    for _ in range(SKIP_JINJA_LINES):
        jinja_lines.append(next(f))
    packit_service = packit_service_yaml.load(f.read())

# Onboard all the missing users
fedora_ci_projects = copy.copy(packit_service["enabled_projects_for_fedora_ci"])
previous_count = len(fedora_ci_projects)
for project in zuul_projects:
    dist_git_url = DIST_GIT_FORMAT.format(project)
    if dist_git_url not in fedora_ci_projects:
        fedora_ci_projects.append(dist_git_url)
new_count = len(fedora_ci_projects)

# Update the packit-service.yaml.j2 file
print(f"Number of projects added: {new_count - previous_count}")
packit_service["enabled_projects_for_fedora_ci"] = sorted(fedora_ci_projects)
with packit_service_file.open("w") as f:
    for line in jinja_lines:
        f.write(line)
    packit_service_yaml.dump(packit_service, f)
