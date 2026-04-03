from __future__ import annotations

from importlib.metadata import EntryPoint
from unittest.mock import patch

from weevr_cli.plugins.discovery import ENTRY_POINT_GROUP, discover_entry_points


def _make_entry_point(name: str) -> EntryPoint:
    return EntryPoint(name=name, value=f"fake_{name}.cli", group=ENTRY_POINT_GROUP)


class TestDiscoverEntryPoints:
    def test_returns_sorted(self) -> None:
        eps = [_make_entry_point("zebra"), _make_entry_point("alpha"), _make_entry_point("middle")]
        with patch("weevr_cli.plugins.discovery.entry_points", return_value=eps):
            result = discover_entry_points()
        assert [ep.name for ep in result] == ["alpha", "middle", "zebra"]

    def test_no_plugins(self) -> None:
        with patch("weevr_cli.plugins.discovery.entry_points", return_value=[]):
            result = discover_entry_points()
        assert result == []
