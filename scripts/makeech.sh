#!/bin/bash

# set -x

# wrapper to make an ECH PEMfile with the given parameters, which'll usually
# be -public_name and perhaps some alg ids, regardless of whether or not the
# installed openssl supports ECH or we have a local build

# installed one
: ${OSSL:=$(which openssl)}
# local build
: ${OBUILD:=$HOME/code/defo-project-org/openssl}

$OSSL ech -help >/dev/null 2>&1
res=$?
if [[ "$res" != "0" ]]
then
    if [ ! -d $OBUILD ]
    then
        echo "openssl doesn't support ECH sorry"
        exit 99
    fi
    if [[ -f $OBUILD/libssl.so && -f $OBUILD/apps/openssl ]]
    then
        export LD_LIBRARY_PATH=$OBUILD
        OSSL=$OBUILD/apps/openssl
        $OSSL ech -help >/dev/null 2>&1
        res=$?
        if [[ "$res" != "0" ]]
        then
            echo "local openssl doesn't support ECH sorry"
            exit 99
        fi
    fi
fi
if [[ $* == *pemout* ]]
then
    $OSSL ech $*
else
    tmpf=$(mktemp)
    $OSSL ech $* -pemout $tmpf
    cat $tmpf
    rm -f $tmpf
fi
