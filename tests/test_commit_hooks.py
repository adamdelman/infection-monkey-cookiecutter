import os
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
import yaml
from cookiecutter.main import cookiecutter

TEMPLATE_DIR = Path(__file__).parent.parent
ISOLATED_GIT_ENV = {**os.environ, "GIT_CONFIG_GLOBAL": os.devnull}


def dedent_block(text: str) -> str:
    return textwrap.dedent(text).lstrip("\n")


THIS_PR_COMMIT = dedent_block(
    """
    OCPSG-1: Add x

    PR #42
    """
)
OTHER_PR_COMMIT = dedent_block(
    """
    OCPSG-3: Add w

    PR #8
    """
)


def run(cwd: Path, *args: str) -> None:
    subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=True, env=ISOLATED_GIT_ENV)


@pytest.fixture(scope="module")
def project(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output_dir = tmp_path_factory.mktemp("rendered")
    path = Path(
        cookiecutter(
            str(TEMPLATE_DIR),
            no_input=True,
            accept_hooks=False,
            output_dir=str(output_dir),
            extra_context={"project_name": "demo", "hook_gitlint": True},
        )
    )
    run(path, "git", "init", "-q")
    return path


def lint(project: Path, message: str, *gitlint_args: str) -> tuple[int, str]:
    message_file = project / ".git" / "TEST_MSG"
    message_file.write_text(message)
    gitlint = [
        sys.executable,
        "-m",
        "gitlint.cli",
        *gitlint_args,
        "--msg-filename",
        str(message_file),
    ]
    result = subprocess.run(
        gitlint, cwd=project, capture_output=True, text=True, env=ISOLATED_GIT_ENV
    )
    return result.returncode, result.stderr


@pytest.mark.parametrize(
    "message",
    [
        pytest.param(
            dedent_block(
                """
                GC-181422: Process files

                Why this matters.

                PR #1
                """
            ),
            id="explained",
        ),
        pytest.param(
            dedent_block(
                """
                OCPSG-1: Embed schema

                PR #1
                """
            ),
            id="stemmer-exception",
        ),
        pytest.param(
            dedent_block(
                """
                OCPSG-1: Bring back retries

                PR #1
                """
            ),
            id="verb-ending-in-ing",
        ),
        pytest.param(
            dedent_block(
                """
                GC2-15: Add x

                PR #1
                """
            ),
            id="key-with-digit",
        ),
        pytest.param(
            dedent_block(
                """
                MY_PROJ-7: Add x

                PR #1
                """
            ),
            id="key-with-underscore",
        ),
        pytest.param(
            dedent_block(
                """
                Merge branch 'OCPSG-1292-automatically-add-release-notes-and-many-more-words'

                PR #1277
                """
            ),
            id="long-merge-title",
        ),
        pytest.param(
            dedent_block(
                """
                OCPSG-1: Fix command injection

                https://github.com/AkamaiETP/ocp-suggestions/pull/1254#discussion_r4119826451

                PR #1
                """
            ),
            id="long-url-line",
        ),
        pytest.param(
            dedent_block(
                """
                OCPSG-1: Bump version

                PR #1

                Co-authored-by: mssalvatore <19957806+mssalvatore@users.noreply.github.com>
                """
            ),
            id="long-co-authored-by-line",
        ),
        pytest.param("OCPSG-1: fixup! OCPSG-1: Add x\n", id="jira-prefixed-fixup"),
        pytest.param(
            dedent_block(
                """
                OCPSG-1: amend! OCPSG-1: Add x

                OCPSG-1: Add x better
                """
            ),
            id="jira-prefixed-amend",
        ),
        pytest.param(
            dedent_block(
                """
                OCPSG-1: Revert "OCPSG-1: Add x"

                This reverts commit abc.
                """
            ),
            id="jira-prefixed-revert",
        ),
    ],
)
def test_gitlint__accepts_valid_message(project: Path, message: str) -> None:
    assert lint(project, message) == (0, "")


@pytest.mark.parametrize(
    "message, rule",
    [
        pytest.param(
            dedent_block(
                """
                OCPSG-1: Add x

                Adds the writer.
                """
            ),
            "UC1",
            id="body-without-pr",
        ),
        pytest.param(
            dedent_block(
                """
                add map writer

                PR #1
                """
            ),
            "T7",
            id="no-jira-key",
        ),
        pytest.param(
            dedent_block(
                """
                Merged stuff

                PR #1
                """
            ),
            "T7",
            id="hand-written-merge-title",
        ),
        pytest.param(
            dedent_block(
                """
                OCPSG-1: Added x

                PR #1
                """
            ),
            "UL1",
            id="past-tense-known-verb",
        ),
        pytest.param(
            dedent_block(
                """
                OCPSG-1386: OCPSG-700: Removed ACR login

                PR #1
                """
            ),
            "UL1",
            id="past-tense-after-two-jira-keys",
        ),
        pytest.param(
            dedent_block(
                """
                OCPSG-1: Add x

                This explanation keeps on running until it ends up past the seventy-two limit.

                PR #1
                """
            ),
            "B1",
            id="long-prose-line",
        ),
        pytest.param(
            dedent_block(
                """
                OCPSG-1: Bumped x

                PR #1
                """
            ),
            "UL1",
            id="past-tense-unknown-verb",
        ),
        pytest.param(
            dedent_block(
                """
                OCPSG-1: Initial commit

                PR #1
                """
            ),
            "UL1",
            id="not-a-verb",
        ),
    ],
)
def test_gitlint__rejects_invalid_message(project: Path, message: str, rule: str) -> None:
    returncode, stderr = lint(project, message)
    assert returncode != 0
    assert rule in stderr


def commit(repo: Path, message: str) -> None:
    run(repo, "git", "commit", "-q", "--allow-empty", "--no-verify", "-m", message)


def prepare_message(repo: Path, message: str, *hook_args: str) -> str:
    message_file = repo / ".git" / "COMMIT_EDITMSG"
    message_file.write_text(message)
    hook = repo / "commit_hooks" / "add_pr_number.py"
    run(repo, sys.executable, str(hook), *hook_args, str(message_file))
    return message_file.read_text()


@pytest.fixture
def repo(tmp_path: Path, project: Path) -> Path:
    run(tmp_path, "git", "init", "-q", "--bare", "origin.git")
    repo = tmp_path / "repo"
    repo.mkdir()
    for args in (
        ["init", "-q", "-b", "master"],
        ["config", "user.email", "t@example.com"],
        ["config", "user.name", "t"],
        ["remote", "add", "origin", str(tmp_path / "origin.git")],
    ):
        run(repo, "git", *args)
    commit(repo, "Initial commit")
    run(repo, "git", "push", "-q", "-u", "origin", "master")
    shutil.copytree(project / "commit_hooks", repo / "commit_hooks")
    shutil.copy(project / ".gitlint", repo)
    return repo


@pytest.fixture
def feature_branch(repo: Path) -> Path:
    run(repo, "git", "checkout", "-q", "-b", "OCPSG-1-x")
    commit(repo, THIS_PR_COMMIT)
    return repo


def test_add_pr_number__adds_branch_pr_number(feature_branch: Path) -> None:
    empty_editor_message = "\n# Please enter the commit message\n"
    assert prepare_message(feature_branch, empty_editor_message) == (
        "\n\nPR #42\n# Please enter the commit message\n"
    )
    assert prepare_message(feature_branch, "OCPSG-1: Add y\n") == dedent_block(
        """
        OCPSG-1: Add y

        PR #42
        """
    )


def test_add_pr_number__branch_is_pushed(feature_branch: Path) -> None:
    run(feature_branch, "git", "push", "-q", "-u", "origin", "OCPSG-1-x")
    assert prepare_message(feature_branch, "OCPSG-1: Add y\n") == dedent_block(
        """
        OCPSG-1: Add y

        PR #42
        """
    )


def test_add_pr_number__master_ignores_merged_pr(repo: Path) -> None:
    commit(repo, OTHER_PR_COMMIT)
    run(repo, "git", "push", "-q", "origin", "master")
    assert prepare_message(repo, "OCPSG-12: Fix outage\n") == "OCPSG-12: Fix outage\n"


def test_add_pr_number__new_branch_ignores_master_pr(repo: Path) -> None:
    commit(repo, OTHER_PR_COMMIT)
    run(repo, "git", "push", "-q", "origin", "master")
    run(repo, "git", "checkout", "-q", "-b", "OCPSG-1-x")
    assert prepare_message(repo, "OCPSG-1: Add y\n") == "OCPSG-1: Add y\n"


def test_add_pr_number__branch_created_from_origin_master_ignores_master_pr(repo: Path) -> None:
    commit(repo, OTHER_PR_COMMIT)
    run(repo, "git", "push", "-q", "origin", "master")
    run(repo, "git", "checkout", "-q", "-b", "OCPSG-1-x", "origin/master")
    assert prepare_message(repo, "OCPSG-1: Add y\n") == "OCPSG-1: Add y\n"


def test_add_pr_number__squash_message(feature_branch: Path) -> None:
    squash = dedent_block(
        """
        # This is a combination of 2 commits.
        # This is the 1st commit message:

        OCPSG-1: Add y

        # This is the commit message #2:

        OCPSG-1: Add z

        # Please enter the commit message
        """
    )
    expected = dedent_block(
        """
        # This is a combination of 2 commits.
        # This is the 1st commit message:

        OCPSG-1: Add y

        # This is the commit message #2:

        OCPSG-1: Add z

        PR #42

        # Please enter the commit message
        """
    )
    assert prepare_message(feature_branch, squash) == expected


def test_add_pr_number__verbose_diff_is_unchanged(feature_branch: Path) -> None:
    verbose_message = dedent_block(
        """
        OCPSG-1: Add y
        # ------------------------ >8 ------------------------
        diff --git a/x b/x
        +added line
        """
    )
    expected = dedent_block(
        """
        OCPSG-1: Add y

        PR #42
        # ------------------------ >8 ------------------------
        diff --git a/x b/x
        +added line
        """
    )
    assert prepare_message(feature_branch, verbose_message) == expected


def test_add_pr_number__existing_pr_number_or_fixup_is_unchanged(feature_branch: Path) -> None:
    with_pr_number = dedent_block(
        """
        OCPSG-1: Add y

        PR #9
        """
    )
    fixup = "fixup! OCPSG-1: Add x\n"
    assert prepare_message(feature_branch, with_pr_number) == with_pr_number
    assert prepare_message(feature_branch, fixup) == fixup


def test_merge_into_master__requires_and_gets_branch_pr_number(feature_branch: Path) -> None:
    run(feature_branch, "git", "checkout", "-q", "master")
    commit(feature_branch, OTHER_PR_COMMIT)
    run(feature_branch, "git", "merge", "-q", "--no-ff", "--no-commit", "OCPSG-1-x")
    message = "Merge branch 'OCPSG-1-x'\n"
    expected = dedent_block(
        """
        Merge branch 'OCPSG-1-x'

        PR #42
        """
    )
    assert prepare_message(feature_branch, message) == expected
    assert "UC1" in lint(feature_branch, message)[1]
    assert lint(feature_branch, expected) == (0, "")


def test_merge_into_stale_master__ignores_pr_numbers_synced_from_origin(
    feature_branch: Path,
) -> None:
    run(feature_branch, "git", "checkout", "-q", "master")
    commit(feature_branch, OTHER_PR_COMMIT)
    run(feature_branch, "git", "push", "-q", "origin", "master")
    run(feature_branch, "git", "reset", "-q", "--hard", "HEAD~1")
    run(feature_branch, "git", "checkout", "-q", "OCPSG-1-x")
    run(feature_branch, "git", "merge", "-q", "--no-ff", "--no-commit", "origin/master")
    run(feature_branch, "git", "commit", "-q", "--no-verify", "-m", "Merge origin/master")
    run(feature_branch, "git", "checkout", "-q", "master")
    run(feature_branch, "git", "merge", "-q", "--no-ff", "--no-commit", "OCPSG-1-x")
    assert prepare_message(feature_branch, "Merge branch 'OCPSG-1-x'\n") == dedent_block(
        """
        Merge branch 'OCPSG-1-x'

        PR #42
        """
    )


def test_merge_into_feature_branch__needs_no_pr_number(feature_branch: Path) -> None:
    run(feature_branch, "git", "checkout", "-q", "master")
    commit(feature_branch, OTHER_PR_COMMIT)
    run(feature_branch, "git", "checkout", "-q", "OCPSG-1-x")
    run(feature_branch, "git", "merge", "-q", "--no-ff", "--no-commit", "master")
    message = "Merge branch 'master' into OCPSG-1-x\n"
    jira_prefixed_message = f"OCPSG-1: {message}"
    assert prepare_message(feature_branch, message) == message
    assert lint(feature_branch, message) == (0, "")
    assert lint(feature_branch, jira_prefixed_message) == (0, "")


def test_pull_on_master__needs_no_pr_number(repo: Path) -> None:
    commit(repo, OTHER_PR_COMMIT)
    run(repo, "git", "push", "-q", "origin", "master")
    run(repo, "git", "reset", "-q", "--hard", "HEAD~1")
    commit(
        repo,
        dedent_block(
            """
            OCPSG-4: Add v

            PR #9
            """
        ),
    )
    run(repo, "git", "merge", "-q", "--no-ff", "--no-commit", "origin/master")
    message = "Merge branch 'master' of github.com:AkamaiETP/demo\n"
    assert prepare_message(repo, message) == message
    assert lint(repo, message) == (0, "")


def test_long_lived_branches__configured_branch_requires_pr_number(feature_branch: Path) -> None:
    run(feature_branch, "git", "checkout", "-q", "-b", "release", "master")
    run(feature_branch, "git", "merge", "-q", "--no-ff", "--no-commit", "OCPSG-1-x")
    message = "Merge branch 'OCPSG-1-x' into release\n"
    assert prepare_message(feature_branch, message) == message
    assert lint(feature_branch, message) == (0, "")
    hook_arg = "--long-lived-branches=master,release"
    gitlint_arg = "body-requires-pr-number.long-lived-branches=master,release"
    assert prepare_message(feature_branch, message, hook_arg) == dedent_block(
        """
        Merge branch 'OCPSG-1-x' into release

        PR #42
        """
    )
    assert "UC1" in lint(feature_branch, message, "-c", gitlint_arg)[1]


def test_pre_commit_config__same_branches_and_message_file_last(
    project: Path,
) -> None:
    config = yaml.safe_load((project / ".pre-commit-config.yaml").read_text())
    hooks = {hook["id"]: hook for repo in config["repos"] for hook in repo["hooks"]}
    gitlint_args = hooks["gitlint"]["args"]
    assert "body-requires-pr-number.long-lived-branches=master,main,dev" in gitlint_args
    assert gitlint_args[-1] == "--msg-filename"
    assert hooks["add-pr-number"]["args"] == ["--long-lived-branches=master,main,dev"]


def test_hook_gitlint__off_by_default(tmp_path: Path) -> None:
    path = Path(
        cookiecutter(str(TEMPLATE_DIR), no_input=True, accept_hooks=False, output_dir=str(tmp_path))
    )
    assert not (path / ".gitlint").exists()
    assert not any((path / "commit_hooks").iterdir())
    assert "gitlint" not in (path / ".pre-commit-config.yaml").read_text()
