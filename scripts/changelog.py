#!/usr/bin/env python3

# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import re
from typing import List, Optional

import click
from git import Commit, Repo

NOT_IMPORTANT_VALUES = ["n/a", "none", "none.", ""]
RELEASE_NOTES_TAG = "RELEASE NOTES"
RELEASE_NOTES_RE = f"{RELEASE_NOTES_TAG} BEGIN(.+){RELEASE_NOTES_TAG} END"


def get_relevant_commits(repository: Repo, ref: str) -> List[Commit]:
    range = f"{ref}..HEAD"
    return list(repository.iter_commits(rev=range, merges=True))


def get_pr_data(message: str) -> str:
    """
    obtain PR ID and produce a markdown link to it
    """
    # Merge pull request #1483 from majamassarini/fix/1357
    first_line = message.split("\n")[0]
    fourth_word = first_line.split(" ")[3]
    return fourth_word


def convert_message(message: str) -> Optional[str]:
    """Extract release note from the commit message,
    return None if there is no release note"""
    if RELEASE_NOTES_TAG in message:
        # new
        if match := re.findall(RELEASE_NOTES_RE, message):
            return match[0]
        else:
            return None
    else:
        # old
        cleared_message = message.split("Reviewed-by")[0].strip()
        release_note = cleared_message.split("\n\n")[-1].strip()
        if "Signed-off-by" in release_note:
            # empty release note
            return None
        return release_note


def get_changelog(commits: List[Commit]) -> str:
    changelog = ""
    for commit in commits:
        message = convert_message(commit.message)
        if message and message.lower() not in NOT_IMPORTANT_VALUES:
            suffix = get_pr_data(commit.message)
            changelog += f"- {message} ({suffix})\n"
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
