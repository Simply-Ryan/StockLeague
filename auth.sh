#!/bin/bash

# Clear the invalid token
unset GITHUB_TOKEN
export GITHUB_TOKEN=""

# Now try gh login
gh auth login
