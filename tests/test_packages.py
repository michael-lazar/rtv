from rtv import packages


def test_praw3_package():
    # Sanity check that the package was installed
    assert packages.praw
    assert len(packages.__praw_hash__) == 40
    assert packages.__praw_bundled__ is True
