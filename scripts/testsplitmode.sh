#!/bin/bash

# set -x

# to pick up correct executables and .so's
: ${CODETOP:="$HOME/code/defo-project-org/openssl"}
: ${EDTOP:="$HOME/code/ech-dev-utils"}
# where we have/want test files
: ${RUNTOP:=`/bin/pwd`}
export RUNTOP=$RUNTOP
# where back-end web server can be found
: ${LIGHTY:="$HOME/code/lighttpd1.4-upstream-clean"}
# where front-end haproxy can be found
: ${HAPPY:="$HOME/code/defo-project-org/haproxy"}
# where front-end nginx can be found
: ${NTOP:="$HOME/code/nginx"}
export LD_LIBRARY_PATH=$CODETOP:$LIGHTY/src/.libs

allgood="yes"

. $EDTOP/scripts/funcs.sh

NOW=$(whenisitagain)
# in case we wanna dump core and get a backtrace, make a place for
# that (dir name is also in configs/nginxmin.conf)
mkdir -p /tmp/cores
HLOGDIR="$RUNTOP/haproxy/logs"
HLOGFILE="$HLOGDIR/haproxy.log"
CLILOGFILE=`mktemp`
SRVLOGFILE=`mktemp`

TECH=$1

# some preliminaries - ensure directories exist, kill old servers
prep_server_dirs $TECH

FE_PIDFILE=$RUNTOP/$TECH/logs/$TECH.pid
# Kill off old processes from the last test
if [ -f $FE_PIDFILE ]
then
    echo "Killing old $TECH in process `cat $FE_PIDFILE`"
    kill `cat $FE_PIDFILE`
    rm -f $FE_PIDFILE
fi

if [[ "$TECH" == "nginx" ]]
then
    # nginx specific: if we don't have a local config belor RUNTOP, replace
    # pathnames in repo version and copy to where it's needed
    if [ ! -f $RUNTOP/nginx/nginxsplit.conf ]
    then
        do_envsubst
    fi
    # if the repo version of the config is newer, then backup the RUNTOP
    # version and re-run envsubst
    repo_date=`stat -c %Y $EDTOP/configs/nginxsplit.conf`
    runtop_date=`stat -c %Y $RUNTOP/nginx/nginxsplit.conf`
    if (( repo_date >= runtop_date))
    then
        cp $RUNTOP/nginx/nginxsplit.conf $RUNTOP/nginx/nginxsplit.conf.$NOW
        do_envsubst
    fi
fi

if [[ "$TECH" == "nginx" ]]
then
    echo "Executing: $NTOP/objs/nginx -c nginxsplit.conf"
    $NTOP/objs/nginx -c nginxsplit.conf
elif [[ "$TECH" == "haproxy" ]]
then
    HAPDEBUGSTR=" -DdV" 
    echo "Executing: $HAPPY/haproxy -f $EDTOP/configs/haproxymin.conf $HAPDEBUGSTR >>$HLOGFILE 2>&1"
    $HAPPY/haproxy -f $EDTOP/configs/haproxymin.conf $HAPDEBUGSTR >>$HLOGFILE 2>&1
else
    echo "Unknown tech: $TECH -exiting"
    exit 77
fi

# start a backend
PIDFILE=$RUNTOP/lighttpd/logs/lighttpd.pid
lighty_start $EDTOP/configs/lighttpdsplit.conf

SKIPEM="no"
if [[ "$SKIPEM" != "yes" ]]
then

# all these should appear the same to the client
# server log checks will tell us if stuff worked or not
echo "Doing split-mode tests..."
for type in grease public real hrr
do
    for port in 7443 7444 7445 7446 
    do
        echo "Testing $type $port"
        cli_test $port $type
    done
done

fi # end of SKIPEM

# need special stuff for early_data as lighty doesn't support that
echo "Doing early data tests"
# lighttpd doesn't support early data so we need to swap over to
# s_server
lighty_stop

# we wanna try with and without hitting hrr
for type in nohrr hrr
do
    port=7446
    echo "Testing $type $port"
    s_server_start $type
    sleep 3
    # connect twice, 2nd time using resumption and sending early data
    session_ticket_file=`mktemp`
    rm -f $session_ticket_file
    $EDTOP/scripts/echcli.sh -H foo.example.com -s localhost -p $port -P $RUNTOP/echconfig.pem -f index.html -S $session_ticket_file >>$CLILOGFILE 2>&1
    if [ ! -f $session_ticket_file ]
    then
        # s_server_stop
        echo "No session, so can't try early data - skipping $type $port"
        allgood="no"
        break
    fi
    $EDTOP/scripts/echcli.sh -H foo.example.com -s localhost -p $port -P $RUNTOP/echconfig.pem -f index.html -S $session_ticket_file -e >>$CLILOGFILE 2>&1
    rm -f $session_ticket_file
    res=$?
    if [[ "$res" != "0" ]]
    then
        echo "Early-data+split-mode test failed (with-HRR: $HRR)"
        allgood="no"
    fi
    s_server_stop
done


if [[ "$allgood" == "yes" ]]
then
    echo "All good."
    rm -f $CLILOGFILE $SRVLOGFILE
else
    echo "Something failed."
    mv $CLILOGFILE $RUNTOP/$TECH/logs/cli.log
    mv $SRVLOGFILE $RUNTOP/$TECH/logs/srv.log
fi

# Kill off processes from this test
killall $TECH
rm -f $FE_PIDFILE $PIDFILE

