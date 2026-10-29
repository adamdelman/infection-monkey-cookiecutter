# {{ cookiecutter.project_name | replace('-', ' ') | replace('_', ' ') }}
{%- if cookiecutter.hook_gitlint %}

## Development setup

Install [pre-commit](https://pre-commit.com) once per machine, then enable the hooks in each clone:

```bash
pipx install pre-commit   # or: brew install pre-commit
pre-commit install        # installs the pre-commit, prepare-commit-msg and commit-msg hooks
```

If `pre-commit install` refuses because `core.hooksPath` is set (e.g. by the old commit-guard tool),
remove the global hook path first:

```bash
git config --global --unset core.hooksPath
```

## Commit messages

Every commit message needs a Jira-prefixed, imperative title and a `PR #N` line:

```text
OCPSG-123: Add map writer

Optional explanation of what changed and why.

PR #456
```

The title starts with the Jira key and an imperative verb (`Add`, not `Added` or `Adds`) and is
at most 72 characters long.

You type the `PR #N` line once per branch. After that it is added to every new commit on the
branch, and to the merge message when the branch is merged into `master`, `main` or `dev`.

Before the PR exists, commit with `git commit --no-verify`, push and open the PR, then run
`git commit --amend` and add the `PR #N` line.

Fixups, squashes, amends, `git revert` commits, merges into feature branches and `git pull` merges
on `master`, `main` or `dev` are not checked.
{%- endif %}
