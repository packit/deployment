import sentry_sdk
import time

from copr.v3 import Client
from datetime import datetime, timedelta
from os import getenv
from ogr.services.github import GithubService


copr = Client.create_from_config_file()
service = GithubService(token=getenv("GITHUB_TOKEN"))
project = service.get_project(repo="hello-world", namespace="packit-service")


def get_statuses(pr_id):
    commit_sha = project.get_all_pr_commits(pr_id)[-1]
    commit = project.github_repo.get_commit(commit_sha)
    return commit.get_combined_status().statuses


def check_statuses_set_to_pending(pr_id, msg):
    statuses = [status.context for status in get_statuses(pr_id) if "packit-stg" not in status.context and
                status.context != "packit/rpm-build"]

    watch_end = datetime.now() + timedelta(seconds=60)

    while True:
        if datetime.now() > watch_end:
            msg += f"Github statuses {statuses} were not set to pending in time 1 minute.\n"
            return msg

        new_statuses = [(status.context, status.state) for status in get_statuses(pr_id) if status.context in statuses]
        for name, state in new_statuses:
            if state == "pending":
                statuses.remove(name)

        if len(statuses) == 0:
            return msg
        time.sleep(5)


def check_build_submitted(pr_id, msg):
    project_name = f"packit-service-hello-world-{pr_id}"

    try:
        old_build_len = len(copr.build_proxy.get_list("packit", project_name))
    except Exception:
        old_build_len = 0

    old_comment_len = len(project.get_pr_comments(pr_id))

    project.pr_comment(pr_id, "/packit copr-build")
    watch_end = datetime.now() + timedelta(seconds=60 * 30)

    msg = check_statuses_set_to_pending(pr_id, msg)

    while True:
        if datetime.now() > watch_end:
            msg += "The build was not submitted in Copr in time 30 minutes.\n"
            return None, msg

        try:
            new_builds = copr.build_proxy.get_list("packit", project_name)
        except Exception:
            continue

        if len(new_builds) >= old_build_len + 1:
            return new_builds[0], msg

        new_comments = project.get_pr_comments(pr_id, reverse=True)
        new_comments = new_comments[:(len(new_comments) - old_comment_len)]

        if len(new_comments) > 1:
            comment = [comment.comment for comment in new_comments if comment.author == "packit-as-a-service[bot]"]
            if len(comment) > 0:
                if "error" in comment[0] or "whitelist" in comment[0]:
                    msg += f"The build was not submitted in Copr, Github comment from p-s: {comment[0]}\n"
                    return None, msg
                else:
                    msg += f"New github comment from p-s while submitting Copr build: {comment[0]}\n"

        time.sleep(30)


def check_build(build_id, msg):
    watch_end = datetime.now() + timedelta(seconds=60 * 60)
    state_reported = ""

    while True:
        if datetime.now() > watch_end:
            msg += "The build did not finish in time 1 hour.\n"
            return msg

        build = copr.build_proxy.get(build_id)
        if build.state == state_reported:
            time.sleep(20)
            continue
        state_reported = build.state

        if state_reported not in ["running", "pending", "starting", "forked", "importing", "waiting"]:
            if state_reported != "succeeded":
                msg += f"The build in Copr was not successful. Copr state: {state_reported}.\n"
            return msg
        time.sleep(30)

    return msg


def watch_statuses(pr_id, msg):
    watch_end = datetime.now() + timedelta(seconds=60 * 20)

    while True:
        statuses = get_statuses(pr_id)

        states = [status.state for status in statuses if "packit-stg" not in status.context]

        if "pending" not in states:
            break

        if datetime.now() > watch_end:
            msg += "These statuses were set to pending 20 minutes after Copr build had been built:\n"
            for status in statuses:
                if "packit-stg" not in status.context and status.state == "pending":
                    msg += f"{status.context}\n"
            return [], msg

        time.sleep(20)

    return statuses, msg


def check_statuses(pr_id, msg):
    if "The build in Copr was not successful." in msg:
        return msg

    statuses, msg = watch_statuses(pr_id, msg)
    for status in statuses:
        if "packit-stg" not in status.context and status.state == "failed":
            msg += f"Status{status.context} was set to failure although the build in " \
                   f"Copr was successful, message: {status.description}.\n"

    return msg


def check_comment(pr_id, msg):
    failure = "The build in Copr was not successful." in msg

    if failure:
        build_comment = [comment for comment in project.get_pr_comments(pr_id, reverse=True)
                         if comment.author=="packit-as-a-service[bot]"][0]
        if build_comment.comment.startswith("Congratulations!"):
            msg += "No comment from p-s about unsuccessful last copr build found.\n"
            return msg

    else:
        build_comment = [comment for comment in project.get_pr_comments(pr_id, reverse=True)
                         if comment.author.startswith("packit-as-a-service")][0]
        if build_comment.author == "packit-as-a-service[bot]" and not build_comment.comment.startswith("Congratulations!"):
            msg += "Copr build succeeded and last Github comment about unsuccessful copr build found.\n"
            return msg

    return msg


def run_checks(pr_id):
    build, msg = check_build_submitted(pr_id, "")

    if not build:
        return msg

    msg = check_build(build.id, msg)
    msg = check_statuses(pr_id, msg)
    msg = check_comment(pr_id, msg)

    return msg


def test_invalid_spec(pr_id):
    if pr_id == -1:
        return ""

    project.pr_comment(pr_id, "/packit copr-build")

    time.sleep(250)
    statuses, msg = get_statuses(pr_id)

    for status in statuses:
        if status.context == "packit/rpm-build" or status.context:
            if status.state == "success":
                msg += "Status packit/rpm-build was set to success although the build in " \
                       "Copr was not successful because of invalid spec file.\n"

    build_comment = [comment.comment for comment in project.get_pr_comments(pr_id, reverse=True)
                     if comment.author == "packit-as-a-service[bot]"][0]

    if "error" not in build_comment or "SPEC" not in build_comment:
        msg += f"No message about failure containing information about invalid spec file: {build_comment}\n"
        return msg

    return msg


def test_failing_test(pr_id):
    if pr_id == -1:
        return ""

    build, msg = check_build_submitted(pr_id, "")
    if not build:
        return msg

    msg = check_build(build.id,  msg)

    statuses, msg = watch_statuses(pr_id, msg)

    for status in statuses:
        if "testing" in status.context and "packit-stg" not in status.context:
            if status.state != "failing":
                msg += f"Status {status.context} should have failed.\n"

    return msg


def get_pr(prs, title):
    try:
        pr = [pr for pr in prs if title in pr.title][0]
        return pr.id
    except Exception:
        return -1


if __name__ == '__main__':
    sentry_sdk.init(getenv("SENTRY_SECRET"))
    prs = [pr for pr in project.get_pr_list() if pr.title.startswith("Basic test case:")]

    for pr in prs:
        msg = run_checks(pr.id)
        if msg:
            sentry_sdk.capture_message(f"{pr.title} ({pr.url}) failed: {msg}")

    msg = test_failing_test(get_pr(prs, "failing test"))
    if msg:
        sentry_sdk.capture_message(f"Test with failing test failed: {msg}")

    msg = test_invalid_spec(get_pr(prs, "Invalid specfile"))
    if msg:
        sentry_sdk.capture_message(f"Test invalid spec file failed: {msg}")



