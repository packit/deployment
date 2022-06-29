# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import enum
import time
import logging

from typing import Union
from copr.v3 import Client
from datetime import datetime, timedelta, date
from os import getenv
from dataclasses import dataclass

from github import InputGitAuthor
from github.Commit import Commit
from github.GitRef import GitRef

from ogr.services.github import GithubService
from ogr.abstract import PullRequest
from ogr.services.github.check_run import GithubCheckRunStatus, GithubCheckRunResult

copr = Client({"copr_url": "https://copr.fedorainfracloud.org"})
service = GithubService(token=getenv("GITHUB_TOKEN"))
project = service.get_project(repo="hello-world", namespace="packit")
user = InputGitAuthor(name="Release Bot", email="user-cont-team+release-bot@redhat.com")
logging.basicConfig(level=logging.WARNING)


class Deployment(str, enum.Enum):
    production = "production"
    staging = "staging"


@dataclass
class YamlFix:
    from_str: str = ""
    to_str: str = ""
    git_msg: str = ""


@dataclass
class ProductionInfo:
    app_name: str = "Packit-as-a-Service"
    pr_comment: str = "/packit build"
    opened_pr_trigger__packit_yaml_fix: YamlFix = None
    copr_user = "packit"
    push_trigger_tests_prefix = "Basic test case - push trigger"
    bot_name = "packit-as-a-service[bot]"


@dataclass
class StagingInfo:
    app_name = "Packit-as-a-Service-stg"
    pr_comment = "/packit-stg build"
    opened_pr_trigger__packit_yaml_fix = YamlFix(
        b"---", b'---\npackit_instances: ["stg"]', "Build on staging"
    )
    copr_user = "packit-stg"
    push_trigger_tests_prefix = "Basic test case (stg) - push trigger"
    bot_name = "packit-as-a-service-stg[bot]"


DeploymentInfo = Union[ProductionInfo, StagingInfo]


class Trigger(str, enum.Enum):
    comment = "comment"
    pr_opened = "pr_opened"
    push = "push"


class Testcase:
    def __init__(
        self,
        pr: PullRequest = None,
        trigger: Trigger = Trigger.pr_opened,
        deployment: DeploymentInfo = None,
    ):
        self.pr = pr
        self.pr_branch_ref: GitRef = None
        self.failure_msg = ""
        self.trigger = trigger
        self.head_commit = pr.head_commit if pr else None
        self._copr_project_name = None
        self.deployment = deployment if deployment else ProductionInfo()

    @property
    def copr_project_name(self):
        """
        Get the name of Copr project from id of the PR.
        :return:
        """
        if self.pr and not self._copr_project_name:
            self._copr_project_name = f"packit-hello-world-{self.pr.id}"
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
            self.pr_branch_ref.delete()

    def trigger_build(self):
        """
        Trigger the build (by commenting/pushing to the PR/opening a new PR).
        :return:
        """
        if self.trigger == Trigger.comment:
            self.pr.comment(self.deployment.pr_comment)
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
        commit: Commit = project.github_repo.update_file(
            path=contents.path,
            message=f"Commit build trigger ({date.today().strftime('%d/%m/%y')})",
            content="Testing the push trigger.",
            sha=contents.sha,
            branch=self.pr.source_branch,
            committer=user,
            author=user,
        )["commit"]
        self.head_commit = commit.sha

    def fix_packit_yaml(self, ref: str, branch: str):
        """
        Update .packit.yaml file according to the deployment needs
        """
        if self.deployment.opened_pr_trigger__packit_yaml_fix:
            packit_yaml = project.github_repo.get_contents(path=".packit.yaml", ref=ref)
            packit_yaml_content = packit_yaml.decoded_content
            packit_yaml_content = packit_yaml_content.replace(
                self.deployment.opened_pr_trigger__packit_yaml_fix.from_str,
                self.deployment.opened_pr_trigger__packit_yaml_fix.to_str,
            )
            project.github_repo.update_file(
                packit_yaml.path,
                self.deployment.opened_pr_trigger__packit_yaml_fix.git_msg,
                packit_yaml_content,
                packit_yaml.sha,
                branch=branch,
            )

    def create_pr(self):
        """
        Create a new PR, if the source branch 'test_case_opened_pr' does not exist,
        create one and commit some changes before it.
        :return:
        """
        source_branch = "test_case_opened_pr"
        pr_title = "Basic test case - opened PR trigger"
        ref = f"refs/heads/{source_branch}"
        # Delete the branch from the previous test run if it exists.
        existing_branch = project.github_repo.get_git_matching_refs(
            f"heads/{source_branch}"
        )
        if existing_branch.totalCount:
            existing_branch[0].delete()
        # Delete the PR from the previous test run if it exists.
        existing_pr = [pr for pr in project.get_pr_list() if pr.title == pr_title]
        if len(existing_pr) == 1:
            existing_pr[0].close()

        # create a new branch and commit for the PR
        commit = project.github_repo.get_commit("HEAD")
        self.pr_branch_ref = project.github_repo.create_git_ref(ref, commit.sha)
        project.github_repo.create_file(
            path="test.txt",
            message="Opened PR trigger",
            content="Testing the opened PR trigger.",
            branch=source_branch,
            committer=user,
            author=user,
        )
        self.fix_packit_yaml(ref, source_branch)

        self.pr = project.create_pr(
            title=pr_title,
            body="This test case is triggered automatically by our validation script.",
            target_branch=project.default_branch,
            source_branch=source_branch,
        )
        self.head_commit = self.pr.head_commit

    def run_checks(self):
        """
        Run all checks of the test case.
        :return:
        """
        build = self.check_build_submitted()

        if not build:
            return

        self.check_build(build.id)
        self.check_completed_check_runs()
        self.check_comment()

    def check_pending_check_runs(self):
        """
        Check whether some check run is set to queued (they are updated in loop
        so it is enough).
        :return:
        """
        check_runs = [
            check_run.name
            for check_run in project.get_check_runs(commit_sha=self.head_commit)
            if check_run.app.name == self.deployment.app_name
        ]

        watch_end = datetime.now() + timedelta(seconds=60)
        failure_message = "Github check runs were not set to queued in time 1 minute.\n"

        # when a new PR is opened
        while len(check_runs) == 0:
            if datetime.now() > watch_end:
                self.failure_msg += failure_message
                return
            check_runs = [
                check_run.name
                for check_run in project.get_check_runs(commit_sha=self.head_commit)
                if check_run.app.name == self.deployment.app_name
            ]

        while True:
            if datetime.now() > watch_end:
                self.failure_msg += failure_message
                return

            new_check_runs = [
                (check_run.name, check_run.status)
                for check_run in project.get_check_runs(commit_sha=self.head_commit)
                if check_run.name in check_runs
            ]
            for name, state in new_check_runs:
                # check run can be in a short period time changed from queued (Task was accepted)
                # to in_progress, so check only that it doesn't have completed status
                if state != GithubCheckRunStatus.completed:
                    return

            time.sleep(5)

    def check_build_submitted(self):
        """
        Check whether the build was submitted in Copr in time 15 minutes.
        :return:
        """
        if self.pr:
            try:
                old_build_len = len(
                    copr.build_proxy.get_list(
                        self.deployment.copr_user, self.copr_project_name
                    )
                )
            except Exception:
                old_build_len = 0

            old_comment_len = len(self.pr.get_comments())
        else:
            # the PR is not created yet
            old_build_len = 0
            old_comment_len = 0

        self.trigger_build()

        watch_end = datetime.now() + timedelta(seconds=60 * 15)

        self.check_pending_check_runs()

        while True:
            if datetime.now() > watch_end:
                self.failure_msg += (
                    "The build was not submitted in Copr in time 15 minutes.\n"
                )
                return None

            try:
                new_builds = copr.build_proxy.get_list(
                    self.deployment.copr_user, self.copr_project_name
                )
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
                    if comment.author == self.deployment.bot_name
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
        Check whether the build was successful in Copr in time 15 minutes.
        :param build_id: ID of the build
        :return:
        """
        watch_end = datetime.now() + timedelta(seconds=60 * 15)
        state_reported = ""

        while True:
            if datetime.now() > watch_end:
                self.failure_msg += "The build did not finish in time 15 minutes.\n"
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

    def watch_check_runs(self):
        """
        Watch the check runs 20 minutes, if all the check runs have completed status, return the check runs.
        :return: [CheckRun]
        """
        watch_end = datetime.now() + timedelta(seconds=60 * 20)

        while True:
            check_runs = project.get_check_runs(commit_sha=self.head_commit)

            states = [
                check_run.status
                for check_run in check_runs
                if check_run.app.name == self.deployment.app_name
            ]

            if all(state == GithubCheckRunStatus.completed for state in states):
                break

            if datetime.now() > watch_end:
                self.failure_msg += (
                    "These check runs were not completed 20 minutes "
                    "after Copr build had been built:\n"
                )
                for check_run in check_runs:
                    if (
                        check_run.app.name == self.deployment.app_name
                        and check_run.status != GithubCheckRunStatus.completed
                    ):
                        self.failure_msg += f"{check_run.name}\n"
                return []

            time.sleep(20)

        return check_runs

    def check_completed_check_runs(self):
        """
        Check whether all check runs are set to success.
        :return:
        """
        if "The build in Copr was not successful." in self.failure_msg:
            return

        check_runs = self.watch_check_runs()
        for check_run in check_runs:
            if (
                check_run.app.name == self.deployment.app_name
                and check_run.conclusion == GithubCheckRunResult.failure
            ):
                self.failure_msg += (
                    f"Check run {check_run.name} was set to failure although the build in "
                    f"Copr was successful, message: {check_run.output.title}.\n"
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
                if comment.author == self.deployment.bot_name
            ]
            if not packit_comments:
                self.failure_msg += (
                    "No comment from p-s about unsuccessful last copr build found.\n"
                )


if __name__ == "__main__":
    sentry_secret = getenv("SENTRY_SECRET")
    if sentry_secret:
        import sentry_sdk

        sentry_sdk.init(sentry_secret)
    else:
        logging.warning("SENTRY_SECRET was not set!")

    deployment = (
        ProductionInfo()
        if getenv("DEPLOYMENT", Deployment.production) == Deployment.production
        else StagingInfo()
    )

    # run testcases where the build is triggered by a '/packit build' comment
    prs_for_comment = [
        pr for pr in project.get_pr_list() if pr.title.startswith("Basic test case:")
    ]
    for pr in prs_for_comment:
        Testcase(pr=pr, trigger=Trigger.comment, deployment=deployment).run_test()

    # run testcase where the build is triggered by push
    pr_for_push = [
        pr
        for pr in project.get_pr_list()
        if pr.title.startswith(deployment.push_trigger_tests_prefix)
    ]
    if pr_for_push:
        Testcase(
            pr=pr_for_push[0], trigger=Trigger.push, deployment=deployment
        ).run_test()

    # run testcase where the build is triggered by opening a new PR
    Testcase(deployment=deployment).run_test()
