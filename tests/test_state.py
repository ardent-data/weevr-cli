"""Tests for AppState, including lazy credential initialization."""

from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from weevr_cli.state import _AUTH_HINT, AppState, AuthError


class TestCredentialProperty:
    @patch("azure.identity.DefaultAzureCredential")
    def test_lazy_creates_credential(self, mock_cred_cls: MagicMock) -> None:
        state = AppState(console=Console(), config=None, json_mode=False)
        cred = state.credential
        mock_cred_cls.assert_called_once()
        assert cred is mock_cred_cls.return_value

    @patch("azure.identity.DefaultAzureCredential")
    def test_caches_credential(self, mock_cred_cls: MagicMock) -> None:
        state = AppState(console=Console(), config=None, json_mode=False)
        cred1 = state.credential
        cred2 = state.credential
        assert cred1 is cred2
        mock_cred_cls.assert_called_once()

    @patch(
        "azure.identity.DefaultAzureCredential",
        side_effect=Exception("no creds"),
    )
    def test_raises_auth_error_with_hints(self, _mock: MagicMock) -> None:
        state = AppState(console=Console(), config=None, json_mode=False)
        with pytest.raises(AuthError, match="az login") as exc_info:
            _ = state.credential
        msg = str(exc_info.value)
        assert "AZURE_CLIENT_ID" in msg
        assert "managed identity" in msg
        assert "no creds" in msg


class TestAuthHint:
    def test_hint_contains_all_methods(self) -> None:
        assert "az login" in _AUTH_HINT
        assert "AZURE_CLIENT_ID" in _AUTH_HINT
        assert "managed identity" in _AUTH_HINT
