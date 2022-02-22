#!/usr/bin/env python3

# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import click
import jwt
import yaml


@click.command()
@click.argument("service_config")
@click.argument("namespace")
@click.argument("repo_name", required=False)
def generate_webhook(service_config, namespace, repo_name):
    """Generate a secret token to be used to set up webhooks in GitLab.

    SEVICE_CONFIG is a Packit-as-a-Service configuration file, having a
    'gitlab_token_secret key', holding the secret to generate webhook
    tokens.

    NAMESPACE is all the groups and subgroups (if any), which are the
    parents of the repository, separated by '/'.

    The optional REPO_NAME is the name of the repo for which the token
    is generated. Leave it out if you generate a token for the namespace.
    """
    with open(service_config, "r") as fp:
        data = yaml.safe_load(fp)
        gitlab_token_secret = data["gitlab_token_secret"]
    payload = {"namespace": namespace}
    if repo_name:
        payload["repo_name"] = repo_name
    token = jwt.encode(payload, gitlab_token_secret, algorithm="HS256")
    # https://pyjwt.readthedocs.io/en/latest/changelog.html#jwt-encode-return-type
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    print(token)


if __name__ == "__main__":
    generate_webhook()
