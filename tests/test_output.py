import json

from rich.console import Console

from weevr_cli.output import create_console, print_error, print_json


def test_create_console() -> None:
    console = create_console()
    assert isinstance(console, Console)


def test_create_console_json_mode() -> None:
    console = create_console(json_mode=True)
    assert isinstance(console, Console)
    assert console.quiet


def test_print_json_success(capsys: object) -> None:
    import _pytest.capture

    assert isinstance(capsys, _pytest.capture.CaptureFixture)
    print_json({"version": "0.1.0"})
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data == {"version": "0.1.0"}


def test_print_json_error(capsys: object) -> None:
    import _pytest.capture

    assert isinstance(capsys, _pytest.capture.CaptureFixture)
    print_error("Something broke", "unknown_error", json_mode=True)
    captured = capsys.readouterr()
    data = json.loads(captured.err)
    assert data["error"] == "Something broke"
    assert data["code"] == "unknown_error"


def test_print_error_rich(capsys: object) -> None:
    import _pytest.capture

    assert isinstance(capsys, _pytest.capture.CaptureFixture)
    console = create_console(json_mode=False)
    print_error("Something broke", "unknown_error", json_mode=False, console=console)
    captured = capsys.readouterr()
    assert "Something broke" in captured.err
