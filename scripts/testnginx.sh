#!/bin/bash 

set -x
# set -e

# to pick up correct executables and .so's
: ${CODETOP:=$HOME/code/openssl}
export LD_LIBRARY_PATH=$CODETOP
: ${EDTOP:=$HOME/code/ech-dev-utils}
: ${NTOP:=$HOME/code/nginx}
# where we have/want test files
: ${RUNTOP:=`/bin/pwd`}
export RUNTOP=$RUNTOP
: ${VERBOSE:="no"}

if [[ "$PACKAGING" == "" ]]
then
    NBIN=$NTOP/objs/nginx
    CMDPATH=$CODETOP/apps/openssl
else
    CMDPATH=`which openssl`
    NBIN=`which nginx`
    EDTOP="$(dirname "$(realpath "$0")")/.."
    RUNTOP=`mktemp -d`
fi

# in case we wanna dump core and get a backtrace, make a place for
# that (dir name is also in configs/nginxmin.conf)
mkdir -p /tmp/cores

allgood="yes"

function whenisitagain()
{
    /bin/date -u +%Y%m%d-%H%M%S
}
NOW=$(whenisitagain)

CLILOGFILE=`mktemp`
SRVLOGFILE=`mktemp`
KEEPLOG="no"
EARLY="yes"
SPLIT="no"

. $EDTOP/scripts/funcs.sh

prep_server_dirs nginx

# if we want to reload config then that's "graceful restart"
PIDFILE=$RUNTOP/nginx/logs/nginx.pid
if [[ "$1" == "graceful" ]]
then
    echo "Telling nginx to do the graceful thing"
    if [ -f $PIDFILE ]
    then
        # sending sighup to the process reloads the config
        kill -SIGHUP `cat $PIDFILE`
        exit $?
    fi
fi

# Kill off old processes from the last test
if [ -f $PIDFILE ]
then
    echo "Killing old nginx in process `cat $PIDFILE`"
    kill `cat $PIDFILE`
    rm -f $PIDFILE
fi

# if starting afresh check if some process was left over after gdb or something

# kill off other processes (don't bother if PACKAGING)

if [[ "$PACKAGING" == "" ]]
then
    procs=`ps -ef | grep nginx | grep -v grep | grep -v testnginx | awk '{print $2}'`
    for proc in $procs
    do
        echo "Killing old nginx (from gdb maybe) in $proc"
        kill -9 $proc
    done
fi

# give the n/w a chance so ports are free to use
sleep 2

# Set/unset to detach or run in foreground
FGROUND=""
# FGROUND="-DFOREGROUND "

# if we don't have a local config, replace pathnames in repo version
# and copy to where it's needed
if [ ! -f $RUNTOP/nginx/nginxmin.conf ]
then
    do_envsubst
fi
# if the repo version of the config is newer, then backup the RUNTOP
# version and re-run envsubst
repo_date=`stat -c %Y $EDTOP/configs/nginxmin.conf`
runtop_date=`stat -c %Y $RUNTOP/nginx/nginxmin.conf`
if (( repo_date >= runtop_date))
then
    cp $RUNTOP/nginx/nginxmin.conf $RUNTOP/nginx/nginxmin.conf.$NOW
    do_envsubst
fi

echo "Executing: $NBIN -c nginxmin.conf"
# move over there to run code, so config file can have relative paths
cd $RUNTOP
if [ ! -f $RUNTOP/echconfig.pem ]
then
    echo "No ECHConfig - exiting!"
    exit 56
fi
$NBIN -c "$RUNTOP/nginx/nginxmin.conf"
cd -

for type in grease public real hrr
do
    port=5443
    echo "Testing $type $port"
    cli_test $port $type
    if [[ "$VERBOSE" == "yes" ]]
    then
        cat $CLILOGFILE
        rm -f $CLILOGFILE
    fi
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
    echo "Killing nginx in process `cat $PIDFILE`"
    kill `cat $PIDFILE`
    rm -f $PIDFILE
fi
