# Copyright Contributors to the Packit project.
# SPDX-License-Identifier: MIT

import enum
import time
import logging

from typing import Union, List, Optional, Type

from gitlab import GitlabGetError
from gitlab.v4.objects import ProjectBranch

from copr.v3 import Client
from datetime import datetime, timedelta, date
from os import getenv
from dataclasses import dataclass

from github import InputGitAuthor
from github.Commit import Commit
from github.GitRef import GitRef

from ogr import GitlabService
from ogr.services.github import GithubService, GithubProject
from ogr.abstract import PullRequest, GitProject, CommitStatus, CommitFlag
from ogr.services.github.check_run import (
    GithubCheckRunStatus,
    GithubCheckRunResult,
    GithubCheckRun,
)
from ogr.services.gitlab import GitlabProject

copr = Client({"copr_url": "https://copr.fedorainfracloud.org"})
logging.basicConfig(level=logging.INFO)


# Everywhere else in the deployment repo environments are called 'prod' and 'stg'.
# Call them some other name here to avoid accidentally deploying the wrong thing.
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
    name: str = "prod"
    app_name: str = "Packit-as-a-Service"
    pr_comment: str = "/packit build"
    opened_pr_trigger__packit_yaml_fix: YamlFix = None
    copr_user = "packit"
    push_trigger_tests_prefix = "Basic test case - push trigger"
    github_bot_name = "packit-as-a-service[bot]"
    gitlab_account_name = "packit-as-a-service"


@dataclass
class StagingInfo:
    name: str = "stg"
    app_name = "Packit-as-a-Service-stg"
    pr_comment = "/packit-stg build"
    opened_pr_trigger__packit_yaml_fix = YamlFix(
        "---", '---\npackit_instances: ["stg"]', "Build using Packit-stg"
    )
    copr_user = "packit-stg"
    push_trigger_tests_prefix = "Basic test case (stg) - push trigger"
    github_bot_name = "packit-as-a-service-stg[bot]"
    gitlab_account_name = "packit-as-a-service-stg"


DeploymentInfo = Union[ProductionInfo, StagingInfo]


class Trigger(str, enum.Enum):
    comment = "comment"
    pr_opened = "pr_opened"
    push = "push"


class Testcase:
    def __init__(
        self,
        project: GitProject,
        pr: PullRequest = None,
        trigger: Trigger = Trigger.pr_opened,
        deployment: DeploymentInfo = None,
    ):
        self.project = project
        self.pr = pr
        self.pr_branch_ref: Optional[Union[ProjectBranch, GitRef]] = None
        self.failure_msg = ""
        self.trigger = trigger
        self.head_commit = pr.head_commit if pr else None
        self._copr_project_name = None
        self.deployment = deployment or ProductionInfo()

    @property
    def copr_project_name(self):
        """
        Get the name of Copr project from id of the PR.
        :return:
        """
        if self.pr and not self._copr_project_name:
            self._copr_project_name = self.construct_copr_project_name()
        return self._copr_project_name

    def run_test(self):
        """
        Run all checks, if there is any failure message, send it to Sentry and in case of
        opening PR close it.
        :return:
        """
        self.run_checks()
        if self.failure_msg:
            message = f"{self.pr.title} ({self.pr.url}) failed: {self.failure_msg}"
            sentry_sdk.capture_message(message) if getenv(
                "SENTRY_SECRET"
            ) else logging.warning(message)

        if self.trigger == Trigger.pr_opened:
            self.pr.close()
            self.pr_branch_ref.delete()

    def trigger_build(self):
        """
        Trigger the build (by commenting/pushing to the PR/opening a new PR).
        :return:
        """
        logging.info(f"Triggering a build for {self.pr if self.pr else 'new PR'}")
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
        branch = self.pr.source_branch
        commit_msg = f"Commit build trigger ({date.today().strftime('%d/%m/%y')})"
        self.head_commit = self.create_empty_commit(branch, commit_msg)

    def create_pr(self):
        """
        Create a new PR, if the source branch 'test_case_opened_pr' does not exist,
        create one and commit some changes before it.
        :return:
        """
        source_branch = f"test/{self.deployment.name}/opened_pr"
        pr_title = f"Basic test case ({self.deployment.name}) - opened PR trigger"
        self.delete_previous_branch(source_branch)
        # Delete the PR from the previous test run if it exists.
        existing_pr = [pr for pr in self.project.get_pr_list() if pr.title == pr_title]
        if len(existing_pr) == 1:
            existing_pr[0].close()

        self.create_file_in_new_branch(source_branch)
        if self.deployment.opened_pr_trigger__packit_yaml_fix:
            self.fix_packit_yaml(source_branch)

        self.pr = self.project.create_pr(
            title=pr_title,
            body="This test case is triggered automatically by our validation script.",
            target_branch=self.project.default_branch,
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
        self.check_completed_statuses()
        self.check_comment()

    def check_pending_check_runs(self):
        """
        Check whether some check run is set to queued
        (they are updated in loop, so it is enough).
        :return:
        """
        status_names = [self.get_status_name(status) for status in self.get_statuses()]

        watch_end = datetime.now() + timedelta(seconds=60)
        failure_message = "Github check runs were not set to queued in time 1 minute.\n"

        # when a new PR is opened
        while len(status_names) == 0:
            if datetime.now() > watch_end:
                self.failure_msg += failure_message
                return
            status_names = [
                self.get_status_name(status) for status in self.get_statuses()
            ]

        logging.info(f"Watching pending statuses for commit {self.head_commit}")
        while True:
            if datetime.now() > watch_end:
                self.failure_msg += failure_message
                return

            new_statuses = [
                status
                for status in self.get_statuses()
                if self.get_status_name(status) in status_names
            ]

            for status in new_statuses:
                # check run / status can be in a short period time changed from queued (Task was accepted)
                # to in_progress, so check only that it doesn't have completed status
                if not self.is_status_completed(status):
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

        logging.info(
            f"Watching whether a build has been submitted for {self.pr} in {self.copr_project_name}"
        )
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
                    comment.body
                    for comment in new_comments
                    if comment.author == self.account_name
                ]
                if len(comment) > 0:
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
        logging.info(f"Watching Copr build {build_id}")

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
                if comment.author == self.account_name
            ]
            if not packit_comments:
                self.failure_msg += (
                    "No comment from p-s about unsuccessful last copr build found.\n"
                )

    def fix_packit_yaml(self, branch: str):
        """
        Update .packit.yaml file in the branch according to the deployment needs
        """
        path = ".packit.yaml"
        packit_yaml_content = self.project.get_file_content(path=path, ref=branch)
        packit_yaml_content = packit_yaml_content.replace(
            self.deployment.opened_pr_trigger__packit_yaml_fix.from_str,
            self.deployment.opened_pr_trigger__packit_yaml_fix.to_str,
        )

        self.update_file_and_commit(
            path=path,
            commit_msg=self.deployment.opened_pr_trigger__packit_yaml_fix.git_msg,
            content=packit_yaml_content,
            branch=branch,
        )

    def check_completed_statuses(self):
        """
        Check whether all check runs are set to success.
        :return:
        """
        if "The build in Copr was not successful." in self.failure_msg:
            return

        statuses = self.watch_statuses()
        for status in statuses:
            if not self.is_status_successful(status):
                self.failure_msg += (
                    f"Check run {self.get_status_name(status)} was set to failure.\n"
                )

    def watch_statuses(self):
        """
        Watch the check runs 20 minutes, if all the check runs have completed status, return the check runs.
        :return: List[CheckRun]
        """
        watch_end = datetime.now() + timedelta(seconds=60 * 20)
        logging.info(f"Watching statuses for commit {self.head_commit}")

        while True:
            statuses = self.get_statuses()

            if all(self.is_status_completed(status) for status in statuses):
                break

            if datetime.now() > watch_end:
                self.failure_msg += (
                    "These check runs were not completed 20 minutes "
                    "after Copr build had been built:\n"
                )
                for status in statuses:
                    if not self.is_status_completed(status):
                        self.failure_msg += f"{self.get_status_name(status)}\n"
                return []

            time.sleep(20)

        return statuses

    @property
    def account_name(self):
        """
        Get the name of the (bot) account in GitHub/GitLab.
        """
        return None

    def get_statuses(self) -> Union[List[GithubCheckRun], List[CommitFlag]]:
        """
        Get the statuses (checks in GitHub).
        """
        pass

    def is_status_completed(self, status: Union[GithubCheckRun, CommitFlag]) -> bool:
        """
        Check whether the status is in completed state (e.g. success, failure).
        """
        pass

    def is_status_successful(self, status: Union[GithubCheckRun, CommitFlag]) -> bool:
        """
        Check whether the status is in successful state.
        """
        pass

    def delete_previous_branch(self, ref: str):
        """
        Delete the branch from the previous test run if it exists.
        """
        pass

    def create_file_in_new_branch(self, branch: str):
        """
        Create a new branch and a new file in it via API (creates new commit).
        """
        pass

    def update_file_and_commit(
        self, path: str, commit_msg: str, content: str, branch: str
    ):
        """
        Update a file via API (creates new commit).
        """
        pass

    def construct_copr_project_name(self) -> str:
        """
        Construct the Copr project name for the PR to check.
        """
        pass

    def get_status_name(self, status: Union[GithubCheckRun, CommitFlag]) -> str:
        """
        Get the name of the status/check that is visible to user.
        """
        pass

    def create_empty_commit(self, branch: str, commit_msg: str) -> str:
        """
        Create an empty commit via API.
        """
        pass


class GithubTestcase(Testcase):
    project: GithubProject
    user = InputGitAuthor(
        name="Release Bot", email="user-cont-team+release-bot@redhat.com"
    )

    @property
    def account_name(self):
        return self.deployment.github_bot_name

    def get_status_name(self, status: GithubCheckRun) -> str:
        return status.name

    def construct_copr_project_name(self) -> str:
        return f"packit-hello-world-{self.pr.id}"

    def create_empty_commit(self, branch: str, commit_msg: str) -> str:
        contents = self.project.github_repo.get_contents("test.txt", ref=branch)
        # https://pygithub.readthedocs.io/en/latest/examples/Repository.html#update-a-file-in-the-repository
        # allows empty commit (always the same content of file)
        commit: Commit = self.project.github_repo.update_file(
            path=contents.path,
            message=commit_msg,
            content="Testing the push trigger.",
            sha=contents.sha,
            branch=branch,
            committer=self.user,
            author=self.user,
        )["commit"]
        return commit.sha

    def get_statuses(self) -> List[GithubCheckRun]:
        return [
            check_run
            for check_run in self.project.get_check_runs(commit_sha=self.head_commit)
            if check_run.app.name == self.deployment.app_name
        ]

    def is_status_successful(self, status: GithubCheckRun) -> bool:
        return status.conclusion == GithubCheckRunResult.success

    def is_status_completed(self, status: GithubCheckRun) -> bool:
        return status.status == GithubCheckRunStatus.completed

    def delete_previous_branch(self, branch: str):
        existing_branch = self.project.github_repo.get_git_matching_refs(
            f"heads/{branch}"
        )
        if existing_branch.totalCount:
            existing_branch[0].delete()

    def create_file_in_new_branch(self, branch: str):
        commit = self.project.github_repo.get_commit("HEAD")
        ref = f"refs/heads/{branch}"
        self.pr_branch_ref = self.project.github_repo.create_git_ref(ref, commit.sha)
        self.project.github_repo.create_file(
            path="test.txt",
            message="Opened PR trigger",
            content="Testing the opened PR trigger.",
            branch=branch,
            committer=self.user,
            author=self.user,
        )

    def update_file_and_commit(
        self, path: str, commit_msg: str, content: str, branch: str
    ):
        contents = self.project.github_repo.get_contents(path=path, ref=branch)
        self.project.github_repo.update_file(
            path,
            commit_msg,
            content,
            contents.sha,
            branch=branch,
            committer=self.user,
            author=self.user,
        )


class GitlabTestcase(Testcase):
    project: GitlabProject

    @property
    def account_name(self):
        return self.deployment.gitlab_account_name

    def get_status_name(self, status: CommitFlag) -> str:
        return status.context

    def construct_copr_project_name(self) -> str:
        return f"gitlab.com-packit-service-hello-world-{self.pr.id}"

    def create_file_in_new_branch(self, branch: str):
        self.pr_branch_ref = self.project.gitlab_repo.branches.create(
            {"branch": branch, "ref": "master"}
        )

        self.project.gitlab_repo.files.create(
            {
                "file_path": "test.txt",
                "branch": branch,
                "content": "Testing the opened PR trigger.",
                "author_email": "validation@packit.dev",
                "author_name": "Packit Validation",
                "commit_message": "Opened PR trigger",
            }
        )

    def get_statuses(self) -> List[CommitFlag]:
        return [
            status
            for status in self.project.get_commit_statuses(commit=self.head_commit)
            if status._raw_commit_flag.author["username"] == self.account_name
        ]

    def is_status_successful(self, status: CommitFlag) -> bool:
        return status.state == CommitStatus.success

    def is_status_completed(self, status: CommitFlag) -> bool:
        return status.state not in [
            CommitStatus.running,
            CommitStatus.pending,
        ]

    def delete_previous_branch(self, branch: str):
        try:
            existing_branch = self.project.gitlab_repo.branches.get(branch)
        except GitlabGetError:
            return

        existing_branch.delete()

    def update_file_and_commit(
        self, path: str, commit_msg: str, content: str, branch: str
    ):
        file = self.project.gitlab_repo.files.get(file_path=path, ref=branch)
        file.content = content
        file.save(branch=branch, commit_message=commit_msg)

    def create_empty_commit(self, branch: str, commit_msg: str) -> str:
        data = {"branch": branch, "commit_message": commit_msg, "actions": []}
        commit = self.project.gitlab_repo.commits.create(data)
        return commit.id


class Tests:
    project: GitProject
    test_case_kls: Type

    def run(self):
        logging.info(
            "Run testcases where the build is triggered by a '/packit build' comment"
        )
        prs_for_comment = [
            pr
            for pr in self.project.get_pr_list()
            if pr.title.startswith("Basic test case:")
        ]
        for pr in prs_for_comment:
            self.test_case_kls(
                project=self.project,
                pr=pr,
                trigger=Trigger.comment,
                deployment=deployment,
            ).run_test()

        logging.info("Run testcase where the build is triggered by push")
        pr_for_push = [
            pr
            for pr in self.project.get_pr_list()
            if pr.title.startswith(deployment.push_trigger_tests_prefix)
        ]
        if pr_for_push:
            self.test_case_kls(
                project=self.project,
                pr=pr_for_push[0],
                trigger=Trigger.push,
                deployment=deployment,
            ).run_test()

        logging.info("Run testcase where the build is triggered by opening a new PR")
        self.test_case_kls(project=self.project, deployment=deployment).run_test()


class GitlabTests(Tests):
    test_case_kls = GitlabTestcase

    def __init__(
        self,
        instance_url="https://gitlab.com",
        namespace="packit-service",
        token_name="GITLAB_TOKEN",
    ):
        gitlab_service = GitlabService(
            token=getenv(token_name), instance_url=instance_url
        )
        self.project: GitlabProject = gitlab_service.get_project(
            repo="hello-world", namespace=namespace
        )


class GithubTests(Tests):
    test_case_kls = GithubTestcase

    def __init__(self):
        github_service = GithubService(token=getenv("GITHUB_TOKEN"))
        self.project = github_service.get_project(
            repo="hello-world", namespace="packit"
        )


if __name__ == "__main__":
    if sentry_secret := getenv("SENTRY_SECRET"):
        import sentry_sdk

        sentry_sdk.init(sentry_secret)
    else:
        logging.warning("SENTRY_SECRET was not set!")

    deployment = (
        ProductionInfo()
        if getenv("DEPLOYMENT", Deployment.production) == Deployment.production
        else StagingInfo()
    )

    if getenv("GITLAB_TOKEN"):
        logging.info("Running validation for GitLab.")
        GitlabTests().run()
    else:
        logging.info("GITLAB_TOKEN not set, skipping the validation for GitLab.")

    if getenv("GITLAB_GNOME_TOKEN"):
        logging.info("Running validation for GitLab (gitlab.gnome.org instance).")
        GitlabTests(
            instance_url="https://gitlab.gnome.org/",
            namespace="packit-validation",
            token_name="GITLAB_GNOME_TOKEN",
        ).run()
    else:
        logging.info(
            "GITLAB_GNOME_TOKEN not set, skipping the validation for GitLab (gitlab.gnome.org instance)."
        )

    if getenv("GITLAB_FREEDESKTOP_TOKEN"):
        logging.info("Running validation for GitLab (gitlab.freedesktop.org instance).")
        GitlabTests(
            instance_url="https://gitlab.freedesktop.org/",
            namespace="packit-validation",
            token_name="GITLAB_FREEDESKTOP_TOKEN",
        ).run()
    else:
        logging.info(
            "GITLAB_FREEDESKTOP_TOKEN not set, skipping the validation for GitLab (gitlab.freedesktop.org instance)."
        )

    if getenv("GITLAB_SALSA_DEBIAN_TOKEN"):
        logging.info("Running validation for GitLab (salsa.debian.org instance).")
        GitlabTests(
            instance_url="https://salsa.debian.org/",
            namespace="packit-validation",
            token_name="GITLAB_SALSA_DEBIAN_TOKEN",
        ).run()
    else:
        logging.info(
            "GITLAB_SALSA_DEBIAN_TOKEN not set, skipping the validation for GitLab (salsa.debian.org instance)."
        )

    if getenv("GITHUB_TOKEN"):
        logging.info("Running validation for GitHub.")
        GithubTests().run()
    else:
        logging.info("GITHUB_TOKEN not set, skipping the validation for GitHub.")
