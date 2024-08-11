#!/bin/bash

set -x

: ${BROWSER:="firefox"}
: ${URLSFILE="/var/extra/urls_to_test.csv"}
: ${RESULTS_DIR="/var/extra/smokeping/$BROWSER-runs"}

# small wrapper to run selenium in virtual env
cd $HOME/pt
source venv/bin/activate 
python $HOME/code/defo-project-org/ech-dev-utils/scripts/selenium_test.py --browser="$BROWSER" --urls_to_test="$URLSFILE" --results_dir="$RESULTS_DIR"

