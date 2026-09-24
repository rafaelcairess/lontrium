"""Keep the developer configuration reference and product README trustworthy."""

import re
from pathlib import Path

import pytest

from src.core.config import env_setting_kinds

ROOT = Path(__file__).resolve().parent.parent
ENV_EXAMPLE = (ROOT / ".env.example").read_text(encoding="utf-8")
README = (ROOT / "README.md").read_text(encoding="utf-8")

# Handled by Docker/Compose rather than config.py.
DOCKER_ONLY = {
    "CLAIMER_TAG",
    "CLAIMER_CPU_LIMIT",
    "CLAIMER_MEMORY_LIMIT",
    "CLAIMER_PIDS_LIMIT",
    "CLEAN_BROWSER_CACHE_ON_STARTUP",
    "VNC_PASSWORD",
}


def _config_vars() -> list[str]:
    # config.py scans itself for this, so the runtime settings guard and these tests agree.
    return sorted(env_setting_kinds())


def _env_example_vars() -> set[str]:
    return set(re.findall(r"^#?\s*([A-Z_0-9]+)=", ENV_EXAMPLE, re.M))


class TestEverySettingIsDocumented:
    def test_the_scan_still_finds_settings(self):
        # Guards the regex itself: a rename in config.py must not empty this list.
        assert len(_config_vars()) > 60

    @pytest.mark.parametrize("name", _config_vars())
    def test_it_is_in_env_example(self, name):
        assert name in _env_example_vars(), f"{name} is missing from .env.example"

class TestNothingDocumentedThatDoesNotExist:
    def test_no_unknown_settings_in_env_example(self):
        unknown = sorted(_env_example_vars() - set(_config_vars()) - DOCKER_ONLY)
        assert not unknown, f".env.example documents settings the code does not read: {unknown}"


class TestProductReadme:
    """The landing page stays concise while detailed references remain discoverable."""

    @pytest.mark.parametrize(
        "target",
        ["./.env.example", "./MODIFICATIONS.md", "./CHANGELOG.md", "./THIRD_PARTY_NOTICES.md"],
    )
    def test_developer_reference_exists_and_is_linked(self, target):
        assert target in README
        assert (ROOT / target.removeprefix("./")).is_file()

    @pytest.mark.parametrize("translation", ["README.pt-BR.md", "README.es.md"])
    def test_translated_readme_exists_and_is_linked(self, translation):
        assert f"./docs/{translation}" in README
        assert (ROOT / "docs" / translation).is_file()

    def test_end_user_readme_does_not_duplicate_env_reference(self):
        assert "Options are set via environment variables" not in README
        assert "## Configuration" not in README
        assert not re.search(r"^\|\s*`[A-Z_0-9]+`", README, re.M)

    def test_product_promises_and_attribution_remain_visible(self):
        assert "Lontrium-Setup.exe" in README
        assert "rafaelcairess/lontrium" in README
        assert "Your data stays local" in README
        assert "P-Adamiec/Free-Games-Claimer-Remaster" in README
        assert "GNU Affero General Public License v3.0" in README
