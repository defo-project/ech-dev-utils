#!/bin/bash

# Script to run smokeping like tests against CF, defo.ie and my-own.net
# using curl
#
# we'll run this from a cronjob and make the output available at test.defo.ie
# a PHP script will read/display the various flies as HTML
# a 2nd cronjob will delete older log files so we don't fill up a disk

# set -x

# structure is URL mapped to expected return value from
# curl --ech hard for that URL
declare -A targets=(
    [https://my-own.net/ech-check.php]="0"
    [https://my-own.net:8443/ech-check.php]="0"
    [https://defo.ie/ech-check.php]="0"
    [https://cover.defo.ie/]="0"
    [https://draft-13.esni.defo.ie:8413/stats]="0"
    [https://draft-13.esni.defo.ie:8414/stats]="0"
    [https://draft-13.esni.defo.ie:9413/]="0"
    [https://draft-13.esni.defo.ie:10413/]="0"
    [https://draft-13.esni.defo.ie:11413/]="0"
    [https://draft-13.esni.defo.ie:12413/]="0"
    [https://draft-13.esni.defo.ie:12414/]="0"
    [https://crypto.cloudflare.com/cdn-cgi/trace]="0"
    [https://tls-ech.dev/]="0"
    # [https://epochbelt.com/]="0"
    [https://myechtest.site/]="0"
    [https://hidden.hoba.ie/]="0"
    [https://min-ng.test.defo.ie/echstat.php?format=json]="0"
    [https://min-ng.test.defo.ie:15443/echstat.php?format=json]="0"
    [https://v1-ng.test.defo.ie/echstat.php?format=json]="0"
    [https://v1-ng.test.defo.ie:15443/echstat.php?format=json]="0"
    [https://v2-ng.test.defo.ie/echstat.php?format=json]="0"
    [https://v2-ng.test.defo.ie:15443/echstat.php?format=json]="0"
    [https://v3-ng.test.defo.ie/echstat.php?format=json]="0"
    [https://v3-ng.test.defo.ie:15443/echstat.php?format=json]="0"
    [https://v4-ng.test.defo.ie/echstat.php?format=json]="35"
    [https://v4-ng.test.defo.ie:15443/echstat.php?format=json]="35"
    [https://bk1-ng.test.defo.ie/echstat.php?format=json]="35"
    [https://bk1-ng.test.defo.ie:15443/echstat.php?format=json]="35"
    [https://bk2-ng.test.defo.ie/echstat.php?format=json]="35"
    [https://bk2-ng.test.defo.ie:15443/echstat.php?format=json]="35"
    [https://bv-ng.test.defo.ie/echstat.php?format=json]="35"
    [https://bv-ng.test.defo.ie:15443/echstat.php?format=json]="35"
    [https://badalpn-ng.test.defo.ie/echstat.php?format=json]="0"
    [https://badalpn-ng.test.defo.ie:15443/echstat.php?format=json]="0"
    # next one has no A/AAAA published so won't work
    [https://noaddr-ng.test.defo.ie/echstat.php?format=json]="6"
    [https://noaddr-ng.test.defo.ie:15443/echstat.php?format=json]="6"
    [https://many-ng.test.defo.ie/echstat.php?format=json]="0"
    [https://many-ng.test.defo.ie:15443/echstat.php?format=json]="0"
    [https://mixedmode-ng.test.defo.ie/echstat.php?format=json]="35"
    [https://mixedmode-ng.test.defo.ie:15443/echstat.php?format=json]="35"
    [https://p256-ng.test.defo.ie/echstat.php?format=json]="0"
    [https://p256-ng.test.defo.ie:15443/echstat.php?format=json]="0"
    [https://curves1-ng.test.defo.ie/echstat.php?format=json]="0"
    [https://curves1-ng.test.defo.ie:15443/echstat.php?format=json]="0"
    [https://curves2-ng.test.defo.ie/echstat.php?format=json]="0"
    [https://curves2-ng.test.defo.ie:15443/echstat.php?format=json]="0"
    [https://curves3-ng.test.defo.ie/echstat.php?format=json]="0"
    [https://curves3-ng.test.defo.ie:15443/echstat.php?format=json]="0"
    [https://h2alpn-ng.test.defo.ie/echstat.php?format=json]="0"
    [https://h2alpn-ng.test.defo.ie:15443/echstat.php?format=json]="0"
    [https://h1alpn-ng.test.defo.ie/echstat.php?format=json]="0"
    [https://h1alpn-ng.test.defo.ie:15443/echstat.php?format=json]="0"
    [https://mixedalpn-ng.test.defo.ie/echstat.php?format=json]="0"
    [https://mixedalpn-ng.test.defo.ie:15443/echstat.php?format=json]="0"
    [https://longalpn-ng.test.defo.ie/echstat.php?format=json]="0"
    [https://longalpn-ng.test.defo.ie:15443/echstat.php?format=json]="0"
    [https://2thenp-ng.test.defo.ie/echstat.php?format=json]="0"
    [https://2thenp-ng.test.defo.ie:15443/echstat.php?format=json]="0"
    [https://pthen2-ng.test.defo.ie/echstat.php?format=json]="0"
    [https://pthen2-ng.test.defo.ie:15443/echstat.php?format=json]="0"
    [https://withext-ng.test.defo.ie/echstat.php?format=json]="0"
    [https://withext-ng.test.defo.ie:15443/echstat.php?format=json]="0"
    [https://ng.test.defo.ie/echstat.php?format=json]="0"
    [https://ng.test.defo.ie:15443/echstat.php?format=json]="0"
    [https://ap.test.defo.ie/echstat.php?format=json]="0"
    [https://ap.test.defo.ie:15444/echstat.php?format=json]="0"
    [https://ly.test.defo.ie/echstat.php?format=json]="0"
    [https://ss.test.defo.ie/echstat.php?format=json]="0"
    [https://sshrr.test.defo.ie/echstat.php?format=json]="0"
)

# to pick up correct executables and .so's
: ${REPTOP:="sreps"}
: ${CURLTOP:="$HOME/code/curl"}

# time to wait for a remote access to work, 10 seconds
: ${tout:="5s"}
: ${curlparms=" -s --ech hard --doh-url https://one.one.one.one/dns-query"}
: ${curlbin="$CURLTOP/src/curl"}

function url2port()
{
    host=$(echo $1 | cut -d'/' -f3 | cut -d':' -f1)
    port=$(echo $1 | cut -d'/' -f3 | cut -d':' -f2)
    # if there's no ":" we get the same host and port
    if [[ "$port" == "$host" ]]
    then
        echo 443
    else
        echo $port
    fi
}

function url2host()
{
    host=$(echo $1 | cut -d'/' -f3 | cut -d':' -f1)
    echo $host
}

function whenisitagain()
{
    /bin/date -u +%Y%m%d-%H%M%S
}

function get_abs_filename() {
  # $1 : relative filename
  echo "$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
}

# we may add checks in a while...
allgood="yes"

NOW=$(whenisitagain)

if [ ! -d $REPTOP ]
then
    mkdir -p $REPTOP
fi
if [ ! -d $REPTOP ]
then
    echo "Can't make $REPTOP"
    exit 3
fi

rundir="$REPTOP/$NOW"
mkdir -p "$rundir"
if [ ! -d $rundir ]
then
    echo "Can't make $rundir"
    exit 3
fi

logfile=$(get_abs_filename "$rundir/$NOW.log")
tabfile=$(get_abs_filename "$rundir/$NOW.html")
touch "$logfile"
touch "$tabfile"

cd "$rundir"

echo "-----" >>$logfile
echo "Running $0 at $NOW"  >>$logfile
echo "Running $0 at $NOW"

# start of HTML
echo "<table border=\"1\" style=\"width:80%\">" >>$tabfile
#echo "<caption>ECH \"smokeping\" run from $NOW</caption>" >>$tabfile
echo "<tr>" >>$tabfile
echo "<th align=\"center\">Num</th>" >>$tabfile
echo "<th aligh=\"center\">URL</th>" >>$tabfile
echo "<th aligh=\"center\">Result</th>" >>$tabfile
echo "</tr>" >>$tabfile

if [[ "$allgood" == "yes" ]]
then
    index=0
    for targ in "${!targets[@]}"
    do
        expected=${targets[$targ]}
        port=$(url2port $targ)
        host=$(url2host $targ)
        if [[ "$port" != "443" && "$have_portsblocked" == "yes" ]]
        then
            echo "Skipping $targ as ports != 443 seem blocked"
            echo "Skipping $targ as ports != 443 seem blocked" >>$logfile
            echo "<tr><td>$index</td><td>$targ</td><td>Skipped $targ (ports != 443 blocked)</td></tr>" >>$tabfile
            continue
        fi
        # echo "Checking $targ"
        echo "Checking $targ" >>$logfile
        # timeout $tout $curlbin $curlparms $targ
        timeout $tout $curlbin $curlparms -o "$host.$port.out" $targ
        cres=$?
        if [[ "$cres" == "124" ]] 
        then
            allgood="no"
            echo "Timeout getting $targ" >>$logfile
            echo "Timeout getting $targ"
            echo "<tr><td>$index</td><td>$targ</td><td>Timeout</td></tr>" >>$tabfile
        elif [[ "$cres" != "$expected" ]]
        then
            allgood="no"
            echo "Unexpected result ($cres instead of $expected)  getting $targ" >>$logfile
            echo "Unexpected result ($cres instead of $expected)  getting $targ"
            echo "<tr><td>$index</td><td>$targ</td><td>FAIL: $cres instead of $expected</td></tr>" >>$tabfile
        else
            echo "Good/expected result for $targ" >>$logfile
            echo "Good/expected result for $targ"
            echo "<tr><td>$index</td><td>$targ</td><td>success</td></tr>" >>$tabfile
        fi
        index=$((index+1))
    done
fi


END=$(whenisitagain)
echo "Finished $0 at $END"  >>$logfile
echo "-----" >>$logfile
cd -

echo "</table>" >>$tabfile

if [[ "$allgood" == "yes" ]]
then
    echo "Finished $0 at $END"
    echo "All good"
    exit 0
fi

