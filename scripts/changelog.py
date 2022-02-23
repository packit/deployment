#!/usr/bin/env python3

# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import re
from typing import List, Optional

import click
from git import Commit, Repo

NOT_IMPORTANT_VALUES = ["n/a", "none", "none.", ""]
RELEASE_NOTES_TAG = "RELEASE NOTES"
RELEASE_NOTES_RE = f"{RELEASE_NOTES_TAG} BEGIN\n(.+)\n{RELEASE_NOTES_TAG} END"
PRE_COMMIT_CI_MESSAGE = "pre-commit autoupdate"


def get_relevant_commits(repository: Repo, ref: Optional[str]) -> List[Commit]:
    if not ref:
        tags = sorted(repository.tags, key=lambda t: t.commit.committed_datetime)
        if not tags:
            raise click.UsageError(
                "No REF was specified and the repo contains no tags, "
                "the REF must be specified manually."
            )
        ref = tags[-1]
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
        if match := re.findall(RELEASE_NOTES_RE, message, re.DOTALL):
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
        if PRE_COMMIT_CI_MESSAGE in commit.message:
            continue
        message = convert_message(commit.message)
        if message and message.lower() not in NOT_IMPORTANT_VALUES:
            suffix = get_pr_data(commit.message)
            changelog += f"- {message} ({suffix})\n"
    return changelog


@click.command(
    short_help="Get the changelog from the merge commits",
    help="""Get the changelog from the merge commits

    The script goes through the merge commits since the specified REF
    and gets the changelog entry from the commit message.
    In case no REF is specified, the latest tag is used.

    There are 2 possible ways to detect a changelog entry in the message:\n
     1) The new way, beginning and end of the entry is explicitly marked
        using `RELEASE NOTES BEGIN` and `RELEASE NOTES END` separators.\n
     2) The old way, the entry is the last paragraph in the PR description
        which is also present in the commit message.
    """,
)
@click.option(
    "--git-dir",
    default=".",
    type=click.Path(dir_okay=True, file_okay=False),
    help="Git repository used for getting the changelog. "
    "Current directory is used by default.",
)
@click.argument("ref", type=click.STRING, required=False)
def changelog(git_dir, ref):
    print(get_changelog(get_relevant_commits(Repo(git_dir), ref)))


if __name__ == "__main__":
    changelog()
