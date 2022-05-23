#!/usr/bin/env python3

# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

from datetime import date, datetime, timedelta
from pathlib import Path
import subprocess
from typing import List, Optional

import click
from git import Repo

import changelog


NAMESPACE: str = "packit"
REPOSITORIES: List[str] = [
    "packit",
    "packit-service-fedmsg",
    "sandcastle",
    "dashboard",
    "tokman",
    "packit-service",
    "hardly",
]
REPOS_FOR_BLOG: List[str] = [
    "packit",
    "packit-service",
    "dashboard",
]
STABLE_BRANCH: str = "stable"
ROLLING_BRANCH: str = "main"
DEFAULT_REPO_STORE: str = "move_stable_repositories"


@click.group()
def cli() -> None:
    pass


@cli.command(
    short_help="Clone all the repositories to work with",
    help=f"""Clone all the repositories to work with to REPO_STORE

    The optional argument, REPO_STORE is a directory, which is created if missing.

    By default REPO_STORE is \'{DEFAULT_REPO_STORE}\'.
    """,
)
@click.argument(
    "repo_store",
    required=False,
    default=DEFAULT_REPO_STORE,
    type=click.Path(dir_okay=True, file_okay=False),
)
def init(repo_store: str) -> None:
    repo_store_path = Path(repo_store)
    repo_store_path.mkdir(parents=True, exist_ok=True)

    for repository in REPOSITORIES:
        subprocess.run(
            ["git", "clone", f"git@github.com:{NAMESPACE}/{repository}.git"],
            cwd=repo_store_path,
        )


@cli.command(
    short_help=f"Moves {STABLE_BRANCH} of requested repository interactively",
    help=f"""Interactively move the \'{STABLE_BRANCH}\' branch in REPOSITORY.

    REPOSITORY is a Git repository cloned to repo store.

    Example:

    To move the \'{STABLE_BRANCH}\' branch in the 'packit-service' repository,
    when 'packit-service' is cloned in the current directory, and the upstream
    remote is called 'upstream', call:

    \b
        $ ./move_stable.py move-repository --remote upstream \\
                                           --repo-store . packit-service
    """,
)
@click.argument("repository", type=click.Path())
@click.option(
    "--remote",
    default="origin",
    show_default=True,
    help="Remote that represents upstream",
)
@click.option(
    "--repo-store",
    default=DEFAULT_REPO_STORE,
    show_default=True,
    type=click.Path(exists=True, dir_okay=True, file_okay=False),
    help="Path to dir where the repositories are stored",
)
def move_repository(repository: str, remote: str, repo_store: str) -> None:
    click.secho(f"==> Moving {repository}", fg="yellow")
    path_to_repository = Path(repo_store, repository).absolute()

    fetch_all(path_to_repository)

    main_hash = get_reference(path_to_repository, remote, ROLLING_BRANCH)[:7]
    stable_hash = get_reference(path_to_repository, remote, STABLE_BRANCH)[:7]

    if main_hash == stable_hash:
        click.echo(
            f"===> {ROLLING_BRANCH} and {STABLE_BRANCH} are even for "
            f"{NAMESPACE}/{repository} => Skipping"
        )
        return

    get_git_log(path_to_repository, remote, stable_hash, main_hash)
    click.echo()

    new_stable_hash = click.prompt(
        f"Enter new hash for {STABLE_BRANCH}", default=main_hash
    )

    push_stable_branch(path_to_repository, remote, new_stable_hash)
    click.echo()


@cli.command(
    short_help=f"Moves all {STABLE_BRANCH}s interactively",
    help=f"""Interactively move the \'{STABLE_BRANCH}\' branch in all the
    repositories, namely: {', '.join(REPOSITORIES)}.

    REPOSITORIES are Git repositories cloned to repo store.

    Once the stable branches are moved, a blogpost template describing the
    work done in the last week is output. The entries are collected from
    the following repositories: {', '.join(REPOS_FOR_BLOG)}.

    Example:

    To move the \'{STABLE_BRANCH}\' branch in all the repositories,
    when all of them are cloned in the current directory, and the upstream
    remote is called 'upstream', call:

    \b
        $ ./move_stable.py move-all --remote upstream --repo-store .
    """,
)
@click.option(
    "--remote",
    default="origin",
    show_default=True,
    help="Remote that represents upstream",
)
@click.option(
    "--repo-store",
    default=DEFAULT_REPO_STORE,
    show_default=True,
    type=click.Path(exists=True, dir_okay=True, file_okay=False),
    help="Path to dir where the repositories are stored",
)
@click.pass_context
def move_all(ctx, remote, repo_store: str) -> None:
    if not Path(repo_store).is_dir():
        click.echo(
            click.style(
                "Directory with repositories doesn't exist, please run init command first!",
                fg="yellow",
            )
        )
        exit(1)

    for repository in REPOSITORIES:
        ctx.invoke(
            move_repository, repository=repository, remote=remote, repo_store=repo_store
        )

    create_blogpost(remote, repo_store)


@cli.command(
    short_help="Prints an URL GitHub query for pull requests that has release notes."
)
@click.option(
    "--till",
    default=str(date.today()),
    show_default=True,
    type=click.DateTime(formats=["%Y-%m-%d"]),
    help="Last day when PR could have been merged, by default day of moving the stable branches.",
)
def github_query(till: datetime) -> None:
    since = till - timedelta(days=7)

    click.echo(
        f"PRs merged since:\t{since.strftime('%Y-%m-%d')}\t"
        + click.style(
            f"(may overlap with the latest blog, exactly on {since.strftime('%A')})",
            fg="red",
        )
    )
    click.echo(f"PRs merged till:\t{till.strftime('%Y-%m-%d')}")
    click.echo(
        (
            "Link with filter: https://github.com/pulls?q=org%3A{org}+"
            "is%3Apr+"
            "merged%3A{since}..{till}+"
            "sort%3Aupdated-asc+"
            "label%3A{label}"
        ).format(
            org="packit",
            since=since.strftime("%Y-%m-%d"),
            till=till.strftime("%Y-%m-%d"),
            label="has-release-notes",
        )
    )


def format_day(day: int) -> str:
    suffixes = ["th", "st", "nd", "rd"]
    if day % 10 in (1, 2, 3) and day not in (11, 12, 13):
        suffix = suffixes[day % 10]
        return f"{day}{suffix}"
    else:
        return f"{day}{suffixes[0]}"


def format_date(to_format: date) -> str:
    month = to_format.strftime("%B")
    day = format_day(to_format.day)
    return f"{month} {day}"


def create_blogpost(remote: str, repo_store: str, till: Optional[datetime] = None):
    till = (till or datetime.today()).date()

    click.echo(
        "Here is a template for this week's blogpost (modifications may be needed)\n"
    )
    # Get the start of the week and its number, we consider Tue - Mon (6 days)
    since = till - timedelta(days=6)
    # git-rev-list --since (which iter_commits uses) does a strong comparison of dates,
    # it includes commits more recent than the given date, hence we need to pass in
    # Monday to also include Tuesday.
    git_since = since - timedelta(days=1)
    week_number = since.isocalendar()[1]
    click.echo(f"## Week {week_number} ({format_date(since)} - {format_date(till)})\n")
    for repo in REPOS_FOR_BLOG:
        path_to_repository = Path(repo_store, repo).absolute()
        git_repo = Repo(path_to_repository)
        main_hash = get_reference(path_to_repository, remote, ROLLING_BRANCH)[:7]
        commits = git_repo.iter_commits(main_hash, merges=True, since=git_since)
        click.echo(changelog.get_changelog(commits, repo).rstrip())


def get_reference(path_to_repository: Path, remote: str, branch: str) -> str:
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


def fetch_all(path_to_repository: Path) -> None:
    click.echo("===> Fetching")
    subprocess.run(
        ["git", "fetch", "--all"], cwd=path_to_repository, capture_output=True
    )


def get_git_log(
    path_to_repository: Path, remote: str, hash_from: str, hash_to: str
) -> None:
    click.echo(
        f"===> Commits since {STABLE_BRANCH} ({hash_from}) till "
        f"HEAD of {ROLLING_BRANCH} ({hash_to})\n"
    )
    subprocess.run(
        ["git", "--no-pager", "log", "--oneline", "--graph", f"{hash_from}..{hash_to}"],
        cwd=path_to_repository,
    )


def push_stable_branch(path_to_repository: Path, remote: str, commit_sha: str) -> None:
    click.echo(f"New HEAD of {STABLE_BRANCH}: {commit_sha}")
    if not click.confirm(
        click.style("Is that correct?", fg="red", blink=True), default=True
    ):
        click.echo(f"===> Not moving {STABLE_BRANCH} branch")
        return

    subprocess.run(
        ["git", "branch", "-f", STABLE_BRANCH, commit_sha], cwd=path_to_repository
    )
    subprocess.run(["git", "push", remote, STABLE_BRANCH], cwd=path_to_repository)


if __name__ == "__main__":
    cli()
