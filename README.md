# infection-monkey-cookiecutter
A cookiecutter template used for Infection Monkey-related projects

## Commit message hooks (`hook_gitlint`)

`hook_gitlint` adds gitlint checks for commit messages (a Jira-prefixed imperative title and a
`PR #N` line) and a hook that fills in the PR number. It is off by default.

To enable it in an existing project:

```bash
cruft update --variables-to-update '{"hook_gitlint": true}'
```

cruft doesn't update `README.md`, so copy the "Development setup" and "Commit messages" sections
from a newly generated project into the project's README. Each developer then runs
`pre-commit install` once in each clone.

## Testing

The tests cover the `hook_gitlint` commit hooks. Run them from the repo root:

```bash
pip install cookiecutter gitlint pydocstyle pytest
pytest tests
```
