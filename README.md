# Basketball-DA

## Setup

This project uses Python 3.14 and `uv` to manage its virtual environment and dependencies.

### Install uv

Follow the [official uv installation guide](https://docs.astral.sh/uv/getting-started/installation/) for instructions for your operating system.

### Set up the environment

Clone the repository and enter the project directory:

```bash
git clone https://github.com/MmahdiM79/Basketball-DA.git
cd Basketball-DA
```

Run this command for the initial setup and after each `git pull`:

```bash
uv sync --locked
```

This downloads Python 3.14 if needed, creates the `.venv` virtual environment, and installs the dependency versions recorded in `uv.lock`.

Use `uv run python` followed by a script path to run a Python file in this environment. To check the environment's Python version:

```bash
uv run python --version
```

### Add dependencies

The `dependencies` list in `pyproject.toml` is currently empty. To add a package, replace `PACKAGE_NAME` with its name:

```bash
uv add PACKAGE_NAME
```

This updates `pyproject.toml` and `uv.lock` and installs the package. Commit both files so everyone can install the same dependency versions with `uv sync --locked`. The `.venv` directory is ignored by Git.
