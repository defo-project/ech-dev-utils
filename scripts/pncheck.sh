#!/bin/bash
#
# extract the public_name field from ech= fields of an input
# file with HTTPS RR presentation format values that do/do
# not have the public_name value supplied
#
# set -x

NEEDLE=""
INFILE="echdomains.csv"
SEP='|'
: ${GETOPTDIR:=/usr/bin}

# extract public_name(s) from base64 encoded ECHConfigList
# we'll just let the shell barf if the input is badly encoded
# so you might get an error sent to stderr in such a case
function getpn()
{
    base64="$1"
    ah=$(echo "$base64" | base64 -d | xxd -p -c 0)
    ah_len=${#ah}
    results=""
    nstart=4
    while ((nstart < ah_len))
    do
        echconfig=${ah:$nstart:$ah_len}
        # leave in reading unused values, for clarity and
        # possible future use
        # version=${echconfig:0:4}
        ah_echconfig_len=${echconfig:4:4}
        echconfig_len=$((16#$ah_echconfig_len))
        # config_id=${echconfig:8:2}
        # kem_id=${echconfig:10:4}
        ah_pk_len=${echconfig:14:4}
        pk_len=$((16#$ah_pk_len))
        cs_off=$((18+2*pk_len))
        ah_cs_len=${echconfig:$cs_off:4}
        cs_len=$((16#$ah_cs_len))
        # skip the max_name_length
        pn_len_off=$((cs_off+2*cs_len+6))
        ah_pn_len=${echconfig:$pn_len_off:2}
        pn_len=$((16#$ah_pn_len))
        pn_off=$((pn_len_off+2))
        ah_pn=${echconfig:$pn_off:$((2*pn_len))}
        pn=$(echo "$ah_pn" | xxd -r -p)
        nstart=$((nstart+2*echconfig_len+8))
        if [[ "$results" == "" ]]
        then
            results=$pn
        else
            results="$results/$pn"
        fi
    done
    echo "$results"
}

function usage()
{
    echo "$0 [-chnps] - check CSV for ECH public_name values"
    echo "  -c [file-name] specifices the CSV input file (default is 'echdomains.csv')"
    echo "  -h print this"
    echo "  -n match lines that do not contain the public_name (default off)"
    echo "  -p [public_name] specifices the public_name value (no default)"
    echo "  -s [char] specify the CSV separator character (default is '|')"

    echo ""
    echo "The following should work:"
    echo "    $0 -p cloudflare-ech.com"
    exit 99
}

# check we have what looks like a good getopt (the native version on macOS
# seems to not be good)
if [ ! -f "$GETOPTDIR"/getopt ]
then
    echo "No sign of $GETOPTDIR/getopt - exiting"
    exit 32
fi
getoptcnt=$("$GETOPTDIR"/getopt --version | grep -c "util-linux") || true
if [[ "$getoptcnt" != "1" ]]
then
    echo "$GETOPTDIR/getopt doesn't seem to be gnu-getopt - exiting"
    exit 32
fi

# options may be followed by one colon to indicate they have a required argument
if ! options=$("$GETOPTDIR"/getopt -s bash -o c:hnp:s: -l csv:,help,neg,pub:,sep:  -- "$@")
then
    # something went wrong, getopt will put out an error message for us
    exit 1
fi
#echo "|$options|"
eval set -- "$options"
while [ $# -gt 0 ]
do
    case "$1" in
        -c|--csv) INFILE=$2; shift;;
        -h|--help) usage;;
        -n|--neg) NEG="yes" ;;
        -p|--pub) NEEDLE=$2; shift;;
        -s|--sep) SEP=$2; shift;;
        (--) shift; break;;
        (-*) echo "$0: error - unrecognized option $1" 1>&2; exit 1;;
        (*)  break;;
    esac
    shift
done

if [ ! -f "$INFILE" ]
then
    echo "No sign of $INFILE - exiting"
    exit 1
fi

if [[ "$NEEDLE" == "" ]]
then
    echo "No public_name supplied - exiting"
    exit 2
fi

while IFS= read -r line; do
    # skip if no presentation format ECHConfigList present
    if [[ $line != *ech=* ]]
    then
        continue
    fi
    base64=$(echo "$line" | sed -e 's/.*ech=//' | sed -e 's/ .*//')
    # extract public_name(s)
    res="ok"
    pn=$(getpn "$base64") || {
        # if decode barfs signal error and set pn to skip next branch
        # this WILL happen as we have some test cases that deliberately
        # have errors, e.g. dodgy.test.defo.ie, so you should expect
        # some error strings in the output
        res="ERROR"
        echo "$line$SEP$res"
    }
    # yes this could be more terse, but readability is good:-)
    if [[ "$res" == "ok" ]]
    then
        if [[ "$NEG" == "yes" ]]
        then
            if [[ "$pn" != "$NEEDLE" ]]
            then
                echo "$line$SEP$pn"
            fi
        else
            if [[ "$pn" == "$NEEDLE" ]]
            then
                echo "$line$SEP$pn"
            fi
        fi
    fi
done < "$INFILE"
