# tests/unit/test_quick_usage_smoke.py
# Smoke test: ensure quick usage helper renders w/ no error

from src.ui.quick.quick_usage import show_quick_usage


# * verify quick usage prints recognizable blurb
def test_show_quick_usage_smoke(capsys):
    # should not raise & should print a small blurb
    show_quick_usage()
    captured = capsys.readouterr()
    # look for recognizable phrases rendered by rich -> stdout
    assert "Quick usage" in captured.out or "Quick usage" in captured.err
    assert "loom --help" in captured.out or "loom --help" in captured.err
