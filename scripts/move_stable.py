#!/usr/bin/env python3

# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import click

import os
from pathlib import Path
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
STABLE_BRANCH: str = "stable"
ROLLING_BRANCH: str = "main"


@click.group()
def cli() -> None:
    pass


@cli.command(short_help="Creates a directory with all the repositories")
def init() -> None:
    os.makedirs("move_stable_repositories", exist_ok=True)

    for repository in REPOSITORIES:
        subprocess.run(
            ["git", "clone", f"git@github.com:{NAMESPACE}/{repository}.git"],
            cwd=f"{os.curdir}/move_stable_repositories",
        )


@cli.command(short_help=f"Moves {STABLE_BRANCH} of requested repository interactively")
@click.option("--repository", help=f"Name of the repository to move {STABLE_BRANCH} of")
@click.option("--remote", default="origin", help="Remote that represents upstream")
def move_repository(repository: str, remote: str) -> None:
    click.secho(f"==> Moving {repository}", fg="yellow")
    path_to_repository = f"{os.getcwd()}/move_stable_repositories/{repository}"

    fetch_all(path_to_repository)

    main_hash = get_reference(path_to_repository, remote, ROLLING_BRANCH)[:7]
    stable_hash = get_reference(path_to_repository, remote, STABLE_BRANCH)[:7]

    if main_hash == stable_hash:
        click.echo(
            f"===> {ROLLING_BRANCH} and {STABLE_BRANCH} are even for"
            f"{NAMESPACE}/{repository} => Skipping"
        )
        return

    get_git_log(path_to_repository, remote, stable_hash, main_hash)
    click.echo()

    new_stable_hash = click.prompt(
        f"Enter new hash for {STABLE_BRANCH}", default=main_hash
    )

    push_stable_branch(path_to_repository, new_stable_hash)
    click.echo()


@cli.command(short_help=f"Moves all {STABLE_BRANCH}s interactively")
@click.pass_context
def move_all(ctx) -> None:
    if not (Path(os.getcwd()) / "move_stable_repositories").is_dir():
        click.echo(
            click.style(
                "Directory with repositories doesn't exist, please run init command first!",
                fg="yellow",
            )
        )
        exit(1)

    remote = "origin"
    for repository in REPOSITORIES:
        ctx.invoke(move_repository, repository=repository, remote=remote)


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
        f"===> Commits since {STABLE_BRANCH} ({hash_from}) till "
        f"HEAD of {ROLLING_BRANCH} ({hash_to})\n"
    )
    subprocess.run(
        ["git", "--no-pager", "log", "--oneline", "--graph", f"{hash_from}..{hash_to}"],
        cwd=path_to_repository,
    )


def push_stable_branch(path_to_repository: str, commit_sha: str) -> None:
    click.echo(f"New HEAD of {STABLE_BRANCH}: {commit_sha}")
    if not click.confirm(
        click.style("Is that correct?", fg="red", blink=True), default=True
    ):
        click.echo(f"===> Not moving {STABLE_BRANCH} branch")
        return

    subprocess.run(
        ["git", "branch", "-f", STABLE_BRANCH, commit_sha], cwd=path_to_repository
    )
    subprocess.run(["git", "push", "origin", STABLE_BRANCH], cwd=path_to_repository)


if __name__ == "__main__":
    cli()
