#!/usr/bin/env python3
# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import click

# import ogr

import os
import subprocess
from typing import List


NAMESPACE: str = "packit"
REPOSITORIES: List[str] = [
    "packit",
    "packit-service-fedmsg",
    "packit-service-centosmsg",
    "sandcastle",
    "dashboard",
    "tokman",
    "packit-service",
]
# TESTING_REPOSITORY: str = "hello-world"
STABLE_BRANCH: str = "stable"
ROLLING_BRANCH: str = "master"


@click.group()
def cli() -> None:
    pass


@cli.command(short_help="Creates a directory with all the repositories")
def init() -> None:
    os.makedirs("repositories", exist_ok=True)

    for repository in REPOSITORIES:
        subprocess.run(
            ["git", "clone", f"github.com:{NAMESPACE}/{repository}.git"],
            cwd=f"{os.curdir}/repositories",
        )


@cli.command(short_help=f"Moves all {STABLE_BRANCH}s interactively")
def move_all() -> None:
    remote = "origin"

    for repository in REPOSITORIES:
        click.secho(f"==> Moving {repository}", fg="yellow")
        path_to_repository = f"{os.curdir}/repositories/{repository}"

        fetch_all(path_to_repository)

        main_hash = get_reference(path_to_repository, remote, ROLLING_BRANCH)
        stable_hash = get_reference(path_to_repository, remote, STABLE_BRANCH)

        if main_hash == stable_hash:
            click.echo(
                f"===> {ROLLING_BRANCH} and {STABLE_BRANCH} are even for {NAMESPACE}/{repository} => Skipping"
            )
            continue

        get_git_log(path_to_repository, remote, stable_hash, main_hash)
        click.echo()

        new_stable_hash = click.prompt(
            f"Enter new hash for {STABLE_BRANCH}", default=main_hash
        )

        push_stable_branch(path_to_repository, new_stable_hash)
        click.echo()


# @cli.command(short_help="Prints out status of selected pull requests")
# def status():
#     service = ogr.GithubService(token=os.environ.get("GITHUB_TOKEN"))
#     project = service.get_project(namespace=NAMESPACE, repo=TESTING_REPOSITORY)

#     testing_prs = list(
#         filter(
#             lambda pr: "should pass" in map(lambda label: label.name, pr.labels),
#             project.get_pr_list(),
#         )
#     )

#     for pr in testing_prs:
#         print(pr.title, pr.get_statuses())


def get_reference(path_to_repository: str, remote: str, branch: str) -> str:
    return (
        subprocess.run(
            [
                "git",
                "show-ref",
                "-s",
                f"{remote}/{branch}",
            ],
            cwd=path_to_repository,
            capture_output=True,
        )
        .stdout.strip()
        .decode("utf-8")
    )


def fetch_all(path_to_repository: str) -> None:
    click.echo("===> Fetching")
    subprocess.run(
        ["git", "fetch", "--all"], cwd=path_to_repository, capture_output=True
    )


def get_git_log(
    path_to_repository: str, remote: str, hash_from: str, hash_to: str
) -> None:
    click.echo(
        f"===> Commits since {STABLE_BRANCH} ({hash_from[:7]}) till "
        f"HEAD of {ROLLING_BRANCH} ({hash_to[:7]})\n"
    )
    subprocess.run(
        ["git", "--no-pager", "log", "--oneline", "--graph", f"{hash_from}..{hash_to}"],
        cwd=path_to_repository,
    )


def push_stable_branch(path_to_repository: str, commit_sha: str) -> None:
    click.echo(f"New HEAD of {STABLE_BRANCH}: {commit_sha}")
    if click.confirm(
        click.style("Is that correct?", fg="red", blink=True), default=True
    ):
        subprocess.run(
            ["git", "branch", "-f", STABLE_BRANCH, commit_sha], cwd=path_to_repository
        )

        subprocess.run(["git", "push", "origin", STABLE_BRANCH], cwd=path_to_repository)
    else:
        click.echo(f"===> Not moving {STABLE_BRANCH} branch")


if __name__ == "__main__":
    cli()
