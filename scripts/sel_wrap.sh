#!/bin/bash

# set -x

: ${BROWSER:="firefox"}
: ${URLSFILE="/var/extra/urls_to_test.csv"}
: ${RESULTS_DIR="/var/extra/smokeping/$BROWSER-runs"}

function whenisitagain()
{
    /bin/date -u +%Y%m%d-%H%M%S
}
NOW=$(whenisitagain)

echo "=============================="
echo "Running $0 at $NOW with:"
echo "    BROWSER: $BROWSER"
echo "    URLSFILE: $URLSFILE"
echo "    RESULTS_DIR: $RESULTS_DIR"

# small wrapper to run selenium in virtual env
if [[ "$BROWSER" != "chromium" ]]
then
    cd $HOME/pt
    source venv/bin/activate 
fi

python3 $HOME/code/defo-project-org/ech-dev-utils/scripts/selenium_test.py --browser="$BROWSER" --urls_to_test="$URLSFILE" --results_dir="$RESULTS_DIR"

echo "=============================="
