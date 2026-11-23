"""The settings, tools and targets from board.toml."""

import tomllib
from dataclasses import dataclass
from pathlib import Path

from stealth_board.check import find_problems


@dataclass(frozen=True)
class Tool:
    name: str
    modes: tuple[str, ...]
    control: bool = False


@dataclass(frozen=True)
class Target:
    id: str
    name: str
    kind: str
    vendor: str
    url: str
    expect: str
    reject: str | None = None

    @property
    def is_scored(self):
        """Open pages have no protection, so they do not count for the score."""
        return self.kind != "open"


@dataclass(frozen=True)
class Config:
    tries: int
    timeout: int
    click: bool
    tools: tuple[Tool, ...]
    targets: tuple[Target, ...]


class ConfigError(Exception):
    """The config file has problems. The message lists them."""


def load_config(path, adapters_dir):
    raw = tomllib.loads(Path(path).read_text())
    problems = find_problems(raw, adapters_dir)
    if problems:
        raise ConfigError("The config has problems:\n  " + "\n  ".join(problems))
    return Config(
        tries=raw["tries"],
        timeout=raw["timeout"],
        click=raw["click"],
        tools=tuple(Tool(**{**tool, "modes": tuple(tool["modes"])}) for tool in raw["tool"]),
        targets=tuple(Target(**target) for target in raw["target"]),
    )
