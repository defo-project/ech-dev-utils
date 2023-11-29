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

doclient="no"
allgood="yes"

run_indented() {
  local indent=${INDENT:-"    "}
  local indent_cmdline=(awk '{print "'"$indent"'" $0}')

  if [ -t 1 ] && command -v unbuffer >/dev/null 2>&1; then
    { unbuffer "$@" 2> >("${indent_cmdline[@]}" >&2); } | "${indent_cmdline[@]}"
  else
    { "$@" 2> >("${indent_cmdline[@]}" >&2); } | "${indent_cmdline[@]}"
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
mkdir -p $RUNTOP/lighttpd/baz
mkdir -p $HLOGDIR

if [ ! -f $HLOGFILE ]
then
    touch $HLOGFILE
    chmod a+w $HLOGFILE
fi

# check for/make a home page for example.com and other virtual hosts
if [ ! -f $RUNTOP/lighttpd/www/index.html ]
then
    cat >$RUNTOP/lighttpd/www/index.html <<EOF

<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>Lighttpd top page.</title>
</head>
<!-- Background white, links blue (unvisited), navy (visited), red
(active) -->
<body bgcolor="#FFFFFF" text="#000000" link="#0000FF"
vlink="#000080" alink="#FF0000">
<p>This is the pretty dumb top page for testing. </p>

</body>
</html>

EOF
fi

# check for/make a slightly different home page for baz.example.com
if [ ! -f $RUNTOP/lighttpd/baz/index.html ]
then
    cat >$RUNTOP/lighttpd/baz/index.html <<EOF

<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>Lighttpd top page.</title>
</head>
<!-- Background white, links blue (unvisited), navy (visited), red
(active) -->
<body bgcolor="#FFFFFF" text="#000000" link="#0000FF"
vlink="#000080" alink="#FF0000">
<p>This is the pretty dumb top page for baz.example.com testing. </p>

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
echo "Executing: $VALGRIND $HAPPY/haproxy -f $EDTOP/configs/haproxymin.conf $HAPDEBUGSTR 2>$HLOGFILE"
$VALGRIND $HAPPY/haproxy -f $EDTOP/configs/haproxymin.conf $HAPDEBUGSTR 2>$HLOGFILE

if [[ "$doclient" == "yes" ]]
then
    echo "Doing client calls..."
    # Uncomment for loadsa logging...
    # clilog=" -d "
    for port in 7443 7444 7445 7446 
    do
        # do GREASEy case
        echo "Testing port $port"
        INDENT="  " run_indented echo "GREASEing"
        run_indented echo "$CODETOP/esnistuff/echcli.sh $clilog -gn -p $port -c example.com -s localhost -f index.html"
        run_indented $EDTOP/scripts/echcli.sh $clilog -gn -p $port -c example.com -s localhost -f index.html
        res=$?
        if [[ "$res" != "0" ]]
        then
            run_indented echo "GREASEing failed - exiting"
            allgood="no"
            break
        fi
        # do real ECH case
        INDENT="  " run_indented echo "Real ECH"
        run_indented echo "$EDTOP/scripts/echcli.sh $clilog -s localhost -H foo.example.com -p $port -P $ECHCONFIG -f index.html -N "
        run_indented $EDTOP/scripts/echcli.sh $clilog -s localhost -H foo.example.com -p $port -P $ECHCONFIG -f index.html -N
        res=$?
        if [[ "$res" != "0" ]]
        then
            run_indented echo "Real ECH failed - exiting"
            allgood="no"
            break
        fi
    done
fi
if [[ "$allgood" == "yes" ]]
then
    echo "All good."
else
    echo "Something failed."
fi
