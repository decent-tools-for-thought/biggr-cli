"""Module entry point for `python -m biggr_cli`."""

from .cli import entrypoint

if __name__ == "__main__":
    raise SystemExit(entrypoint())
