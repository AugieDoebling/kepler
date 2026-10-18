#!/usr/bin/env bash

# This script is used to run the Kepler application.

# Pull the latest git changes
git pull origin main

# Backup the memory database at startup
# TODO: Implement backup logic here

# Run the Kepler application
source .venv/bin/activate
python3 main.py

# Backup the memory database at shutdown
# TODO: Implement backup logic here