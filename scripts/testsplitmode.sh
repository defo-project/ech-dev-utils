#!/bin/bash

# set -x

# to pick up correct executables and .so's
: ${CODETOP:=$HOME/code/openssl}
export LD_LIBRARY_PATH=$CODETOP
: ${EDTOP:=$HOME/code/ech-dev-utils}
# where we have/want test files
: ${RUNTOP:=`/bin/pwd`}
export RUNTOP=$RUNTOP
# where back-end web server can be found
: ${LIGHTY:="$HOME/code/lighttpd1.4"}
# where front-end haproxy can be found
: ${HAPPY:="$HOME/code/haproxy"}
# where front-end nginx can be found
: ${NTOP:=$HOME/code/nginx}
# default ECH key pair
: ${ECHCONFIG:="echconfig.pem"}

allgood="yes"

function whenisitagain()
{
    /bin/date -u +%Y%m%d-%H%M%S
}

cli_test() {
    local port=$1
    local runparm=$2
    local target="foo.example.com"
    local lres="0"
    local gorp="-g "

    if [[ "$runparm" == "public" ]]
    then
        gorp="-g "
        target="example.com"
    elif [[ "$runparm" == "grease" ]]
    then
        gorp="-g "
    elif [[ "$runparm" == "hrr" ]]
    then
        gorp="-P echconfig.pem -R "
    elif [[ "$runparm" == "real" ]]
    then
        gorp="-P echconfig.pem "
    else
        echo "bad cli_test parameter $runparm, exiting"
        exit 99
    fi
    $EDTOP/scripts/echcli.sh $clilog $gorp -p $port -H $target $DPARM -s localhost -f index.html >>$CLILOGFILE 2>&1
    lres=$?
    if [[ "$lres" != "0" ]]
    then
        echo "test failed: $EDTOP/scripts/echcli.sh $clilog $gorp-p $port -H $target $DPARM -s localhost -f index.html"
        # exit $lres
        allgood="no"
    fi
}

# Check if a lighttpd is running, start one if not
lighty_start() {
    local lrunning=`ps -ef | grep lighttpd | grep -v grep | grep -v tail`

    if [[ "$lrunning" == "" ]]
    then
        export LIGHTYTOP=$RUNTOP
        $LIGHTY/src/lighttpd $FOREGROUND -f $EDTOP/configs/lighttpdsplit.conf -m $LIGHTY/src/.libs >>$SRVLOGFILE 2>&1
    fi
    # Check we now have a lighty running
    lrunning=`ps -ef | grep lighttpd | grep -v grep | grep -v tail`
    if [[ "$lrunning" == "" ]]
    then
        echo "No lighttpd back-end running, sorry - exiting"
        exit 14
    fi
}

lighty_stop() {
    killall lighttpd
}

s_server_start() {
    local srunning=`ps -ef | grep s_server | grep -v grep | grep -v tail | awk '{print $2}'`
    local HRR=$1

    if [[ "$srunning" == "" ]]
    then
        # ditch or keep server tracing
        if [[ "$HRR" == "hrr" ]]
        then
            $EDTOP/scripts/echsvr.sh -e -k echconfig.pem -p 3484 $DPARM -R >$SRVLOGFILE 2>&1 &
        else
            $EDTOP/scripts/echsvr.sh -e -k echconfig.pem -p 3484 $DPARM >$SRVLOGFILE 2>&1 &
        fi
        # recheck in a sec
        sleep 2
        srunning=`ps -ef | grep s_server | grep -v grep | grep -v tail | awk '{print $2}'`
        if [[ "$srunning" == "" ]]
        then
            echo "Can't start s_server exiting"
            exit 87
        fi
    fi
}

s_server_stop() {
    local srunning=`ps -ef | grep s_server | grep -v grep | grep -v tail | awk '{print $2}'`
    kill $srunning
}

# hackyery hack - prepare a nginx conf to use in localhost tests
do_envsubst() {
    cat $EDTOP/configs/nginxsplit.conf | envsubst '{$RUNTOP}' >$RUNTOP/nginx/nginxsplit.conf
}

prep_server_dirs() {
    local tech=$1

    # make directories for lighttpd stuff if needed
    mkdir -p $RUNTOP/nginx/logs

    for docroot in example.com foo.example.com
    do
        mkdir -p $RUNTOP/$tech/$docroot
        # check for/make a home page for example.com and other virtual hosts
        if [ ! -f $RUNTOP/$tech/$docroot/index.html ]
        then
            cat >$RUNTOP/$tech/$docroot/index.html <<EOF

<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>$docroot $tech top page.</title>
</head>
<!-- Background white, links blue (unvisited), navy (visited), red
(active) -->
<body bgcolor="#FFFFFF" text="#000000" link="#0000FF"
vlink="#000080" alink="#FF0000">
<p>This is the pretty dumb top page for $tech $docroot testing. </p>

</body>
</html>

EOF
        fi
    done
}

NOW=$(whenisitagain)
# in case we wanna dump core and get a backtrace, make a place for
# that (dir name is also in configs/nginxmin.conf)
mkdir -p /tmp/cores
HLOGDIR="$RUNTOP/haproxy/logs"
HLOGFILE="$HLOGDIR/haproxy.log"
CLILOGFILE=`mktemp`
SRVLOGFILE=`mktemp`
KEEPLOG="no"
# set next one to " -d " if keeping logs and verbosity desired
DPARM=" "

TECH=$1

# some preliminaries - ensure directories exist, kill old servers
for tech in nginx haproxy
do
    prep_server_dirs $tech
    # if we want to reload config then that's "graceful restart"
    PIDFILE=$RUNTOP/$tech/logs/$tech.pid
    # Kill off old processes from the last test
    if [ -f $PIDFILE ]
    then
        echo "Killing old $tech in process `cat $PIDFILE`"
        kill `cat $PIDFILE`
        rm -f $PIDFILE
    else
        echo "Can't find $PIDFILE - trying killall $tech"
        killall $tech
    fi
    # kill off other processes
    procs=`ps -ef | grep $tech | grep -v grep | grep -v testsplit | awk '{print $2}'`
    for proc in $procs
    do
        echo "Killing old $tech (from gdb maybe) in $proc"
        `ps -fp $proc`
        kill -9 $proc
    done
done

# give the n/w a chance so ports are free to use
sleep 2

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

cd $RUNTOP
if [[ "$TECH" == "nginx" ]]
then
    PIDFILE=$RUNTOP/$TECH/logs/$TECH.pid
    echo "Executing: $NTOP/objs/nginx -c nginxsplit.conf"
    $NTOP/objs/nginx -c nginxsplit.conf
elif [[ "$TECH" == "haproxy" ]]
then
    PIDFILE=$RUNTOP/$TECH/logs/$TECH.pid
    echo "Executing: $HAPPY/haproxy -f $EDTOP/configs/haproxymin.conf $HAPDEBUGSTR >>$HLOGFILE 2>&1"
    $HAPPY/haproxy -f $EDTOP/configs/haproxymin.conf $HAPDEBUGSTR >>$HLOGFILE 2>&1 &
else
    echo "Unknown tech: $TECH -exiting"
    exit 77
fi

# start a backend
lighty_start

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
    # connect twice, 2nd time using resumption and sending early data
    session_ticket_file=`mktemp`
    rm -f $session_ticket_file
    $EDTOP/scripts/echcli.sh -H foo.example.com -s localhost -p $port -P echconfig.pem $DPARM -f index.html -S $session_ticket_file >>$CLILOGFILE 2>&1
    if [ ! -f $session_ticket_file ]
    then
        echo "No session so no early data - exiting"
        exit 1
    fi
    $EDTOP/scripts/echcli.sh -H foo.example.com -s localhost -p $port -P echconfig.pem $DPARM -f index.html -S $session_ticket_file -e >>$CLILOGFILE 2>&1
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
    if [[ "$KEEPLOG" != "no" ]]
    then
        echo "Client logs in $CLILOGFILE"
        echo "Server logs in $SRVLOGFILE"
    else
        rm -f $CLILOGFILE $SRVLOGFILE
    fi
fi

# Kill off old processes from the last test
if [ -f $PIDFILE ]
then
    echo "Killing $TECH in process `cat $PIDFILE`"
    kill `cat $PIDFILE`
    rm -f $PIDFILE
else
    echo "Can't find $PIDFILE - trying killall $TECH"
    killall $TECH
fi
cd -
