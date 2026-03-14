from importlib import import_module


def test_package_exposes_project_metadata() -> None:
    package = import_module("observer_rock")

    assert package.__app_name__ == "observer-rock"
    assert package.__version__ == "0.1.0"
