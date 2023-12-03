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
# default ECH key pair
: ${ECHCONFIG:="echconfig.pem"}

export LD_LIBRARY_PATH=$CODETOP

HLOGDIR="$RUNTOP/haproxy/logs"
HLOGFILE="$HLOGDIR/haproxy.log"
CLILOGFILE="$HLOGDIR/clienttest.log"

doclient="no"
allgood="yes"

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
        gorp="-P echconfig.pem"
    else
        echo "bad cli_test parameter $runparm, exiting"
        exit 99
    fi
    $EDTOP/scripts/echcli.sh $clilog $gorp -p $port -H $target -s localhost -f index.html >>$CLILOGFILE 2>&1
    lres=$?
    if [[ "$lres" != "0" ]]
    then
        echo "test failed, exiting"
        echo "command that failed: $CODETOP/esnistuff/echcli.sh $clilog $gorp-p $port -H $target -s localhost -f index.html"
        # exit $lres
        allgood="no"
    fi
}

if [[ "$1" == "client" ]]
then
    doclient="yes"
elif [[ "$1" != "" ]]
then
    echo "Unrecognised argument: $1"
    echo "usage: $0 [client]"
    exit -1
fi

# make directories for lighttpd stuff if needed
mkdir -p $RUNTOP/lighttpd/logs
mkdir -p $RUNTOP/lighttpd/www
mkdir -p $RUNTOP/lighttpd/public_name
mkdir -p $HLOGDIR

if [ ! -f $HLOGFILE ]
then
    touch $HLOGFILE
    chmod a+w $HLOGFILE
fi

# check for/make a home page for foo.example.com and other virtual hosts
if [ ! -f $RUNTOP/lighttpd/www/index.html ]
then
    cat >$RUNTOP/lighttpd/www/index.html <<EOF

<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>Lighttpd foo.example.com top page.</title>
</head>
<!-- Background white, links blue (unvisited), navy (visited), red
(active) -->
<body bgcolor="#FFFFFF" text="#000000" link="#0000FF"
vlink="#000080" alink="#FF0000">
<p>This is the pretty dumb top page for foo.example.com </p>

</body>
</html>

EOF
fi

# check for/make a slightly different home page for public_name/example.com
if [ ! -f $RUNTOP/lighttpd/public_name/index.html ]
then
    cat >$RUNTOP/lighttpd/public_name/index.html <<EOF

<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>Lighttpd public_name page.</title>
</head>
<!-- Background white, links blue (unvisited), navy (visited), red
(active) -->
<body bgcolor="#FFFFFF" text="#000000" link="#0000FF"
vlink="#000080" alink="#FF0000">
<p>This is the pretty dumb top page for public_name/example.com </p>

</body>
</html>

EOF
fi

# set to run in foreground or as daemon -D => foreground
# unset =>daemon
# FOREGROUND="-D "

# set to use valgrind, unset to not
# VALGRIND="valgrind --leak-check=full --show-leak-kinds=all"
#VALGRIND="valgrind --leak-check=full --error-limit=1 --track-origins=yes"
VALGRIND=""

# Check if a lighttpd is running
lrunning=`ps -ef | grep lighttpd | grep -v grep | grep -v tail`

if [[ "$lrunning" == "" ]]
then
    export LIGHTYTOP=$RUNTOP
    echo "Executing: $VALGRIND $LIGHTY/src/lighttpd $FOREGROUND -f $EDTOP/configs/lighttpd4haproxymin.conf -m $LIGHTY/src/.libs"
    $LIGHTY/src/lighttpd $FOREGROUND -f $EDTOP/configs/lighttpd4haproxymin.conf -m $LIGHTY/src/.libs
else
    echo "Lighttpd already running."
    echo "$lrunning"
fi

# Check we have a back-end
lrunning=`ps -ef | grep lighttpd | grep -v grep | grep -v tail`
if [[ "$lrunning" == "" ]]
then
    echo "No back-end running, sorry - exiting"
    exit 1
fi

HAPDEBUGSTR=" -dV " 
if [[ "$doclient" == "yes" ]]
then
    # run server in background
    HAPDEBUGSTR=" -DdV " 
    # Kill any earlier haproxy running
    killall haproxy
fi

# Now start up a haproxy
echo "Executing: $VALGRIND $HAPPY/haproxy -f $EDTOP/configs/haproxymin.conf $HAPDEBUGSTR >$HLOGFILE 2>&1"
$VALGRIND $HAPPY/haproxy -f $EDTOP/configs/haproxymin.conf $HAPDEBUGSTR >$HLOGFILE 2>&1

if [[ "$doclient" == "yes" ]]
then
    # all things should appear the same to the client
    # server log checks will tells us if stuff worked or not
    echo "Doing client calls..."
    for type in grease public real hrr
    do
        for port in 7443 7444 7445 7446 
        do
            echo "Testing $type $port"
            cli_test $port $type
        done
    done
fi
if [[ "$allgood" == "yes" ]]
then
    echo "All good."
else
    echo "Something failed."
fi
