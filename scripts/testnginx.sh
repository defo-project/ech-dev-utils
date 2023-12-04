#!/bin/bash

# set -x

# to pick up correct executables and .so's
: ${CODETOP:=$HOME/code/openssl}
export LD_LIBRARY_PATH=$CODETOP
: ${EDTOP:=$HOME/code/ech-dev-utils}
: ${NTOP:=$HOME/code/nginx}
# where we have/want test files
: ${RUNTOP:=`/bin/pwd`}
export RUNTOP=$RUNTOP
: ${LIGHTY:=$HOME/code/lighttpd1.4}

# make directories for lighttpd stuff if needed
mkdir -p $RUNTOP/nginx/logs
mkdir -p $RUNTOP/nginx/www
mkdir -p $RUNTOP/nginx/foo

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
# set next one to " -d " if keeping logs and verbosity desired
DPARM=" "

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
        $LIGHTY/src/lighttpd $FOREGROUND -f $EDTOP/configs/lighttpd4nginx-split.conf -m $LIGHTY/src/.libs >>$SRVLOGFILE 2>&1
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
            $EDTOP/scripts/echsvr.sh -e -k echconfig.pem -p 9444 $DPARM -R >$SRVLOGFILE 2>&1 &
        else
            $EDTOP/scripts/echsvr.sh -e -k echconfig.pem -p 9444 $DPARM >$SRVLOGFILE 2>&1 &
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
    cat $EDTOP/configs/nginxmin.conf | envsubst '{$RUNTOP}' >$RUNTOP/nginx/nginxmin.conf
}

# check for/make a home page for example.com and other virtual hosts
if [ ! -f $RUNTOP/nginx/www/index.html ]
then
    cat >$RUNTOP/nginx/www/index.html <<EOF

<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>example.com nginx top page.</title>
</head>
<!-- Background white, links blue (unvisited), navy (visited), red
(active) -->
<body bgcolor="#FFFFFF" text="#000000" link="#0000FF"
vlink="#000080" alink="#FF0000">
<p>This is the pretty dumb top page for nginx testing. </p>

</body>
</html>

EOF
fi

# check for/make a slightly different home page for foo.example.com
if [ ! -f $RUNTOP/nginx/foo/index.html ]
then
    cat >$RUNTOP/nginx/foo/index.html <<EOF

<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>foo.example.com nginx top page.</title>
</head>
<!-- Background white, links blue (unvisited), navy (visited), red
(active) -->
<body bgcolor="#FFFFFF" text="#000000" link="#0000FF"
vlink="#000080" alink="#FF0000">
<p>This is the pretty dumb top page for foo.example.com nginx testing. </p>

</body>
</html>

EOF
fi

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
else
    echo "Can't find $PIDFILE - trying killall nginx"
    killall nginx
fi

# if starting afresh check if some process was left over after gdb or something

# kill off other processes
procs=`ps -ef | grep nginx | grep -v grep | grep -v testnginx | awk '{print $2}'`
for proc in $procs
do
    echo "Killing old nginx (from gdb maybe) in $proc"
    kill -9 $proc
done

# give the n/w a chance so ports are free to use
sleep 2

# set to use valgrind, unset to not
# VALGRIND="valgrind --leak-check=full --show-leak-kinds=all"
VALGRIND=""

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

echo "Executing: $VALGRIND $NTOP/objs/nginx -c nginxmin.conf"
# move over there to run code, so config file can have relative paths
cd $RUNTOP
$VALGRIND $NTOP/objs/nginx -c nginxmin.conf
cd -

for type in grease public real hrr
do
    port=5443
    echo "Testing $type $port"
    cli_test $port $type
done

#if we're testing split-mode stuff...
if [[ "$SPLIT" == "yes" ]]
then
    # start a backend
    lighty_start
    # all these should appear the same to the client
    # server log checks will tell us if stuff worked or not
    echo "Doing split-mode tests..."
    for type in grease public real hrr
    do
        for port in 5443 9443
        do
            echo "Testing $type $port"
            cli_test $port $type
        done
    done
    # need special stuff for early_data as lighty doesn't support that
    if [[ "$EARLY" == "yes" ]]
    then
        echo "Doing early data tests"
        lighty_stop

        # need to srart s_server differently to trigger hrr, same client 
        # args is fine though
        for type in nohrr hrr
        do
            port=9443
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
    fi
fi

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
else
    echo "Can't find $PIDFILE - trying killall nginx"
    killall nginx
fi
