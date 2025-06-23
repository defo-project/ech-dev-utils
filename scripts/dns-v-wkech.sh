#!/bin/bash

# Compare ECH values seen in DNS and at .well-known/origin-svcb

# set -x

function getb64ech()
{
    rrval="$1"
    echb64=""
    for substr in $rrval
    do
        if [[ $substr == ech=* ]]
        then
            echb64=${substr:4}
            echo "$echb64"
            echo
        fi
    done
}

# origin is a DNS name or a host:port string if not using port 443
origin="$1"

wkf=$(mktemp)
df=$(mktemp)

wkurl="https://$origin/.well-known/origin-svcb"
wkech_content=$(curl "$wkurl")
wkech=""
if [[ "$wkech_content" == "" ]]
then
    echo "No wkech for $origin seen"
else
    wkech=$(echo "$wkech_content" | jq '.endpoints[].params.ech' 2>/dev/null)
    if [[ "$wkech" == "" ]]
    then
        echo "No ECHConfigs seen at $wkurl"
    else
        echo "${wkech//\"/}" >"$wkf"
    fi
fi

qname=$origin
if [[ $origin == *":"* ]]
then
    host=$(echo "$origin" | awk -F':' '{print $1}')
    port=$(echo "$origin" | awk -F':' '{print $2}')
    if [[ "$port" != "443" ]]
    then
        qname="_$port._https.$host"
    else
        qname="$host"
    fi
fi

lines=$(dig +short https "$qname")
if [[ "$lines" == "" ]]
then
    echo "No HTTPS RR for $qname seen"
else
    dnsech=$(getb64ech "$lines")
    echo "$dnsech" >"$df"
fi

if [[ "$wkech$dnsech" != "" ]]
then 
    diff -q "$wkf" "$df" >/dev/null
    differ=$?
    if [[ "$differ" == "0" ]]
    then
        echo "ECH configs are the same in $wkurl and HTPS RR for $qname"
        echo "    $dnsech"
    else
        echo "ECH configs differ between $wkurl and HTPS RR for $qname"
        if [[ "$wkech" == "" ]]
        then
            echo "No ECHConfigs at $wkurl"
        else
            echo "From $wkurl:"
            sed 's/^/    /' <"$wkf"
        fi
        if [[ "$dnsech" == "" ]]
        then
            echo "No ECHConfigs at $qname"
        else
            echo "From HTTPS RR for $qname:"
            sed 's/^/    /' <"$df"
        fi
        if [[ "$wkech" != "" && "$dnsech" != "" ]]
        then
            echo "Diff:"
            git --no-pager diff --word-diff=color --word-diff-regex=. "$wkf" "$df"
        fi
    fi
fi

rm -rf "$wkf" "$df"
