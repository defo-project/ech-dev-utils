# ech-dev-utils utility functions

function envcheck()
{
    # check an env var that is needed here is set
    if [[ "$1" == "" ]]
    then
        echo "Missing env var - exiting"
        exit 1
    fi
}

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
        gorp="-P $RUNTOP/echconfig.pem -R "
    elif [[ "$runparm" == "real" ]]
    then
        gorp="-P echconfig.pem "
    else
        echo "bad cli_test parameter $runparm, exiting"
        exit 99
    fi
    envcheck $EDTOP
    envcheck $CLILOGFILE
    envcheck $allgood
    $EDTOP/scripts/echcli.sh $clilog $gorp -p $port -H $target -s localhost -f index.html >>$CLILOGFILE 2>&1
    lres=$?
    if [[ "$lres" != "0" ]]
    then
        echo "test failed: $EDTOP/scripts/echcli.sh $clilog $gorp-p $port -H $target -s localhost -f index.html"
        allgood="no"
    fi
}

# stop a lighttpd if one is running
lighty_stop() {
    local pfile="$RUNTOP/lighttpd/logs/lighttpd.pid"

    if [ -f $pfile ]
    then
        kill `cat $pfile`
        rm -f $pfile
    fi
}

# Check if a lighttpd is running, start one if not
lighty_start() {
    local cfgfile=$1
    local pfile="$RUNTOP/lighttpd/logs/lighttpd.pid"

    lighty_stop
    envcheck $RUNTOP
    envcheck $LIGHTY
    envcheck $SRVLOGFILE
    if [ ! -f $cfgfile ]
    then
        echo "Can't read $cfgfile - exiting"
        exit 45
    fi
    export LIGHTYTOP=$RUNTOP
    if [[ "$PACKAGING" == "" ]]
    then
        $LIGHTY/src/lighttpd -f $cfgfile -m $LIGHTY/src/.libs >>$SRVLOGFILE 2>&1
    else
        lighttpd -f $cfgfile >>$SRVLOGFILE 2>&1
    fi
    # Check we now have a lighty running
    if [ ! -f $pfile ]
    then
        echo "Can't read $pfile - exiting"
        exit 45
    fi
}

s_server_start() {
    local srunning=`ps -ef | grep s_server | grep -v grep | grep -v tail | awk '{print $2}'`
    local hrr=$1

    envcheck $EDTOP
    envcheck $SRVLOGFILE
    if [[ "$srunning" == "" ]]
    then
        # ditch or keep server tracing
        if [[ "$hrr" == "hrr" ]]
        then
            $EDTOP/scripts/echsvr.sh -e -k echconfig.pem -p 3484 -R >$SRVLOGFILE 2>&1 &
        else
            $EDTOP/scripts/echsvr.sh -e -k echconfig.pem -p 3484 >$SRVLOGFILE 2>&1 &
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
    envcheck $EDTOP
    envcheck $RUNTOP
    # We'll use sed for now as figuring out how to get envsubst running in the github CI
    # isn't (yet;-) obvious
    # cat $EDTOP/configs/nginxsplit.conf | envsubst '{$RUNTOP}' >$RUNTOP/nginx/nginxsplit.conf
    # cat $EDTOP/configs/nginxmin.conf | envsubst '{$RUNTOP}' >$RUNTOP/nginx/nginxmin.conf
    sed "s#\$RUNTOP#$RUNTOP#g" "$EDTOP/configs/nginxmin.conf" > "$RUNTOP/nginx/nginxmin.conf"
    sed "s#\$RUNTOP#$RUNTOP#g" "$EDTOP/configs/nginxsplit.conf" > "$RUNTOP/nginx/nginxsplit.conf"
}

prep_server_dirs() {
    local tech=$1

    envcheck $RUNTOP

    cd $RUNTOP
    # make sure fake CA is setup
    if [ ! -d $RUNTOP/cadir ]
    then
        # don't re-do this if not needed, might break other configs
        $EDTOP/scripts/make-example-ca.sh
    fi
    # make sure we have an ECHConfig PEM file
    if [ ! -f $RUNTOP/echconfig.pem ]
    then
        $CMDPATH ech -public_name example.com || true
    fi
    if [ ! -d $RUNTOP/echkeydir ]
    then
        mkdir -p $RUNTOP/echkeydir
        cp $RUNTOP/echconfig.pem $RUNTOP/echkeydir/echconfig.pem.ech
    fi
    # make directories for lighttpd stuff if needed
    mkdir -p $RUNTOP/$tech/logs

    for docroot in example.com foo.example.com baz.example.com
    do
        mkdir -p $RUNTOP/$tech/dir-$docroot
        # check for/make a home page for example.com and other virtual hosts
        if [ ! -f $RUNTOP/$tech/dir-$docroot/index.html ]
        then
            cat >$RUNTOP/$tech/dir-$docroot/index.html <<EOF

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
    cd -
}

