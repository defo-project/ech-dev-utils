#!/bin/bash

# Script to run basic tests using the openssl command line tool.
# Equivalent tests should migrate to being run as part of ``make test``

# to pick up correct .so's - maybe note
: ${CODETOP:=$HOME/code/openssl}
export LD_LIBRARY_PATH=$CODETOP
: ${RUNTOP:="."}
: ${GETOPTDIR:=/usr/bin}
# DNS recursive to use (don't ask:-)
: ${DNSRECURSIVE=""}

# Path to openssl binary
if [[ "$PACKAGING" == "" ]]
then
    CMDPATH=$CODETOP/apps/openssl
else
    CMDPATH=`which openssl`
    set -ex
fi

# variables/settings
# use Valgrind or not
VG="no"
# print loads or not
DEBUG="no"
# run without doing ECH at all
NOECH="no"
# whether or not to grease (only makes sense with NOECH==yes)
GREASE="no"
# the specific HPKE suite to use for grease, if so instructed
GSUITE="0x20,1,1"
GSUITESET="no"
# GTYPE="65034" # that's 0xfe0a - for draft-10
GTYPE_DEF="65037" # that's 0xfe0d - for draft-13
GTYPE=$GTYPE_DEF

# Protocol parameters

# note that cloudflare do actually turn on h2 if we ask for that so
# you might see binary cruft if that's selected
DEFALPNOUTER="outer,public,h2"
DEFALPNINNER="inner,secret,http/1.1"
DEFALPNVAL=" -ech_alpn_outer $DEFALPNOUTER -alpn $DEFALPNINNER"
DOALPN="yes"
SUPPALPN=""

# default port
PORT="443"
# port from commeand line
SUPPLIEDPORT=""
# outer SNI to use
SUPPLIEDOUTER=""
# HTTPPATH="index.html"
HTTPPATH=""

# the name or IP of the host to which we'll connect
SUPPLIEDSERVER=""
# the name that we'll put in inne CH - the ECH/SNI
SUPPLIEDHIDDEN=""

# PNO is the public_name_override that'll be sent as clear_sni
SUPPLIEDPNO=""
SUPPLIEDWAIT=""

# ECH (or filename) from command line
SUPPLIEDECH=""

# CA info for server
SUPPLIEDCADIR=""

# stored session
SUPPLIEDSESSION=""
# re-using a session allows early data, so note that, if so
REUSINGSESSION="no"

# test with bogus custom extensions
TESTCUST="no"

# default values
HIDDEN="cloudflare-ech.com"
DEFFRAG="cdn-cgi/trace" # what CF like for giving a hint as to whether ECH worked
PNO=""
CAPATH="/etc/ssl/certs/"
CAFILE="$RUNTOP/cadir/oe.csr"
REALCERT="no" # default to fake CA for localhost
CIPHERSUITES="" # default to internal default
HRR="no" # default to not trying to force HRR
SELECTED=""
IGNORE_CID="no"
EARLY_DATA="no"
IP_PROTSEL=""


function whenisitagain()
{
    /bin/date -u +%Y%m%d-%H%M%S
}
NOW=$(whenisitagain)

function getb64ech()
{
    rrval=$1
    echb64=""
    for substr in $rrval
    do
        if [[ $substr == ech=* ]]
        then
            echb64=${substr:4}
        fi
    done
    echo $echb64
}

echo "Running $0 at $NOW"

function usage()
{
    echo "$0 [-cdfgGhHPpsRrnlvL] [-- [literal s_client opts]]- try out encrypted client hello (ECH) via openssl s_client"
    echo "  -4 use IPv4"
    echo "  -6 use IPv6"
    echo "  -a [alpn-str] specifies a comma-sep list of alpn values"
    echo "  -c [name] specifices a name that I'll send as an outer SNI (NONE is special)"
    echo "  -C [number] selects the n-th ECHConfig from input RR/PEM file (0 based)"
    echo "  -d means run s_client in verbose mode"
    echo "  -e means send HTTP request (in ./ed_file) as early_data"
    echo "  -f [pathname] specifies the file/pathname to request (default: '/')"
    echo "  -g means GREASE (only applied with -n)"
    echo "  -G means set GREASE suite to default rather than randomly pick"
    echo "  -h means print this"
    echo "  -H [name] means try connect to that hidden server"
    echo "  -I means to ignore the server's chosen config_id and send random"
    echo "  -j just use 0x1301 ciphersuite"
    echo "  -n means don't trigger ech at all"
    echo "  -N means don't send specific inner/outer alpns"
    echo "  -O [name} means to use that name as the outer SNI"
    echo "  -p [port] specifices a port (default: 443)"
    echo "  -P [filename] means read ECHConfigs public value from file and not DNS"
    echo "  -r (or --realcert) says to not use locally generated fake CA regardless"
    echo "  -R try force HRR by preferring P-384 over X2519"
    echo "  -s [name] specifices a server to which I'll connect (localhost=>local certs, unless --realcert)"
    echo "  -S [file] means save or resume session from <file>"
    echo "  -t [type] means to set the TLS extension type for GREASE to <type>"
    echo "  -T [test_cust] means to test use of bogus CH custom exts"
    echo "  -v means run with valgrind"
    echo "  -- anything after -- is passed directly to s_client"

    echo ""
    echo "The following should work:"
    echo "    $0 -H defo.ie"
    exit 99
}

# check we have what looks like a good getopt (the native version on macOS
# seems to not be good)
if [ ! -f $GETOPTDIR/getopt ]
then
    echo "No sign of $GETOPTDIR/getopt - exiting"
    exit 32
fi
getoptcnt=`$GETOPTDIR/getopt --version | grep -c "util-linux"` || true
if [[ "$getoptcnt" != "1" ]]
then
    echo "$GETOPTDIR/getopt doesn't seem to be gnu-getopt - exiting"
    exit 32
fi

# options may be followed by one colon to indicate they have a required argument
if ! options=$($GETOPTDIR/getopt -s bash -o 46a:C:c:def:gGhH:IjnNO:p:P:Rrs:S:t:Tvw: -l four,six,alpn,choose:,clear_sni:,debug,early,filepath:,grease,greasesuite,help,hidden:,ignore_cid,just,noech,noalpn,outer:,port:,echpub:,hrr,realcert,server:,session:,gtype:,test_cust,valgrind,wait: -- "$@")
then
    # something went wrong, getopt will put out an error message for us
    exit 1
fi
#echo "|$options|"
eval set -- "$options"
while [ $# -gt 0 ]
do
    case "$1" in
        -4|--four) IP_PROTSEL=" -4 ";;
        -6|--six) IP_PROTSEL=" -6 ";;
        -a|--alpn) SUPPALPN=$2; shift;;
        -c|--clear_sni) SUPPLIEDPNO=$2; shift;;
        -C|--choose) SELECTED=$2; shift;;
        -d|--debug) DEBUG="yes" ;;
        -e|--early) EARLY_DATA="yes" ;;
        -f|--filepath) HTTPPATH=$2; shift;;
        -g|--grease) GREASE="yes";;
        -G|--greasesuite) GSUITESET="yes";;
        -h|--help) usage;;
        -H|--hidden) SUPPLIEDHIDDEN=$2; shift;;
        -I|--ignore_cid) IGNORE_CID="yes" ;;
        -j|--just) CIPHERSUITES=" -ciphersuites TLS_AES_128_GCM_SHA256 " ;;
        -n|--noech) NOECH="yes" ;;
        -N|--noalpn) DOALPN="no" ;;
        -O|--outer) SUPPLIEDOUTER=$2; shift;;
        -p|--port) SUPPLIEDPORT=$2; shift;;
        -P|--echpub) SUPPLIEDECH=$2; shift;;
        -r|--realcert) REALCERT="yes" ;;
        -R|--hrr) HRR="yes" ;;
        -s|--server) SUPPLIEDSERVER=$2; shift;;
        -S|--session) SUPPLIEDSESSION=$2; shift;;
        -t|--gtype) GTYPE=$2; shift;;
        -T|--test_cust) TESTCUST="yes" ;;
        -v|--valgrind) VG="yes" ;;
        -w|--wait) SUPPLIEDWAIT=$2; shift;;
        (--) shift; break;;
        (-*) echo "$0: error - unrecognized option $1" 1>&2; exit 1;;
        (*)  break;;
    esac
    shift
done

hidden=$HIDDEN
if [[ "$SUPPLIEDHIDDEN" != "" ]]
then
    hidden=$SUPPLIEDHIDDEN
fi

# figure out if we have tracing enabled within OpenSSL
# there's probably an easier way but s_client -help
# ought work
TRACING=""
tmpf=`mktemp`
$CMDPATH s_client -help >$tmpf 2>&1
tcount=`grep -c 'trace output of protocol messages' $tmpf` || true
if [[ "$tcount" == "1" ]]
then
    TRACING="-trace "
fi
rm -f $tmpf

# prefer kdig over dig for now... dig crashing on exit sometimes
# DIGCMD='dig'
DIGCMD='kdig'
# check we have $DIGCMD
if [[ "``which $DIGCMD``" == "" ]]
then
    echo "Can't find the $DIGCMD command - exiting"
    exit 12
fi

#dbgstr=" -verify_quiet"
dbgstr=" "
#dbgstr=" "
if [[ "$DEBUG" == "yes" ]]
then
    # least to most...
    #dbgstr="-msg -debug $TRACING"
    dbgstr="-msg -debug $TRACING -tlsextdebug"
    #dbgstr="-msg -debug $TRACING -tlsextdebug -keylogfile keys.cli"
    #dbgstr="-msg -debug $TRACING -security_debug_verbose -state -tlsextdebug -keylogfile cli.keys"
fi

if [[ "$TESTCUST" == "yes" ]]
then
    tcust=" -ech_custom"
fi

hrrstr=""
if [[ "$HRR" == "yes" ]]
then
    hrrstr=" -groups P-384:X25519 "
fi

vgcmd=""
if [[ "$VG" == "yes" ]]
then
    #vgcmd="valgrind --leak-check=full "
    vgcmd="valgrind --leak-check=full --error-limit=no --track-origins=yes "
fi

if [[ "$SUPPLIEDPORT" != "" ]]
then
    PORT=$SUPPLIEDPORT
fi

snioutercmd=" "
if [[ "$SUPPLIEDPNO" != "" && "$NOECH" != "yes" ]]
then
    snioutercmd="-sni_outer $SUPPLIEDPNO"
fi

# Set address of target
if [[ "$SUPPLIEDPNO" != "" && "$hidden" == "" ]]
then
    target=" -connect $SUPPLIEDPNO:$PORT "
else
    # I guess we better connect to hidden
    # Note that this could leak via DNS again
    target=" -connect $hidden:$PORT "
fi
server=$hidden
if [[ "$SUPPLIEDSERVER" != "" ]]
then
    target=" -connect $SUPPLIEDSERVER:$PORT"
    server=$SUPPLIEDSERVER
fi

selstr=""
if [[ "$SELECTED" != "" ]]
then
    selstr=" -ech_select $SELECTED "
fi

# set ciphersuites
ciphers=$CIPHERSUITES

if [[ "$NOECH" == "no" && "$GREASE" == "no" ]]
then
    if [[ "$SUPPLIEDECH" != "" ]]
    then
        if [ ! -f $SUPPLIEDECH ]
        then
            echo "Assuming supplied ECH is encoded ECHConfigList or SVCB"
            ECH=" $selstr -ech_config_list $SUPPLIEDECH "
        else
            # check if file suffix is .pem (base64 encoding)
            # and react accordingly, don't take any other file extensions
            ssfname=`basename $SUPPLIEDECH`
            if [ `basename "$ssfname" .pem` != "$ssfname" ]
            then
                ECH=" $selstr -ech_config_list `cat $SUPPLIEDECH | sed '/BEGIN ECHCONFIG/,/END ECHCONFIG/{//!b};d' | tr -d '\n'`"
            else
                echo "Not sure of file type of $SUPPLIEDECH - try make a PEM file to help me"
                exit 8
            fi
        fi
    else
        # try draft-13 only for now, i.e. HTTPS
        # kill the spaces and joing the lines if multi-valued seen
        qname=$hidden
        if [[ "$PORT" != "" && "$PORT" != "443" ]]
        then
            qname="_$PORT._https.$hidden"
        fi
        recursivestr=""
        if [[ "$DNSRECURSIVE" != "" ]]
        then
            echo "Using DNS recursive: $DNSRECURSIVE"
            recursivestr=" @$DNSRECURSIVE "
        fi
        # check if we're in aliasMode or serviceMode (priority 0 is the former, other the latter)
        priority=`$DIGCMD +short -t TYPE65 $qname | awk '{print $1}'`
        if [[ "$priority" == "0" ]]
        then
            # aliasMode - we'll do one level of indirection only
            qname=`$DIGCMD +short -t TYPE65 $qname | awk '{print $2}'`
            if [[ "$PORT" != "" && "$PORT" != "443" ]]
            then
                qname="_$PORT._https.$qname"
            fi
            digrrval=`$DIGCMD +short $recursivestr -t TYPE65 $qname`
            digval=$(getb64ech "$digrrval")
        else
            digrrval=`$DIGCMD +short $recursivestr -t TYPE65 $qname`
            digval=$(getb64ech "$digrrval")
        fi

        if [[ "$digval" == "" ]]
        then
            echo "Didn't get any HTTPS RR value for $qname - exiting"
            exit 22
        fi
        ECH=" $selstr -ech_config_list $digval "
    fi
fi

if [[ "$NOECH" == "no" && "$GREASE" == "no" && "$ECH" == "" ]]
then
    echo "Not trying - no sign of ECHKeys ECH "
    exit 100
fi

if [[ "$GTYPE" == "$GTYPE_DEF" ]]
then
    grease_str=" -ech_grease "
else
    grease_str=" -ech_grease -ech_grease_type=$GTYPE"
fi
if [[ "$GSUITESET" == "yes" ]]
then
    grease_str=" $grease_str -ech_grease_suite=$GSUITE"
fi

ignore_str=" "
if [[ "$IGNORE_CID" == "yes" ]]
then
    ignore_str=" -ech_ignore_cid "
fi

# normally the inner SNI is what we want to hide
echstr="-servername $hidden $ECH $ignore_str "
if [[ "$NOECH" == "yes" ]]
then
    echo "Not trying ECH"
    if [[ "$SUPPLIEDPNO" != "" ]]
    then
        echstr="-servername $SUPPLIEDPNO $ignore_str "
    elif [[ "$SUPPLIEDPNO" == "" && "$hidden" != "" ]]
    then
        echstr="-servername $hidden $ignore_str "
    elif [[ "$hidden" == "" || "$SUPPLIEDPNO" == "NONE" ]]
    then
        echstr=" -noservername $ignore_str"
    fi
    if [[ "$GREASE" == "yes" ]]
    then
        echo "Trying to GREASE though"
        echstr=" $echstr $grease_str $ignore_str "
    fi
else
    if [[ "$GREASE" == "yes" && "$hidden" == "NONE" ]]
    then
        echo "Trying to GREASE"
        echstr=" -noservername $grease_str $ignore_str "
    elif [[ "$GREASE" == "yes" && "$hidden" != "NONE" ]]
    then
        echstr=" -servername $hidden $grease_str $ignore_str "
    elif [[ "$GREASE" == "no" && "$hidden" != "NONE" ]]
    then
        echstr=" -servername $hidden $ECH $ignore_str "
    elif [[ "$GREASE" == "no" && "$hidden" == "NONE" ]]
    then
        echstr=" -noservername $ECH $ignore_str "
    fi
fi

if [[ "$SUPPLIEDOUTER" != "" ]]
then
    # add that parameter to echstr - not all cases will make
    # sense but that's ok
    echstr="$echstr -sni_outer $SUPPLIEDOUTER"
fi

if [[ "$NOECH" == "no" && "$SUPPLIEDHIDDEN" == "" && "$HTTPPATH" == "" ]]
then
    # we're at CF, set things to work nicely
    HTTPPATH=$DEFFRAG
    DOALPN="no"
fi

#httpreq="GET $HTTPPATH\\r\\n\\r\\n"
httphost=$hidden
if [[ "$NOECH" == "yes" ]]
then
    if [[ "$SUPPLIEDPNO" != "" ]]
    then
        httphost=$SUPPLIEDPNO
    elif [[ "$SUPPLIEDSERVER" != "" ]]
    then
        httphost=$SUPPLIEDSERVER
    else
        httphost="localhost"
    fi
fi
# httpreq="GET /$HTTPPATH HTTP/1.1\\r\\nConnection: close\\r\\nHost: $httphost\\r\\n\\r\\n"
# 2025-02-26: the request below seems to include an extra \\r\\n causing an extra log line
# in nginx (at least)
# httpreq="GET /$HTTPPATH HTTP/1.1\\r\\nConnection: keep-alive\\r\\nHost: $httphost\\r\\n\\r\\n"
httpreq="GET /$HTTPPATH HTTP/1.1\\r\\nConnection: keep-alive\\r\\nHost: $httphost\\r\\n"

# tell it where CA stuff is...
if [[ "$server" != "localhost" ]]
then
    certsdb=" -CApath $CAPATH"
else
    if [[ "$REALCERT" == "no" && -f $CAFILE ]]
    then
        certsdb=" -CAfile $CAFILE"
    else
        certsdb=" -CApath $CAPATH"
    fi
fi

# force tls13
force13="-no_ssl3 -no_tls1 -no_tls1_1 -no_tls1_2"
#force13="-cipher TLS13-AES-128-GCM-SHA256 -no_ssl3 -no_tls1 -no_tls1_1 -no_tls1_2"
#force13="-tls1_3 -cipher TLS13-AES-128-GCM-SHA256 "

# session resumption
session=""
if [[ "$SUPPLIEDSESSION" != "" ]]
then
    if [ ! -f $SUPPLIEDSESSION ]
    then
        # save so we can resume
        session=" -sess_out $SUPPLIEDSESSION"
    else
        # resuming
        session=" -sess_in $SUPPLIEDSESSION"
        REUSINGSESSION="yes"
    fi
fi

alpn=""
if [[ "$DOALPN" == "yes" && "$NOECH" == "no" ]]
then
    if [[ "$GREASE" == "yes" ]]
    then
        alpn=" -alpn $DEFALPNINNER"
    else
        alpn=$DEFALPNVAL
    fi
fi
if [[ "$SUPPALPN" != "" ]]
then
    # override above
    alpn=" -alpn $SUPPALPN"
fi

earlystr=""
if [[ "$EARLY_DATA" == "yes" ]]
then
    if [[ "$REUSINGSESSION" != "yes" ]]
    then
        echo "Can't send early data unless re-using a session"
        exit 87
    fi
    if [ ! -f ed_file ]
    then
        echo -e "$httpreq\n" >ed_file
    fi
    earlystr=" -early_data ed_file "
fi

TMPF=`mktemp /tmp/echtestXXXX`

if [[ "$DEBUG" == "yes" ]]
then
    echo "HTTP REQ: $httpreq"
    echo "Running: $CMDPATH s_client $IP_PROTSEL $dbgstr $certsdb $force13 $target $echstr $snioutercmd $session $alpn $ciphers $earlystr $tcust $hrrstr"
fi
# seconds to sleep after firing up client so that tickets might arrive
sleepaftr=2

if [[ "$SUPPLIEDWAIT" != "" ]]
then
    sleepaftr="$SUPPLIEDWAIT"
else
    if [[ "$DEBUG" == "yes" ]]
    then
        # bit slower so sleep a bit more
        sleepaftr=8
    fi
    if [[ "$VG" == "yes" ]]
    then
        # bit slower so sleep a bit more
        sleepaftr=6
    fi
fi

if [[ "$EARLY_DATA" == "yes" ]]
then
    httpreq1=${httpreq/foo.example.com/barbar.example.com}
    ( echo -e "$httpreq1" ; sleep $sleepaftr) | $vgcmd $CMDPATH s_client $IP_PROTSEL $dbgstr $certsdb $force13 $target $echstr $snioutercmd $session $alpn $ciphers $earlystr $tcust $hrrstr $@ >$TMPF 2>&1
else
    ( echo -e "$httpreq" ; sleep $sleepaftr) | $vgcmd $CMDPATH s_client $IP_PROTSEL $dbgstr $certsdb $force13 $target $echstr $snioutercmd $session $alpn $ciphers $tcust $hrrstr $@ >$TMPF 2>&1
fi

c200=`grep -c "200 OK" $TMPF` || true
csucc=`grep -c "ECH: success" $TMPF` || true
c4xx=`grep -ce "^HTTP/1.1 4[0-9][0-9] " $TMPF` || true
if [[ "$DEBUG" == "yes" ]]
then
    echo "$0 All output"
    cat $TMPF
    echo ""
fi
if [[ "$VG" == "yes" ]]
then
    vgout=`grep -e "^==" $TMPF`
    echo "$0 Valgrind"
    echo "$vgout"
    echo ""
fi
if [[ "$GREASE" == "yes" ]]
then
  goodresult=`grep -c "ECH: only greasing, and got ECH in return" $TMPF` || true
else
  goodresult=`grep -c "ECH: success" $TMPF` || true
fi
echo "$0 Summary: "
allresult=`grep "ECH: " $TMPF`
# check if we saw any OpenSSL Errors, except we ignore
# any related to fopen that can happen if/when we ask
# an openssl s_server, for a file it doesn't have or if
# the server's running in the wrong mode
sslerror=""
sslerrorcount=`grep -c ":error:" $TMPF` || true
if [[ "$sslerrorcount" != "0" ]]
then
    sslerror=`grep ":error:" $TMPF \
             | grep -v BIO_new_file \
             | grep -v NCONF_get_string \
             | grep -v "error:8000000" ` || true
fi
rm -f $TMPF
if (( $goodresult > 0 ))
then
    echo "Looks like ECH worked ok"
    res=0
else
    if [[ "$NOECH" != "yes" && "$GREASE" != "yes" ]]
    then
        echo "Bummer - probably didn't work"
        res=1
    elif [[ "$NOECH" == "yes" ]]
    then
        echo "Didn't try ECH"
        res=0
    elif [[ "$GREASE" == "yes" ]]
    then
        echo "Only greased"
        res=0
    fi
fi
if [[ "$sslerror" != "" ]]
then
    echo "Got an SSL error though:"
    echo "$sslerror"
    res=1
fi
echo $allresult
exit $res
