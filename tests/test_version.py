"""Test the module version."""
from vivintpy import __version__


def test_version() -> None:
    """Test version."""
    assert __version__ == "2022.12.2"
