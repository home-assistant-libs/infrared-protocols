#!/usr/bin/env bash

# Stop on errors
set -e

uv pip install -e "."
uv pip install -e ".[dev]"
