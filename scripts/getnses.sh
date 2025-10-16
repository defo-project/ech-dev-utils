#!/bin/bash
#
# Give a file with a list of names, check the NS for that name
# and report if it's cloudfare or DEfO or NXDOMAIN/SERVFAIL or
# something else

NAMEFILE="./names"

for name in `cat $NAMEFILE`
do
    thens=`dig +short ns $name | head -1`
    thestatus=`dig $name | grep status | awk '{print $6}'`
    twoldnotneeded="direct"
    if [[ "$thens" == "" ]]
    then
        twold=`echo $name | awk -F'.' '{print $(NF-1)"."$NF}'`
        thens=`dig +short ns $twold | head -1`
        thestatus=`dig $twold | grep status | awk '{print $6}'`
        twoldnotneeded="via-2ld"
    elif [[ $thens == *'communications error'* ]]
    then
        twold=`echo $name | awk -F'.' '{print $(NF-1)"."$NF}'`
        thens=`dig +short ns $twold | head -1`
        thestatus=`dig $twold | grep status | awk '{print $6}'`
        twoldnotneeded="via-2ld"
    fi
    echo "$name,$thens,$thestatus,$twoldnotneeded"
    sleep 1
done
