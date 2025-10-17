#!/bin/bash
#
# Given an echdomains.csv file, report on domains where
# ECH once worked but seemingly no longer does

INFILE="echdomains.csv"

names=$(cat "$INFILE" | grep "ech=" | awk -F'|' '{print $2}' | sort | uniq)

for name in $names
do
    firstgoodline=$(awk -v aname="$name" -F'|' '$2==aname && $3==1 {print $0}' "$INFILE" | head -1)
    lastbadline=$(awk -v aname="$name" -F'|' '$2==aname && $3==0 {line=$0}END{print line}' "$INFILE")
    lastgoodline=$(awk -v aname="$name" -F'|' '$2==aname && $3==1 {line=$0}END{print line}' "$INFILE")

    if [[ "$firstgoodline" == "" ]]
    then
        continue
    fi
    if [[ "$lastbadline" == "" ]]
    then
        continue
    fi
    # lexicographic order is fine - lines start with date strings
    if [[ "$lastbadline" > "$lastgoodline" ]]
    then
        echo "$lastbadline|$firstgoodline"
    fi
done

