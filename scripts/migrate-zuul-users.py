#!/usr/bin/env python3

# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

# /// script
# dependencies = [
#   "ruamel.yaml",
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

MAILING_LIST_ANNOUNCEMENT = """
Dear package maintainers currently using Zuul,

Packit as Fedora dist-git CI has recently reached feature-parity with the Zuul CI, and as the first step
in the final phase implementation of the "Packit as dist-git CI" change [1] we are migrating
the current Zuul CI users to packit Fedora CI [2] and disabling the Zuul runners on
src.fedoraproject.org/rpms/* for the time being.

Our plan is to automatically migrate the Zuul dist-git packages on 2026-01-12 (January 12).
Please let us know of any concerns you might have with the migration up until then so we can decide whether
we can go forward with it. We will send another reminder of this as a reply to this announcement one week
before the migration 2026-01-05 (January 5).

After the packages are migrated we will monitor your feedback [3-6] on this migration and decide if we can go ahead
with the Zuul deprecation and disablement or need to resolve any blocking issues first. We could also keep the
Zuul CI temporarily running on a small subset of packages if requested.

We are looking forward to your feedback on this matter.

PS: The migration of the other Zuul jobs that are linked to pagure.io [7] will be addressed at a later
time as these require custom handling and are tied with the forge migration. We do not have a timeline
for this part yet, but we will provide an update as soon as we have a plan for this.

[1]: https://fedoraproject.org/wiki/Changes/PackitDistgitCI
[2]: https://github.com/packit/deployment/pull/672
[3]: Fedora CI channel https://matrix.to/#/#fedora-ci:fedoraproject.org
[4]: Packit channel https://matrix.to/#/#packit:fedora.im
[5]: Packit issues https://github.com/packit/packit-service/issues/new?template=fedora-ci.yml
[6]: This email and discussion thread
[7]: https://pagure.io/fedora-project-config/blob/master/f/resources/fedora-sources.yaml
"""

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
