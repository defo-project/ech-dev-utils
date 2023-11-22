#!/bin/bash

# Script to run smokeping like tests against CF, defo.ie and my-own.net
# using echcli.sh

# set -x

# structure is host:port mapped to pathname
declare -A targets=(
    [my-own.net]="ech-check.php"
    [my-own.net:8443]="ech-check.php"
    [defo.ie]="ech-check.php"
    [cover.defo.ie]=""
    [draft-13.esni.defo.ie:8413]="stats"
    [draft-13.esni.defo.ie:8414]="stats"
    [draft-13.esni.defo.ie:9413]=""
    [draft-13.esni.defo.ie:10413]=""
    [draft-13.esni.defo.ie:11413]=""
    [draft-13.esni.defo.ie:12413]=""
    [draft-13.esni.defo.ie:12414]=""
    [crypto.cloudflare.com]="cdn-cgi/trace"
    [tls-ech.dev]=""
    [epochbelt.com]=""
    [myechtest.site]=""
    [hidden.hoba.ie]=""
)

# to pick up correct executables and .so's
: ${CODETOP:=$HOME/code/openssl}
export LD_LIBRARY_PATH=$CODETOP
# to pick up correct wrapper scripts
: ${EDTOP:=$HOME/code/ech-dev-utils}

# place to stash outputs when things go wrong
: ${bad_dir:="$HOME/logs/smoke_ech_baddies"}

# time to wait for a remote access to work, 10 seconds
: ${tout:="10s"}

: ${DOMAIL:="no"}

# if ports other than 443 are blocked we don't want
# to timeout loads of times, just once
have_portsblocked="no"

DEFPORT=443

function whenisitagain()
{
    /bin/date -u +%Y%m%d-%H%M%S
}

function fileage()
{
    echo $(($(date +%s) - $(date +%s -r "$1")))
}

function hostport2host()
{
    case $1 in
      *:*) host=${1%:*} port=${1##*:};;
        *) host=$1      port=$DEFPORT;;
    esac
    echo $host
}

function hostport2port()
{
    case $1 in
      *:*) host=${1%:*} port=${1##*:};;
        *) host=$1      port=$DEFPORT;;
    esac
    echo $port
}

TMPD=`mktemp -d`
allgood="yes"
digcmd="dig https"

NOW=$(whenisitagain)

cd $TMPD

logfile=$TMPD/$NOW.log

echo "-----" >>$logfile
echo "Running $0 at $NOW"  >>$logfile
echo "Running $0 at $NOW"

# check we have binaries
if [ ! -d $CODETOP ] 
then
    allgood="no"
    echo "Can't see $CODETOP - exiting" >>$logfile
fi
echcli=$EDTOP/echcli.sh
if [ ! -f $echcli ]
then
    allgood="no"
    echo "Can't see $EDTOP/echcli.sh - exiting" >>$logfile
fi
if [ ! -f $CODETOP/apps/openssl ]
then
    allgood="no"
    echo "Can't see $CODETOP/apps/openssl - exiting" >>$logfile
fi
havecurl=`which curl`
if [[ "$havecurl" == "" ]]
then
    allgood="no"
    echo "Can't see a curl binary - exiting" >>$logfile
fi

# Check if ports other than 443 are blocked from this
# vantage point (I run tests in a n/w where that's
# sadly true sometimes;-)
# echo "Checking if ports other than 443 are maybe blocked"
not443testurl="https://draft-13.esni.defo.ie:9413/"
timeout $tout curl $not443testurl >/dev/null 2>&1
eres=$?
if [[ "$eres" == "124" ]] 
then
    echo "Timeout running curl for $not443testurl" >>$logfile
    echo "Timeout running curl for $not443testurl"
    have_portsblocked="yes"
fi

# check if dig knows https or not
digcmd="dig https"
dout=`dig +short https defo.ie`
if [[ $dout != "1 . ech="* ]]
then
    digcmd="dig -t TYPE65"
fi

if [[ "$allgood" == "yes" ]]
then
    for targ in "${!targets[@]}"
    do
        host=$(hostport2host $targ)
        port=$(hostport2port $targ)
        if [[ "$port" != "443" && "$have_portsblocked" == "yes" ]]
        then
            echo "Skipping $targ as ports != 443 seem blocked"
            continue
        fi
        path=${targets[$targ]}
        pathstr=""
        if [[ "$path" != "" ]]
        then
            pathstr="-f $path"
        fi
        wkurl="https://$host:$port/.well-known/origin-svcb"
        qname=$host
        if [[ "$port" != "$DEFPORT" ]]
        then
            qname="_$port._https.$host"
        fi
        echo "Checking $host:$port/$path and $wkurl" >>$logfile
        # get wkurl
        if [[ "$host" != "crypto.cloudflare.com" && "$host" != "tls-ech.dev" ]]
        then
            timeout $tout curl -o $host.$port.json -s $wkurl
            cres=$?
            if [[ "$cres" == "124" ]] 
            then
                allgood="no"
                echo "Timeout getting $wkurl" >>$logfile
            fi
        else
            echo "{ \"No .well-known for $host \"}" >$host.$port.json
        fi
        # grab DNS
        $digcmd $qname >$host.$port.dig 2>&1
        # try ECH 
        timeout $tout $echcli -H $host -p $port $pathstr -d >$host.$port.echcli.log
        eres=$?
        if [[ "$eres" == "124" ]] 
        then
            allgood="no"
            echo "Timeout running echcli.sh for $host:$port/$path" >>$logfile
        fi
        if [[ "$eres" != "0" ]] 
        then
            allgood="no"
            echo "Error ($eres) from echcli.sh for $host:$port/$path" >>$logfile
        fi
    done
fi

END=$(whenisitagain)
echo "Finished $0 at $END"  >>$logfile
echo "-----" >>$logfile
cd -

if [[ "$allgood" == "yes" ]]
then
    rm -rf $TMPD
    echo "Finished $0 at $END"
    echo "All good"
    exit 0
fi

# stash bad stuff
if [ ! -d $bad_dir ]
then
    mkdir -p $bad_dir
    if [ ! -d $bad_dir ]
    then
        echo "Can't create $bad_dir - exiting"
        exit 1
    fi
fi
# stash logs of bad run and info about bad runs
mv $TMPD $bad_dir/$NOW
# send a mail to root (will be fwd'd) but just once every 24 hours
# 'cause we only really need "new" news
itsnews="yes"
age_of_news=0
if [ -f $bad_dir/bad_runs ]
then
    age_of_news=$(fileage $bad_dir/bad_runs)
    # only consider news "new" if we haven't mailed today
    if ((age_of_news < 24*3600))
    then
        itsnews="no"
    fi
fi
if [[ "$DOMAIL" == "yes" && "$itsnews" == "yes" ]]
then
    echo "ECH badness at $NOW" | mail -s "ECH badness at $NOW" root
fi
# add to list of bad runs (updating file age)
echo "ECH badness at $NOW" >>$bad_dir/bad_runs
exit 2
