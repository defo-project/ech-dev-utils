#!/bin/bash

# Run a lighttpd on localhost:3443 with foo.example.com accessible
# via ECH

# set -x
set -e

# to pick up correct executables and .so's
: ${CODETOP:=$HOME/code/openssl}
export LD_LIBRARY_PATH=$CODETOP
: ${EDTOP:=$HOME/code/ech-dev-utils}
: ${RUNTOP:=`/bin/pwd`}
export RUNTOP=$RUNTOP
: ${LIGHTY:=$HOME/code/lighttpd1.4}

if [[ "$PACKAGING" != "" ]]
then
    EDTOP="$(dirname "$(realpath "$0")")/.."
    RUNTOP=`mktemp -d`
fi

PIDFILE=$RUNTOP/lighttpd/logs/lighttpd.pid
CLILOGFILE=`mktemp`
SRVLOGFILE=`mktemp`
KEEPLOG="no"

allgood="yes"

export TOP=$CODETOP

export LD_LIBRARY_PATH=$CODETOP

. $EDTOP/scripts/funcs.sh

prep_server_dirs lighttpd

lighty_stop
lighty_start $EDTOP/configs/lighttpdmin.conf

for type in grease public real hrr
do
    port=3443
    echo "Testing $type $port"
    cli_test $port $type
done

lighty_stop

if [[ "$allgood" == "yes" ]]
then
    echo "All good."
    rm -f $CLILOGFILE $SRVLOGFILE
else
    echo "Something failed."
    if [[ "$KEEPLOG" != "no" ]]
    then
        echo "Client logs in $CLILOGFILE"
        echo "Server logs in $SRVLOGFILE"
    else
        rm -f $CLILOGFILE $SRVLOGFILE
    fi
fi

