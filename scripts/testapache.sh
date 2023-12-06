#!/bin/bash

# set -x

# to pick up correct executables and .so's
: ${CODETOP:=$HOME/code/openssl}
export LD_LIBRARY_PATH=$CODETOP
: ${EDTOP:=$HOME/code/ech-dev-utils}
# Note that the value for this has to match that for ATOP
# in apachemin.conf, so if you change this on the
# command line, you'll need to edit the conf file
: ${ATOP:=$HOME/code/httpd}
# where we have/want test files
: ${RUNTOP:=`/bin/pwd`}

. $EDTOP/scripts/funcs.sh

CLILOGFILE=`mktemp`
SRVLOGFILE=`mktemp`
KEEPLOG="no"

allgood="yes"

prep_server_dirs apache

# if we want to reload config then that's "graceful restart"
if [[ "$1" == "graceful" ]]
then
    echo "Telling apache to do the graceful thing"
    $ATOP/httpd -d $RUNTOP -f $EDTOP/configs/apachemin.conf -k graceful
    exit $?
fi

PIDFILE=$RUNTOP/apache/logs/httpd.pid
# Kill off old processes from the last test
if [ -f $PIDFILE ]
then
    echo "Killing old httpd in process `cat $PIDFILE`"
    kill `cat $PIDFILE`
    rm -f $PIDFILE
fi
# just in case:-)
killall httpd

echo "Executing: $ATOP/httpd -d $RUNTOP -f $EDTOP/configs/apachemin.conf"
$ATOP/httpd -d $RUNTOP -f $EDTOP/configs/apachemin.conf

for type in grease public real hrr
do
    port=9443
    echo "Testing $type $port"
    cli_test $port $type
done

killall httpd
rm -f $PIDFILE
