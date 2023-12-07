#!/bin/bash

# set -x

# map the ECHConfigList from a PEM file to an ascii-hex RR that
# could be included in a zone file as the value of a basic HTTPS RR
#
# I've added support for including IPv4 and IPv6 hints, but that's
# not tested much.
# I've not added support for ALPNs yet as I don't need it for now
# and the escape-char handling would be a pain.

PEMFILE="echconfig.pem"
RRFILE="/dev/stdout"
DOMAIN=""
IPV4s=""
IPV6s=""
BASE64="no"

function usage()
{
    echo "$0 - map a PEMFile containing an ECHConfigs to an ascii-hex or base64 encoded SVCB RR value"
    echo "  -b means to produce base64 encoded output (default is ascii-hex)"
    echo "  -p [pemfile] specifies the pemfile input (default $PEMFILE)"
    echo "  -d domain specifies the domain to lookup A/AAAA RRs for to populate the above instead"
    echo "  -r [rrfile] specifies the output (default $RRFILE)"
    echo "  -h means print this"
    exit 99
}

# options may be followed by one colon to indicate they have a required argument
if ! options=$(/usr/bin/getopt -s bash -o bd:hp:r: -l base64,domain:,help,pemfile:,rrfile: -- "$@")
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
        -b|--base64) BASE64="yes";;
        -p|--pemfile) PEMFILE=$2; shift;;
        -d|--domain) DOMAIN=$2; shift;;
        -r|--rrfile) RRFILE=$2; shift;;
        (--) shift; break;;
        (-*) echo "$0: error - unrecognized option $1" 1>&2; exit 1;;
        (*)  break;;
    esac
    shift
done

if [ ! -f $PEMFILE ]
then
    echo "Can't read $PEMFILE - exiting"
    exit 1
fi

rr_preamble="000100"
ah_ech=`tail -2 $PEMFILE | head -1 | base64 -d | xxd -ps -c 200 | tr -d '\n'`  
ah_ech_len=${#ah_ech}
ah_ech_len=`printf  "%04x" $((ah_ech_len/2))`
ah_ech_header="0005${ah_ech_len}"
# if you're good with no more...
rr_postamble=""
ipv4hints=""
ipv6hints=""

if [[ "$DOMAIN" != "" ]]
then
    # try dig to get addresses for DOMAIN and then proceed
    IPV4s=`dig +short +unknownformat $DOMAIN | awk '{print $3}'`
    IPV6s=`dig +short +unknownformat aaaa $DOMAIN | awk '{print $3}'`
    if [[ "$IPV4s" == "" && "$IPV6s" == "" ]]
    then
        echo "No A/AAAA records for $DOMAIN - exiting"
        exit 99
    fi
    if [[ "$IPV4s" != "" ]]
    then
        acount=0
        ipv4hint_val=""
        for val in $IPV4s
        do   
            ((acount++))
            ipv4hint_val="$ipv4hint_val$val"
        done
        ipv4hint_type="0004"
        ipv4hint_len=`printf "%04x" $((acount*4))`
        ipv4hints="$ipv4hint_type$ipv4hint_len$ipv4hint_val"
    fi
    if [[ "$IPV6s" != "" ]]
    then
        acount=0
        ipv6hint_val=""
        for val in $IPV6s
        do   
            ((acount++))
            ipv6hint_val="$ipv6hint_val$val"
        done
        ipv6hint_type="0006"
        ipv6hint_len=`printf "%04x" $((acount*16))`
        ipv6hints="$ipv6hint_type$ipv6hint_len$ipv6hint_val"
    fi
fi

if [[ "$BASE64" != "yes" ]]
then
    echo "$rr_preamble$ipv4hints$ah_ech_header$ah_ech$ipv6hints$rr_postamble" >$RRFILE
else
    b64str=`echo "$rr_preamble$ipv4hints$ah_ech_header$ah_ech$ipv6hints$rr_postamble" | xxd -p -r | base64 -w 0` 
    echo $b64str >$RRFILE
fi
