# Claude Code Memory

## Repository Information
- **Repository**: albertocavalcante/sapo
- **GitHub URL**: https://github.com/albertocavalcante/sapo
- **Main branch**: main
- **Current working branch**: main

## Git Remotes
- **origin**: https://github.com/albertocavalcante/sapo.git (primary working repo)

## GitHub CLI Commands
When creating PRs, use: `gh pr create --repo albertocavalcante/sapo`

## Project Commands
- **Package Manager**: Poetry (use `poetry add` not `pip install`)
- **Linting**: `poetry run ruff check --fix`
- **Formatting**: `poetry run ruff format` 
- **Type checking**: `poetry run mypy sapo/`
- **Testing**: `poetry run pytest`

## Important Notes
- **USE POETRY NOT PIP**: Always use `poetry add` instead of `pip install`
- Always run `poetry run ruff check --fix` and `poetry run ruff format` before committing
- Never use `git add .` - stage specific files only
- Validator framework tests completed (56 tests added)
- Recent work: Added comprehensive unit tests for validator framework, removed rocket emojis