#!/bin/bash

set -e

# Run a haproxy test

# to pick up correct .so's etc
: ${CODETOP:="$HOME/code/defo-project-org/openssl"}
# to pick up correct wrapper scripts
: ${EDTOP:="$HOME/code/ech-dev-utils"}
# to set where our cadir and ECH keys are
: ${RUNTOP:="$HOME/lt"}
# where backend web server can be found
: ${LIGHTY:="$HOME/code/lighttpd1.4-upstream-clean"}
# where frontend haproxy can be found
: ${HAPPY:="$HOME/code/defo-project-org/haproxy"}


if [[ "$PACKAGING" == "" ]]
then
    HAPPYBIN=$HAPPY/haproxy
    CMDPATH=$CODETOP/apps/openssl
else
    CMDPATH=`which openssl`
    HAPPYBIN=`which haproxy`
    EDTOP="$(dirname "$(realpath "$0")")/.."
    RUNTOP=`mktemp -d`
    VERBOSE=yes
fi
export RUNTOP=$RUNTOP
export LD_LIBRARY_PATH=$CODETOP
export EDTOP=$EDTOP

HLOGDIR="$RUNTOP/haproxy/logs"
SRVLOGFILE="$HLOGDIR/haproxy.log"
CLILOGFILE="$HLOGDIR/clienttest.log"
BE_PIDFILE="$RUNTOP/haproxy/logs/haproxy.pid"
KEEPLOG="no"

allgood="yes"

. $EDTOP/scripts/funcs.sh

prep_server_dirs lighttpd

mkdir -p $HLOGDIR

if [ ! -f $SRVLOGFILE ]
then
    touch $SRVLOGFILE
    chmod a+w $SRVLOGFILE
fi

lighty_stop
if [ -s $BE_PIDFILE ]
then
    # kill `cat $BE_PIDFILE`
    rm -f $BE_PIDFILE
fi

lighty_start $EDTOP/configs/lighttpd4haproxymin.conf

# Now start up a haproxy
# run haproxy in background
cd $RUNTOP
HAPDEBUGSTR=" -DdV " 
echo "Executing: $HAPPYBIN -f $EDTOP/configs/haproxymin.conf $HAPDEBUGSTR >$SRVLOGFILE 2>&1"
$HAPPYBIN -f $EDTOP/configs/haproxymin.conf $HAPDEBUGSTR >$SRVLOGFILE 2>&1 || true
if [[ "$VERBOSE" == "yes" ]]
then
    cat $SRVLOGFILE
fi
cd -

# all things should appear the same to the client
# server log checks will tells us if stuff worked or not
echo "Doing shared-mode client calls..."
for type in grease public real hrr
do
    for port in 7443 7444 7445
    do
        echo "Testing $type $port"
        cli_test $port $type
        if [[ "$VERBOSE" == "yes" ]]
        then
            cat $CLILOGFILE
            rm -f $CLILOGFILE
        fi
    done
done


lighty_stop
if [ -s $BE_PIDFILE ]
then
    kill `cat $BE_PIDFILE`
    rm -f $BE_PIDFILE
fi

if [[ "$allgood" == "yes" ]]
then
    echo "All good."
    # rm -f $CLILOGFILE $SRVLOGFILE
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

