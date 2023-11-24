#!/bin/bash

# set -x

# to pick up correct executables and .so's
: ${CODETOP:=$HOME/code/openssl}
export LD_LIBRARY_PATH=$CODETOP
: ${EDTOP:=$HOME/code/ech-dev-utils}
# Note that the value for this has to match that for ATOP
# in apachemin-draft-13.conf, so if you change this on the
# command line, you'll need to edit the conf file
: ${ATOP:=$HOME/code/httpd}
# where we have/want test files
: ${RUNTOP:=`/bin/pwd`}

# make directories for lighttpd stuff if needed
mkdir -p $RUNTOP/apache/logs
mkdir -p $RUNTOP/apache/www
mkdir -p $RUNTOP/apache/foo

# check for/make a home page for example.com and other virtual hosts
if [ ! -f $RUNTOP/apache/www/index.html ]
then
    cat >$RUNTOP/apache/www/index.html <<EOF

<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>example.com apache top page.</title>
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

# check for/make a slightly different home page for foo.example.com
if [ ! -f $RUNTOP/apache/foo/index.html ]
then
    cat >$RUNTOP/apache/foo/index.html <<EOF

<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>foo.example.com apache top page.</title>
</head>
<!-- Background white, links blue (unvisited), navy (visited), red
(active) -->
<body bgcolor="#FFFFFF" text="#000000" link="#0000FF"
vlink="#000080" alink="#FF0000">
<p>This is the pretty dumb top page for foo.example.com testing. </p>

</body>
</html>

EOF
fi

# if we want to reload config then that's "graceful restart"
if [[ "$1" == "graceful" ]]
then
    echo "Telling apache to do the graceful thing"
    $ATOP/httpd -d $RUNTOP -f $EDTOP/configs/apachemin.conf -k graceful
    exit $?
fi

PIDFILE=$RUNTOP/apache/httpd.pid
# Kill off old processes from the last test
if [ -f $PIDFILE ]
then
    echo "Killing old httpd in process `cat $PIDFILE`"
    kill `cat $PIDFILE`
    rm -f $PIDFILE
else 
    echo "Can't find $PIDFILE - tring killall httpd"
    killall httpd
fi

# if starting afresh check if some process was left over after gdb or something

# kill off other processes
procs=`ps -ef | grep httpd | grep -v grep | awk '{print $2}'`
for proc in $procs
do
    echo "Killing old httpd (from gdb maybe) in $proc"
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

echo "Executing: $VALGRIND $ATOP/httpd -d $RUNTOP -f $EDTOP/configs/apachemin.conf $FGROUND"
# move over there to run code, so config file can have relative paths
cd $RUNTOP
$VALGRIND $ATOP/httpd -d $RUNTOP -f $EDTOP/configs/apachemin.conf $FGROUND
cd - 

