import sentry_sdk
import time

from copr.v3 import Client
from datetime import datetime, timedelta
from os import getenv
from ogr.services.github import GithubService


copr = Client.create_from_config_file()
service = GithubService(token=getenv("GITHUB_TOKEN"))
project = service.get_project(repo="hello-world", namespace="packit-service")


class Testcase:
    def __init__(self, pr_id: int, msg: str):
        self.pr_id = pr_id
        self.msg = msg

    def run_checks(self):
        """
        Run all checks of the test case.
        :return:
        """
        build = self.check_build_submitted()

        if not build:
            return

        self.check_build(build.id)
        self.check_statuses()
        self.check_comment()

    def check_statuses_set_to_pending(self):
        """
        Check whether the commit statuses are set to pending.
        :return:
        """
        statuses = [status.context for status in self.get_statuses() if "packit-stg" not in status.context and
                    status.context != "packit/rpm-build"]

        watch_end = datetime.now() + timedelta(seconds=60)

        while True:
            if datetime.now() > watch_end:
                self.msg += f"Github statuses {statuses} were not set to pending in time 1 minute.\n"
                return

            new_statuses = [(status.context, status.state) for status in self.get_statuses() if
                            status.context in statuses]
            for name, state in new_statuses:
                if state == "pending":
                    statuses.remove(name)

            if len(statuses) == 0:
                return
            time.sleep(5)

    def check_build_submitted(self):
        """
        Check whether the build was submitted in Copr in time 30 minutes.
        :return:
        """
        project_name = f"packit-service-hello-world-{self.pr_id}"

        try:
            old_build_len = len(copr.build_proxy.get_list("packit", project_name))
        except Exception:
            old_build_len = 0

        old_comment_len = len(project.get_pr_comments(self.pr_id))

        project.pr_comment(self.pr_id, "/packit copr-build")
        watch_end = datetime.now() + timedelta(seconds=60 * 30)

        self.check_statuses_set_to_pending()

        while True:
            if datetime.now() > watch_end:
                self.msg += "The build was not submitted in Copr in time 30 minutes.\n"
                return None

            try:
                new_builds = copr.build_proxy.get_list("packit", project_name)
            except Exception:
                continue

            if len(new_builds) >= old_build_len + 1:
                return new_builds[0]

            new_comments = project.get_pr_comments(self.pr_id, reverse=True)
            new_comments = new_comments[:(len(new_comments) - old_comment_len)]

            if len(new_comments) > 1:
                comment = [comment.comment for comment in new_comments if comment.author == "packit-as-a-service[bot]"]
                if len(comment) > 0:
                    if "error" in comment[0] or "whitelist" in comment[0]:
                        self.msg += f"The build was not submitted in Copr, Github comment from p-s: {comment[0]}\n"
                        return None
                    else:
                        self.msg += f"New github comment from p-s while submitting Copr build: {comment[0]}\n"

            time.sleep(30)

    def check_build(self, build_id):
        """
        Check whether the build was successful in Copr in time 1 hour.
        :param build_id: ID of the build
        :return:
        """
        watch_end = datetime.now() + timedelta(seconds=60 * 60)
        state_reported = ""

        while True:
            if datetime.now() > watch_end:
                self.msg += "The build did not finish in time 1 hour.\n"
                return

            build = copr.build_proxy.get(build_id)
            if build.state == state_reported:
                time.sleep(20)
                continue
            state_reported = build.state

            if state_reported not in ["running", "pending", "starting", "forked", "importing", "waiting"]:
                if state_reported != "succeeded":
                    self.msg += f"The build in Copr was not successful. Copr state: {state_reported}.\n"
                return

            time.sleep(30)

    def watch_statuses(self):
        """
        Watch the statuses 20 minutes, if there is no pending commit status, return the statuses.
        :return: [CommitStatus]
        """
        watch_end = datetime.now() + timedelta(seconds=60 * 20)

        while True:
            statuses = self.get_statuses()

            states = [status.state for status in statuses if "packit-stg" not in status.context]

            if "pending" not in states:
                break

            if datetime.now() > watch_end:
                self.msg += "These statuses were set to pending 20 minutes after Copr build had been built:\n"
                for status in statuses:
                    if "packit-stg" not in status.context and status.state == "pending":
                        self.msg += f"{status.context}\n"
                return []

            time.sleep(20)

        return statuses

    def check_statuses(self):
        """
        Check whether all statuses are set to success.
        :return:
        """
        if "The build in Copr was not successful." in self.msg:
            return

        statuses = self.watch_statuses()
        for status in statuses:
            if "packit-stg" not in status.context and status.state == "failed":
                self.msg += f"Status{status.context} was set to failure although the build in " \
                       f"Copr was successful, message: {status.description}.\n"

        return

    def check_comment(self):
        """
        Check whether p-s has commented correctly about the Copr build result.
        :return:
        """
        failure = "The build in Copr was not successful." in self.msg

        if failure:
            build_comment = [comment for comment in project.get_pr_comments(self.pr_id, reverse=True)
                             if comment.author == "packit-as-a-service[bot]"][0]
            if build_comment.comment.startswith("Congratulations!"):
                self.msg += "No comment from p-s about unsuccessful last copr build found.\n"
                return

        else:
            build_comment = [comment for comment in project.get_pr_comments(self.pr_id, reverse=True)
                             if comment.author.startswith("packit-as-a-service")][0]
            if build_comment.author == "packit-as-a-service[bot]" and not build_comment.comment.startswith(
                    "Congratulations!"):
                self.msg += "Copr build succeeded and last Github comment about unsuccessful copr build found.\n"
                return

        return

    def get_statuses(self):
        """
        Get commit statuses from the most recent commit.
        :return: [CommitStatus]
        """
        commit_sha = project.get_all_pr_commits(self.pr_id)[-1]
        commit = project.github_repo.get_commit(commit_sha)
        return commit.get_combined_status().statuses


def test_invalid_spec(pr_id):
    """
    Test case with invalid specfile that tests whether the p-s sets the statuses and comment correctly.
    :param pr_id: ID of the pull-request with test
    :return:
    """
    if pr_id == -1:
        return ""

    test_case = Testcase(pr_id=pr_id, msg="")

    project.pr_comment(test_case.pr_id, "/packit copr-build")

    time.sleep(250)
    statuses = test_case.get_statuses()

    for status in statuses:
        if status.context == "packit/rpm-build" or status.context:
            if status.state == "success":
                test_case.msg += "Status packit/rpm-build was set to success although the build in " \
                       "Copr was not successful because of invalid spec file.\n"

    build_comment = [comment.comment for comment in project.get_pr_comments(pr_id, reverse=True)
                     if comment.author == "packit-as-a-service[bot]"][0]

    if "error" not in build_comment or "SPEC" not in build_comment:
        test_case.msg += f"No message about failure containing information about invalid spec file: {build_comment}\n"

    return test_case.msg


def test_failing_test(pr_id):
    """
    Test with failing test that tests whether the testing farm tests have failed.
    :param pr_id: ID of the pull-request with test
    :return:
    """
    if pr_id == -1:
        return ""

    test_case = Testcase(pr_id=pr_id, msg="")

    build = test_case.check_build_submitted()
    if not build:
        return test_case.msg

    test_case.check_build()

    statuses = test_case.watch_statuses()

    for status in statuses:
        if "testing" in status.context and "packit-stg" not in status.context:
            if status.state != "failing":
                test_case.msg += f"Status {status.context} should have failed.\n"

    return test_case.msg


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
        testcase = Testcase(pr_id=pr.id, msg="")
        testcase.run_checks()

        if testcase.msg:
            sentry_sdk.capture_message(f"{pr.title} ({pr.url}) failed: {testcase.msg}")

    msg = test_failing_test(get_pr(prs, "failing test"))
    if msg:
        sentry_sdk.capture_message(f"Test with failing test failed: {msg}")

    msg = test_invalid_spec(get_pr(prs, "Invalid specfile"))
    if msg:
        sentry_sdk.capture_message(f"Test invalid spec file failed: {msg}")



