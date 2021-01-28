# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import enum
import sentry_sdk
import time

from copr.v3 import Client
from datetime import datetime, timedelta, date
from os import getenv

from github import InputGitAuthor
from ogr.services.github import GithubService
from ogr.abstract import PullRequest


copr = Client.create_from_config_file()
service = GithubService(token=getenv("GITHUB_TOKEN"))
project = service.get_project(repo="hello-world", namespace="packit")
user = InputGitAuthor(
    name="Release Bot", email="user-cont-team+release-bot@redhat.com"
)


class Trigger(str, enum.Enum):
    comment = "comment"
    pr_opened = "pr_opened"
    push = "push"


class Testcase:
    def __init__(self, pr: PullRequest = None, trigger: Trigger = Trigger.pr_opened):
        self.pr = pr
        self.failure_msg = ""
        self.trigger = trigger
        self._copr_project_name = None

    @property
    def copr_project_name(self):
        """
        Get the name of Copr project from id of the PR.
        :return:
        """
        if self.pr and not self._copr_project_name:
            self._copr_project_name = (
                f"packit-hello-world-{self.pr.id}"
            )
        return self._copr_project_name

    def run_test(self):
        """
        Run all checks, if there is any failure message, send it to Sentry and in case of
        opening PR close it.
        :return:
        """
        self.run_checks()
        if self.failure_msg:
            sentry_sdk.capture_message(
                f"{self.pr.title} ({self.pr.url}) failed: {self.failure_msg}"
            )
        if self.trigger == Trigger.pr_opened:
            self.pr.close()

    def trigger_build(self):
        """
        Trigger the build (by commenting/pushing to the PR/opening a new PR).
        :return:
        """
        if self.trigger == Trigger.comment:
            project.pr_comment(self.pr.id, "/packit build")
        elif self.trigger == Trigger.push:
            self.push_to_pr()
        else:
            self.create_pr()

    def push_to_pr(self):
        """
        Push a new commit to the PR.
        :return:
        """
        contents = project.github_repo.get_contents(
            "test.txt", ref=self.pr.source_branch
        )
        # https://pygithub.readthedocs.io/en/latest/examples/Repository.html#update-a-file-in-the-repository
        # allows empty commit (always the same content of file)
        project.github_repo.update_file(
            path=contents.path,
            message=f"Commit build trigger ({date.today().strftime('%d/%m/%y')})",
            content="Testing the push trigger.",
            sha=contents.sha,
            branch=self.pr.source_branch,
            committer=user,
            author=user,
        )

    def create_pr(self):
        """
        Create a new PR, if the source branch 'test_case_opened_pr' does not exist,
        create one and commit some changes before it.
        :return:
        """
        source_branch = "test_case_opened_pr"
        pr_title = "Basic test case - opened PR trigger"

        if source_branch not in project.get_branches():
            # if the source branch does not exist, create one
            # and create a commit
            commit = project.github_repo.get_commit("HEAD")
            project.github_repo.create_git_ref(f"refs/heads/{source_branch}", commit.sha)
            project.github_repo.create_file(
                path="test.txt",
                message="Opened PR trigger",
                content="Testing the opened PR trigger.",
                branch=source_branch,
                committer=user,
                author=user
            )

        existing_pr = [pr for pr in project.get_pr_list() if pr.title == pr_title]
        if len(existing_pr) == 1:
            existing_pr[0].close()

        self.pr = project.create_pr(
            title=pr_title,
            body="This test case is triggered automatically by our validation script.",
            target_branch=project.default_branch,
            source_branch=source_branch,
        )

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
        Check whether some commit status is set to pending (they are updated in loop
        so it is enough).
        :return:
        """
        statuses = [
            status.context
            for status in self.get_statuses()
            if "packit-stg" not in status.context
        ]

        watch_end = datetime.now() + timedelta(seconds=60)
        failure_message = (
            "Github statuses were not set "
            "to pending in time 1 minute.\n"
        )

        # when a new PR is opened
        while len(statuses) == 0:
            if datetime.now() > watch_end:
                self.failure_msg += failure_message
                return
            statuses = [
                status.context
                for status in self.get_statuses()
                if "packit-stg" not in status.context
            ]

        while True:
            if datetime.now() > watch_end:
                self.failure_msg += failure_message
                return

            new_statuses = [
                (status.context, status.state)
                for status in self.get_statuses()
                if status.context in statuses
            ]
            for name, state in new_statuses:
                if state == "pending":
                    return

            time.sleep(5)

    def check_build_submitted(self):
        """
        Check whether the build was submitted in Copr in time 30 minutes.
        :return:
        """
        if self.pr:
            try:
                old_build_len = len(
                    copr.build_proxy.get_list("packit", self.copr_project_name)
                )
            except Exception:
                old_build_len = 0

            old_comment_len = len(self.pr.get_comments())
        else:
            # the PR is not created yet
            old_build_len = 0
            old_comment_len = 0

        self.trigger_build()

        watch_end = datetime.now() + timedelta(seconds=60 * 30)

        self.check_statuses_set_to_pending()

        while True:
            if datetime.now() > watch_end:
                self.failure_msg += (
                    "The build was not submitted in Copr in time 30 minutes.\n"
                )
                return None

            try:
                new_builds = copr.build_proxy.get_list("packit", self.copr_project_name)
            except Exception:
                # project does not exist yet
                continue

            if len(new_builds) >= old_build_len + 1:
                return new_builds[0]

            new_comments = self.pr.get_comments(reverse=True)
            new_comments = new_comments[: (len(new_comments) - old_comment_len)]

            if len(new_comments) > 1:
                comment = [
                    comment.comment
                    for comment in new_comments
                    if comment.author == "packit-as-a-service[bot]"
                ]
                if len(comment) > 0:
                    if "error" in comment[0] or "whitelist" in comment[0]:
                        self.failure_msg += (
                            f"The build was not submitted in Copr, "
                            f"Github comment from p-s: {comment[0]}\n"
                        )
                        return None
                    else:
                        self.failure_msg += (
                            f"New github comment from p-s while "
                            f"submitting Copr build: {comment[0]}\n"
                        )

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
                    self.failure_msg += (
                        f"The build in Copr was not successful. "
                        f"Copr state: {state_reported}.\n"
                    )
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
                self.failure_msg += (
                    "These statuses were set to pending 20 minutes "
                    "after Copr build had been built:\n"
                )
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
        Check whether p-s has commented when the Copr build was not successful.
        :return:
        """
        failure = "The build in Copr was not successful." in self.failure_msg

        if failure:
            packit_comments = [
                comment
                for comment in self.pr.get_comments(reverse=True)
                if comment.author == "packit-as-a-service[bot]"
            ]
            if not packit_comments:
                self.failure_msg += (
                    "No comment from p-s about unsuccessful last copr build found.\n"
                )

    def get_statuses(self):
        """
        Get commit statuses from the head commit of the PR.
        :return: [CommitStatus]
        """
        commit = project.github_repo.get_commit(self.pr.head_commit)
        return commit.get_combined_status().statuses


if __name__ == "__main__":
    sentry_sdk.init(getenv("SENTRY_SECRET"))

    # run testcases where the build is triggered by a '/packit build' comment
    prs_for_comment = [
        pr for pr in project.get_pr_list() if pr.title.startswith("Basic test case:")
    ]
    for pr in prs_for_comment:
        Testcase(pr=pr, trigger=Trigger.comment).run_test()

    # run testcase where the build is triggered by push
    pr_for_push = [
        pr
        for pr in project.get_pr_list()
        if pr.title.startswith("Basic test case - push trigger")
    ]
    if pr_for_push:
        Testcase(pr=pr_for_push[0], trigger=Trigger.push).run_test()

    # run testcase where the build is triggered by opening a new PR
    Testcase().run_test()
