Release Checklist
-----------------

1. Switch to the master branch and stash any uncommited changes.
2. Bump the version number in [rtv/\_\_version\_\_.py](rtv/__version__.py).
3. Update the release notes in the [CHANGELOG.rst](CHANGELOG.rst).
4. Update the contributor list by running [``scripts/build_authors.py``](scripts/build_authors.py).
5. Re-generate the manpage by running [``scripts/build_manpage.py``](scripts/build_manpage.py).
6. Make sure the bundled packages are up-to-date by running [``scripts/update_packages.py``](scripts/update_packages.py).
7. Commit all changes to the master branch.
8. Clean out any old build/release files by running [``scripts/pip_clean.py``](scripts/pip_clean.py).
9. Build the source tarball and binary wheel: ``$ python3 setup.py sdist bdist_wheel``
10. Upload the packages to PyPI: ``$ twine upload dist/*``
11. Verify that the upload was successful: ``$ pip install rtv --upgrade --force-reinstall``
12. Smoke test the new release on Python 2 and Python 3.
12. Create a new release on Github and copy the release notes from the changelog.
13. Use Github to delete any old branches that have been merged.

Packaging Guide
---------------

The most up-to-date and pragmatic guide on packaging for PyPI is given here (as of Fall 2017):

https://packaging.python.org/tutorials/distributing-packages/

PyPI Credentials
----------------

PyPI credentials are stored in plaintext in the **~/.pypirc** file.

```
[pypi]
username = michael-lazar
password = secret
```
