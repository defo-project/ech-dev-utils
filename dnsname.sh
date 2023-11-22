#!/bin/bash

set -x

input=05636F766572046465666F02696500

function dnsdecode()
{
    ahstring=$1
    name=""

    nlen=${#ahstring}
    llen=99
    while ((llen!=0))
    do
        ahllen=`echo $ahstring | awk '{print substr($1,0,2)}'`
        llen=$((0x$ahllen))
        ahlabel=`echo $ahstring | awk '{print substr($1,3,'$((2*llen))')}'`
        label=`echo $ahlabel | xxd -r -p`
        if [[ "$name" == "" ]]
        then
            name="$label"
        else
            name="$name.$label"
        fi
        ahstring=`echo $ahstring | awk '{print substr($1,'$((2*llen+3))','$nlen')}'`
        nlen=${#ahstring}
    done

    echo $name
}

dnsdecode  $input
