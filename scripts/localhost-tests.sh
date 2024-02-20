#!/bin/bash

# set -ex
set -e

# A couple of basic openssl ECH tests
# we assume we're in the root of a checked out ech-dev-utils repo

# Override-able paths
: ${EDTOP:="$HOME/code/ech-dev-utils"}
: ${CODETOP:=$HOME/code/openssl}
if [[ "$PACKAGING" == "" ]]
then
    export LD_LIBRARY_PATH=$CODETOP
    CMDPATH=$CODETOP/apps/openssl
else
    CMDPATH=`which openssl`
    EDTOP="."
fi

# basic ECH check vs. defo.ie
$EDTOP/scripts/echcli.sh -d -H defo.ie -f ech-check.php

if [ ! -d cadir ]
then
    # don't re-do this if not needed, might break other configs
    $EDTOP/scripts/make-example-ca.sh
fi
if [ ! -f echconfig.pem ]
then
    $CMDPATH ech -public_name example.com || true
fi

$EDTOP/scripts/echsvr.sh &
$EDTOP/scripts/echcli.sh -s localhost -H foo.example.com -p 8443 -P echconfig.pem -f index.html

$EDTOP/scripts/echcli.sh -H foo.example.com -p 8443 -s localhost -P echconfig.pem -S ed.sess
ls -l ed.sess
$EDTOP/scripts/echcli.sh -H foo.example.com -p 8443 -s localhost -P echconfig.pem -S ed.sess -e
rm ed.sess
if [[ "$PACKAGING" == "" ]]
then
    ECHSVR=`ps -ef | grep "openssl s_server" | grep -v grep | awk '{print $2}'`
    if [[ "$ECHSVR" != "" ]]
    then
        kill $ECHSVR
    fi
fi

