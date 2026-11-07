import plantmon


def test_package_has_version_string():
    assert isinstance(plantmon.__version__, str)
