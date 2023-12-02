#!/bin/bash

set -x

# to pick up correct executables and .so's
: ${CODETOP:=$HOME/code/openssl}
export LD_LIBRARY_PATH=$CODETOP
: ${EDTOP:=$HOME/code/ech-dev-utils}
: ${NTOP:=$HOME/code/nginx}
# where we have/want test files
: ${RUNTOP:=`/bin/pwd`}
export RUNTOP=$RUNTOP

# make directories for lighttpd stuff if needed
mkdir -p $RUNTOP/nginx/logs
mkdir -p $RUNTOP/nginx/www
mkdir -p $RUNTOP/nginx/foo

# in case we wanna dump core and get a backtrace, make a place for
# that (dir name is also in configs/nginxmin.conf)
mkdir -p /tmp/cores

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
PIDFILE=$RUNTOP/nginx/nginx.pid
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

# give the n/w a chance so 9443 is free to use
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
    cat $EDTOP/configs/nginxmin.conf | envsubst >$RUNTOP/nginx/nginxmin.conf
fi

echo "Executing: $VALGRIND $NTOP/objs/nginx -c $EDTOP/configs/nginxmin.conf"
# move over there to run code, so config file can have relative paths
cd $RUNTOP
$VALGRIND $NTOP/objs/nginx -c nginxmin.conf 
cd -

