#!/usr/bin/env bash
# Removes any lingering build/release files from the project directory

find . -type f -name '*.pyc' -delete
find . -type f -name '*.pyo' -delete
find . -type d -name '__pycache__' -delete
find . -type d -name 'build' -delete
find . -type d -name 'dist' -delete
find . -type d -name '*.egg-info' -delete
