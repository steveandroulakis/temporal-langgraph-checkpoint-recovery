"""Nox configuration for automated testing and linting."""

import nox


@nox.session(python=["3.11", "3.12"])
def tests(session: nox.Session) -> None:
    """Run the test suite."""
    session.install("-e", ".[dev]")
    session.run("pytest", "tests/", "-v")


@nox.session
def lint(session: nox.Session) -> None:
    """Run ruff for linting."""
    session.install("ruff")
    session.run("ruff", "check", ".")


@nox.session
def format(session: nox.Session) -> None:
    """Run ruff for formatting."""
    session.install("ruff")
    session.run("ruff", "format", ".")


@nox.session
def format_check(session: nox.Session) -> None:
    """Check ruff formatting without making changes."""
    session.install("ruff")
    session.run("ruff", "format", "--check", ".")


@nox.session
def typecheck(session: nox.Session) -> None:
    """Run mypy for type checking."""
    session.install("-e", ".[dev]")
    session.run("mypy", "order_fulfillment/", "scripts/")


@nox.session
def pre_commit(session: nox.Session) -> None:
    """Run all pre-commit checks."""
    session.install("-e", ".[dev]")
    session.run("ruff", "check", ".")
    session.run("ruff", "format", "--check", ".")
    session.run("mypy", "order_fulfillment/", "scripts/")
    session.run("pytest", "tests/", "-v")
