# Contributing to Matibhrom

Thank you for contributing to the Matibhrom Bengali LLM Hallucination Experiment Platform! This document outlines the contribution workflow and standards.

## Branch Naming

All branches must follow one of these prefixes:

- `feat/` — New features or enhancements
- `fix/` — Bug fixes
- `data/` — Data updates (benchmark, evidence, corpus)
- `exp/` — Experimental changes
- `docs/` — Documentation updates
- `refactor/` — Code refactoring without behavior changes
- `test/` — Test additions or modifications
- `ci/` — CI/CD changes

Examples:
- `feat/add-annotation-ui`
- `fix/cache-invalidation`
- `data/add-medical-distractors`
- `exp/new-prompt-template`

## Pull Request Template

All PRs must include:

1. **What changed** — Summary of the changes
2. **Why** — Motivation and context
3. **Tests added** — List of new/modified tests
4. **DECISIONS.md updated?** — Yes/No with reference to decision

### Special Requirements

- **Prompt templates, schemas, lock files:** Require **two approvals** from team members
- **Data PRs:** Must include a successful `validate_data.py` run recorded in the PR description
- **No direct commits to `main`** — All changes via PR
- **No commits to `outputs/`** — This directory is gitignored

## Development Setup

```bash
# 1. Clone and create virtual environment
python -m venv .venv
source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements-cpu.txt

# 3. Copy environment template
cp .env.example .env
# Edit .env with your API keys

# 4. Validate dummy data
python -m src.validate_data --items data/dummy/items.jsonl --evidence data/dummy/evidence.jsonl --corpus data/dummy/corpus.jsonl

# 5. Run tests
pytest --cov=src --cov-fail-under=80

# 6. Dry run on dev split
python -m src.runner.run --config configs/experiments.yaml --split dev --limit 5 --check-budget
```

## Code Standards

### Python

- **Version:** Python 3.11
- **Formatting:** Black (line length 88)
- **Linting:** Ruff
- **Type hints:** Required on all public functions
- **Docstrings:** Google-style for public functions and classes

### Configuration

- **Config files:** YAML with OmegaConf
- **Environment variables:** Never commit `.env` files
- **Secrets:** Use `.env` (gitignored) or secret manager

### Testing

- **Framework:** pytest
- **Coverage target:** ≥ 80% branch coverage on runner/, cache/, locks/, io_atomic/, validate_data/
- **Test data:** Use `data/dummy/` — tests must pass without network or GPU
- **Negative tests:** Include in `tests/test_negative_cases.py`

## Data Changes

When modifying benchmark data (`data/benchmark/`):

1. Run validation: `python -m src.validate_data --items ... --evidence ... --corpus ...`
2. Record validation output in PR
3. If domain counts change, update spec and validation rules
4. Bump `SCHEMA_VERSION` in `src/schema_version.py` for breaking changes
5. Bump `CODEBOOK_VERSION` for annotation taxonomy changes

## Lock Files

When freezing a run:
1. Lock files are automatically created in `outputs/{run_id}/locks/`
2. Copied to repo root `locks/` for CI visibility
3. Any change after lock requires a new `run_id`

## Release Process

1. Update version in `pyproject.toml`
2. Run full test suite: `pytest`
3. Validate benchmark: `python -m src.validate_data ...`
4. Create PR with version bump
5. Merge after approvals
6. Tag release: `git tag v1.x.x`

## Contact

- **Team:** Turtlers (Akib, Jaef, Sabit)
- **Supervisor:** S M Asif Hossain
- **Lab:** ELITE Research Lab LLC

---

*This document is part of the Matibhrom specification. All deviations must be recorded in DECISIONS.md.*