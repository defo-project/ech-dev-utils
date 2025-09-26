#!/bin/bash
#
# A script to make an ECH PEM file according to the Internet-draft
# https://datatracker.ietf.org/doc/draft-farrell-tls-pemesni/
# using the boringssl command line tool (the OpenSSL command line
# tool emits this format by itself)

set -e

: "${BSSL:=$PWD/bssl}" # boringssl binary
: "${PN:=example.com}" # public name
: "${CID:=$((RANDOM%256))}"  # config_id
: "${PEMF:=$PWD/echconfig.pem}" # output ECH PEM file

sdir="$PWD"
tdir=$(mktemp -d)
cd "$tdir" || exit
$BSSL generate-ech -public-name "$PN" -config-id "$CID" \
    -out-private-key priv.ech -out-ech-config-list pub.ech \
    -out-ech-config foo -max-name-length 0
PRIV=$(cat priv.ech | base64)
ECL=$(cat pub.ech | base64)

cat >"$PEMF" <<EOF
-----BEGIN PRIVATE KEY-----
$PRIV
-----END PRIVATE KEY-----
-----BEGIN ECHCONFIG-----
$ECL
-----END ECHCONFIG-----
EOF
cd "$sdir" || exit
rm -rf "$tdir"

