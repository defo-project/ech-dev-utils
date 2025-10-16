#!/bin/bash
#
# Given an echdomains.csv file, for each line with an ech=
# value, for each unique test name, output the last line
# where that name was used and ECH worked

INFILE="echdomains.csv"

names=$(cat "$INFILE" | awk -F'|' '{print $2}' | sort | uniq)

for name in $names
do
    lastline=$(awk -v aname="$name" -F'|' '$2==aname && $3==1 {line=$0}END{print line}' "$INFILE")
    if [[ "$lastline" != "" ]]
    then
        echo $lastline
    fi
done

