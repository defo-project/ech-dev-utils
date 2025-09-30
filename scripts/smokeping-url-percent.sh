#!/bin/bash

# Count the successes/fails per URL in a set of runs of our ECH smokeping
# interop test CSV outputs

# directories that contain result CSVs, each datestamped directory has a
# CSV file, e.g. 20250929-132002/20250929-132002.csv
dirnames="2025*"

# place for results
resfile="big.csv"

# the oddball ones here are chromium specific
good1="expected"
good2="expected exception: Message: unknown error: net::ERR_INVALID_ECH_CONFIG_LIST"
good3="expected exception: Message: unknown error: net::ERR_NAME_NOT_RESOLVED"
good4="expected exception: Message: unknown error: net::ERR_SSL_PROTOCOL_ERROR"
bad1="fail"
bad2="unexpected exception: "
bad3="unexpected exception: Message: unknown error: net::ERR_ECH_FALLBACK_CERTIFICATE_INVALID"
bad4="unexpected exception: Message: unknown error: net::ERR_ECH_NOT_NEGOTIATED"
bad5="unexpected exception: Message: unknown error: net::ERR_NAME_NOT_RESOLVED"

# first 2 columns: test-number, URL
cols12=$(mktemp)
# join on column 3 of CSV result files
resultcols=$(mktemp)
total=0
for dir in $dirnames
do
    tmpf=$(mktemp)
    tmpf1=$(mktemp)
    csvf="$dir/$dir.csv"
    echo "$dir" >"$tmpf"
    tail -n +2 "$csvf" | awk -F, '{print $3}' >>"$tmpf"
    if [ -s "$resultcols" ]
    then
        paste -d ',' "$resultcols" "$tmpf" >"$tmpf1"
        rm -f "$tmpf"
        total=$((total+1))
    else
        mv "$tmpf" "$tmpf1"
        # grab first columns once, they're the same
        awk -F, '{print $1","$2}' "$csvf" >"$cols12"
    fi
    mv "$tmpf1" "$resultcols"
done

# strings to 0/1 results, could be generalised later
tmpf=$(mktemp)
cat "$resultcols" | sed -e "s/$bad5/0/g" >"$tmpf"
mv "$tmpf" "$resultcols"
cat "$resultcols" | sed -e "s/$bad4/0/g" >"$tmpf"
mv "$tmpf" "$resultcols"
cat "$resultcols" | sed -e "s/$bad3/0/g" >"$tmpf"
mv "$tmpf" "$resultcols"
cat "$resultcols" | sed -e "s/$bad2/0/g" >"$tmpf"
mv "$tmpf" "$resultcols"
cat "$resultcols" | sed -e "s/$bad1/0/g" >"$tmpf"
mv "$tmpf" "$resultcols"
cat "$resultcols" | sed -e "s/$good4/1/g" >"$tmpf"
mv "$tmpf" "$resultcols"
cat "$resultcols" | sed -e "s/$good3/1/g" >"$tmpf"
mv "$tmpf" "$resultcols"
cat "$resultcols" | sed -e "s/$good2/1/g" >"$tmpf"
mv "$tmpf" "$resultcols"
cat "$resultcols" | sed -e "s/$good1/1/g" >"$tmpf"
mv "$tmpf" "$resultcols"

echo "total,successes,percent" >"$tmpf"
firstline=1
while IFS= read -r line; do
    if [ "$firstline" != "1" ]
    then
        successes=$(echo "$line" | sed -e 's/,/\n/g' | grep -c 1)
        percent=$((100*successes/total))
        echo "$total,$successes,$percent" >>"$tmpf"
    else
        firstline=0
    fi
done < "$resultcols"

# finally put 'em together
paste -d ',' "$cols12" "$tmpf" "$resultcols" >"$resfile"
rm -f "$cols12" "$tmpf" "$resultcols"
tail -n +2 "$resfile" | awk -F, '{print $5,$2}' | sort -n
