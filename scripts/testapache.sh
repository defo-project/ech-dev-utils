#!/bin/bash

set -ex

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

if [[ "$PACKAGING" == "" ]]
then
    ABIN=$ATOP/httpd
    CMDPATH=$CODETOP/apps/openssl
else
    CMDPATH=`which openssl`
    ABIN=`which apache2`
    EDTOP="$(dirname "$(realpath "$0")")/.."
    RUNTOP=`mktemp -d`
fi

. $EDTOP/scripts/funcs.sh

export RUNTOP PACKAGING

CLILOGFILE=`mktemp`
SRVLOGFILE=`mktemp`
KEEPLOG="no"

allgood="yes"

prep_server_dirs apache

# if we want to reload config then that's "graceful restart"
if [[ "$1" == "graceful" ]]
then
    echo "Telling apache to do the graceful thing"
    $ABIN -d $RUNTOP -f $EDTOP/configs/apachemin.conf -k graceful
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

echo "Executing: $ABIN -d $RUNTOP -f $EDTOP/configs/apachemin.conf"
WHACKAGING=1 $ABIN -d $RUNTOP -f $EDTOP/configs/apachemin.conf

for type in grease public real hrr
do
    port=9443
    echo "Testing $type $port"
    cli_test $port $type
done
kill `cat $PIDFILE`
rm -f $PIDFILE
