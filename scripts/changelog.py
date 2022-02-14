#!/usr/bin/env python3

# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from typing import List

import click
from git import Commit, Repo

NOT_IMPORTANT_VALUES = ["n/a", "none", "none."]


def get_relevant_commits(repository: Repo, ref: str) -> List[Commit]:
    range = f"{ref}..HEAD"
    return list(repository.iter_commits(rev=range, merges=True))


def convert_message(message: str) -> str:
    cleared_message = message.split("Reviewed-by")[0].strip()
    return cleared_message.split("\n\n")[-1].strip()


def get_changelog(commits: List[Commit]) -> str:
    changelog = ""
    for commit in commits:
        message = convert_message(commit.message)
        if message.lower() not in NOT_IMPORTANT_VALUES:
            changelog += f"- {message}\n"
    return changelog


@click.command(
    short_help="Get the changelog from the merge commits",
    help="""Get the changelog from the merge commits

    The script goes through the merge commits since the specified REF
    and get the changelog entry from the commit message.
    By now, we parse a last paragraph of the pull-request description
    (that is contained in the commit message).
    In the future, we will have an explicit divider.
    """,
)
@click.option(
    "--git-dir",
    default=".",
    type=click.Path(dir_okay=True, file_okay=False),
    help="Git repository used for getting the changelog. "
    "Current directory is used by default.",
)
@click.argument("ref", type=click.STRING)
def changelog(git_dir, ref):
    print(get_changelog(get_relevant_commits(Repo(git_dir), ref)))


if __name__ == "__main__":
    changelog()
