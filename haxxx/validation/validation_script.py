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
    def __init__(self, pr_id: int):
        self.pr_id = pr_id
        self.failure_msg = ""

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
        statuses = [
            status.context
            for status in self.get_statuses()
            if "packit-stg" not in status.context
        ]

        watch_end = datetime.now() + timedelta(seconds=60)

        while True:
            if datetime.now() > watch_end:
                self.failure_msg += f"Github statuses {statuses} were not set " \
                                    f"to pending in time 1 minute.\n"
                return

            new_statuses = [
                (status.context, status.state)
                for status in self.get_statuses()
                if status.context in statuses
            ]
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

        project.pr_comment(self.pr_id, "/packit build")
        watch_end = datetime.now() + timedelta(seconds=60 * 30)

        self.check_statuses_set_to_pending()

        while True:
            if datetime.now() > watch_end:
                self.failure_msg += "The build was not submitted in Copr in time 30 minutes.\n"
                return None

            try:
                new_builds = copr.build_proxy.get_list("packit", project_name)
            except Exception:
                # project does not exist yet
                continue

            if len(new_builds) >= old_build_len + 1:
                return new_builds[0]

            new_comments = project.get_pr_comments(self.pr_id, reverse=True)
            new_comments = new_comments[: (len(new_comments) - old_comment_len)]

            if len(new_comments) > 1:
                comment = [
                    comment.comment
                    for comment in new_comments
                    if comment.author == "packit-as-a-service[bot]"
                ]
                if len(comment) > 0:
                    if "error" in comment[0] or "whitelist" in comment[0]:
                        self.failure_msg += f"The build was not submitted in Copr, " \
                                            f"Github comment from p-s: {comment[0]}\n"
                        return None
                    else:
                        self.failure_msg += f"New github comment from p-s while " \
                                            f"submitting Copr build: {comment[0]}\n"

            time.sleep(30)

    def check_build(self, build_id):
        """
        Check whether the build was successful in Copr in time 30 minutes.
        :param build_id: ID of the build
        :return:
        """
        watch_end = datetime.now() + timedelta(seconds=60 * 30)
        state_reported = ""

        while True:
            if datetime.now() > watch_end:
                self.failure_msg += "The build did not finish in time 30 minutes.\n"
                return

            build = copr.build_proxy.get(build_id)
            if build.state == state_reported:
                time.sleep(20)
                continue
            state_reported = build.state

            if state_reported not in [
                "running",
                "pending",
                "starting",
                "forked",
                "importing",
                "waiting",
            ]:

                if state_reported != "succeeded":
                    self.failure_msg += f"The build in Copr was not successful. " \
                                        f"Copr state: {state_reported}.\n"
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

            states = [
                status.state
                for status in statuses
                if "packit-stg" not in status.context
            ]

            if "pending" not in states:
                break

            if datetime.now() > watch_end:
                self.failure_msg += "These statuses were set to pending 20 minutes " \
                                    "after Copr build had been built:\n"
                for status in statuses:
                    if "packit-stg" not in status.context and status.state == "pending":
                        self.failure_msg += f"{status.context}\n"
                return []

            time.sleep(20)

        return statuses

    def check_statuses(self):
        """
        Check whether all statuses are set to success.
        :return:
        """
        if "The build in Copr was not successful." in self.failure_msg:
            return

        statuses = self.watch_statuses()
        for status in statuses:
            if "packit-stg" not in status.context and status.state == "failed":
                self.failure_msg += (
                    f"Status {status.context} was set to failure although the build in "
                    f"Copr was successful, message: {status.description}.\n"
                )

    def check_comment(self):
        """
        Check whether p-s has commented correctly about the Copr build result.
        :return:
        """
        failure = "The build in Copr was not successful." in self.failure_msg

        if failure:
            build_comment = [
                comment
                for comment in project.get_pr_comments(self.pr_id, reverse=True)
                if comment.author == "packit-as-a-service[bot]"
            ][0]
            if build_comment.comment.startswith("Congratulations!"):
                self.failure_msg += (
                    "No comment from p-s about unsuccessful last copr build found.\n"
                )
                return

        else:
            build_comment = [
                comment
                for comment in project.get_pr_comments(self.pr_id, reverse=True)
                if comment.author.startswith("packit-as-a-service")
            ][0]
            if (
                build_comment.author == "packit-as-a-service[bot]"
                and not build_comment.comment.startswith("Congratulations!")
            ):
                self.failure_msg += "Copr build succeeded and last Github comment " \
                                    "about unsuccessful copr build found.\n"
                return

    def get_statuses(self):
        """
        Get commit statuses from the most recent commit.
        :return: [CommitStatus]
        """
        commit_sha = project.get_all_pr_commits(self.pr_id)[-1]
        commit = project.github_repo.get_commit(commit_sha)
        return commit.get_combined_status().statuses


if __name__ == "__main__":
    sentry_sdk.init(getenv("SENTRY_SECRET"))

    prs = [
        pr for pr in project.get_pr_list() if pr.title.startswith("Basic test case:")
    ]

    for pr in prs:
        testcase = Testcase(pr_id=pr.id)
        testcase.run_checks()
        if testcase.failure_msg:
            sentry_sdk.capture_message(f"{pr.title} ({pr.url}) failed: {testcase.failure_msg}")
