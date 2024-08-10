#!/bin/bash

# Script to run smokeping like tests against CF, defo.ie and my-own.net
# using curl
#
# we'll run this from a cronjob and make the output available at test.defo.ie
# a PHP script will read/display the various flies as HTML
# a 2nd cronjob will delete older log files so we don't fill up a disk

# set -x

# main inputs - can be overridden via command line of environment
: ${RESULTS_DIR:="/var/extra/smokeping/runs"}
: ${URLS_TO_TEST:="/var/extra/urls_to_test.csv"}

# to pick up correct executables and .so's
: ${CURLTOP:="$HOME/code/curl"}
: ${GETOPTDIR:=/usr/bin}

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

function usage()
{
    echo "$0 [-hdu] - run ECH tests with curl"
	echo "  -h print this"
    echo "  -r <results_dir> - specify the directory below which date stamped results with be put"
	echo "  -u <urls_to_test> - provide a non-default s4et of URLs and expected outcomes"
    exit 99
}

# check we have what looks like a good getopt (the native version on macOS 
# seems to not be good)
if [ ! -f $GETOPTDIR/getopt ]
then
    echo "No sign of $GETOPTDIR/getopt - exiting"
    exit 32
fi
getoptcnt=`$GETOPTDIR/getopt --version | grep -c "util-linux"`
if [[ "$getoptcnt" != "1" ]]
then
    echo "$GETOPTDIR/getopt doesn't seem to be gnu-getopt - exiting"
    exit 32
fi

# options may be followed by one colon to indicate they have a required argument
if ! options=$($GETOPTDIR/getopt -s bash -o h,r:,u: -l help,results_dir:,urls_to_test: -- "$@")
then
    # something went wrong, getopt will put out an error message for us
    exit 1
fi
#echo "|$options|"
eval set -- "$options"
while [ $# -gt 0 ]
do
    case "$1" in
        -h|--help) usage;;
        -r|--results_dir) RESULTS_DIR=$2; shift;;
        -u|--urls_to_test) URLS_TO_TEST=$2; shift;;
        (--) shift; break;;
        (-*) echo "$0: error - unrecognized option $1" 1>&2; exit 1;;
        (*)  break;;
    esac
    shift
done

if [ ! -d $RESULTS_DIR ]
then
    mkdir -p $RESULTS_DIR
fi
if [ ! -d $RESULTS_DIR ]
then
    echo "Can't make $RESULTS_DIR"
    exit 3
fi

rundir="$RESULTS_DIR/$NOW"
mkdir -p "$rundir"
if [ ! -d $rundir ]
then
    echo "Can't make $rundir"
    exit 3
fi

if [ ! -f $URLS_TO_TEST ]
then
    echo "Can't read $URLS_TO_TEST - exiting"
    exit 4
fi

# load from $URLS_TO_TEST into $targets
# associative array of URLs to test with expected curl return values
# e.g.: [https://my-own.net/ech-check.php]="0"
declare -A targets=( )
lineno=0
while IFS=',' read -r url curl_e ff_e chr_e; do
    if ((lineno!=0))
    then
        targets[$url]+=$curl_e
    fi
    lineno=$((lineno+1))
done < "$URLS_TO_TEST"

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
            echo "<tr><td>$index</td><td>$targ</td><td>expected</td></tr>" >>$tabfile
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
