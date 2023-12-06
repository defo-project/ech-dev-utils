#!/bin/bash

# set -x

# Run a haproxy test

# to pick up correct .so's - maybe note 
: ${CODETOP:="$HOME/code/openssl"}
# to pick up correct wrapper scripts
: ${EDTOP:="$HOME/code/ech-dev-utils"}
# to set where our cadir and ECH keys are
: ${RUNTOP:="$HOME/lt"}
# where back-end web server can be found
: ${LIGHTY:="$HOME/code/lighttpd1.4"}
# where front-end haproxy can be found
: ${HAPPY:="$HOME/code/haproxy"}

export LD_LIBRARY_PATH=$CODETOP

HLOGDIR="$RUNTOP/haproxy/logs"
SRVLOGFILE="$HLOGDIR/haproxy.log"
CLILOGFILE="$HLOGDIR/clienttest.log"
PIDFILE="$RUNTOP/haproxy/logs/haproxy.pid"
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

lighty_start $EDTOP/configs/lighttpd4haproxymin.conf

killall haproxy

# Now start up a haproxy
# run haproxy in background
HAPDEBUGSTR=" -DdV " 
echo "Executing: $HAPPY/haproxy -f $EDTOP/configs/haproxymin.conf $HAPDEBUGSTR >$SRVLOGFILE 2>&1"
$HAPPY/haproxy -f $EDTOP/configs/haproxymin.conf $HAPDEBUGSTR >$SRVLOGFILE 2>&1

# all things should appear the same to the client
# server log checks will tells us if stuff worked or not
echo "Doing shared-mode client calls..."
for type in grease public real hrr
do
    for port in 7443 7444 7445
    do
        echo "Testing $type $port"
        cli_test $port $type
    done
done

killall haproxy lighttpd
rm -f $PIDFILE

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

