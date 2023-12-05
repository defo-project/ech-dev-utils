#!/bin/bash

# Run a lighttpd on localhost:3443 with foo.example.com accessible
# via ECH

# set -x

# to pick up correct executables and .so's
: ${CODETOP:=$HOME/code/openssl}
export LD_LIBRARY_PATH=$CODETOP
: ${EDTOP:=$HOME/code/ech-dev-utils}
: ${RUNTOP:=`/bin/pwd`}
export RUNTOP=$RUNTOP
: ${LIGHTY:=$HOME/code/lighttpd1.4}

export TOP=$CODETOP

export LD_LIBRARY_PATH=$CODETOP

# make directories for lighttpd stuff if needed
mkdir -p $RUNTOP/lighttpd/logs
mkdir -p $RUNTOP/lighttpd/www
mkdir -p $RUNTOP/lighttpd/baz

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
FOREGROUND="-D "

# set to use valgrind, unset to not
# VALGRIND="valgrind --leak-check=full --show-leak-kinds=all"
# VALGRIND="valgrind --leak-check=full --error-limit=1 --track-origins=yes"
VALGRIND=""

echo "Executing: $VALGRIND $LIGHTY/src/lighttpd $FOREGROUND -f $EDTOP/configs/lighttpdmin.conf -m $LIGHTY/src/.libs"
$VALGRIND $LIGHTY/src/lighttpd $FOREGROUND -f $EDTOP/configs/lighttpdmin.conf -m $LIGHTY/src/.libs
