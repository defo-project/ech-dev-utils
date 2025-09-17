#!/bin/bash
#
# Do some ECH key management tests with haproxy via the `stats` socket

# set -x

# The starting point is a server with the following ECH setup at startup:
#
#  $socat /tmp/haproxy.sock stdio
#  prompt
#  
#  > show ssl ech
#  ***
#  frontend: ECH-front
#  ECH entry: 0 public_name: example.com age: 48 (has private key)
#          [fe0d,84,example.com,[0020,0001,0001],1a53b49ab895381ea59f98cc4ce305a3cfbc4e358b08ba41c212cd0245b1b02e,00,00]
#  
#  ECH entry: 1 public_name: example.com age: 48 (has private key)
#          [fe0d,13,example.com,[0020,0001,0001],890db6cfe8de866cd4d04fabfd7301ad4fc6148060a9a8baa23670e7b1320020,00,00]
#  ***
#  frontend: Two-TLS
#  ECH entry: 0 public_name: example.com age: 48 (has private key)
#          [fe0d,84,example.com,[0020,0001,0001],1a53b49ab895381ea59f98cc4ce305a3cfbc4e358b08ba41c212cd0245b1b02e,00,00]
#  
#  ECH entry: 1 public_name: example.com age: 48 (has private key)
#          [fe0d,13,example.com,[0020,0001,0001],890db6cfe8de866cd4d04fabfd7301ad4fc6148060a9a8baa23670e7b1320020,00,00]

# settings
# to pick up correct .so's etc
: ${OSSL:="$HOME/code/openssl-upstream-master"}

# list of public names for new keys
: ${PUBS:="eg1.com eg2.com"}

# list of frontends
: ${FRONTS="ECH-front Two-TLS"}

# number of private keys for each public name
: ${NPRIVS:="3"}

# whether to leave stuff in place on exit
: ${INPLACE:="no"}

# socket name
: ${SOCKNAME:="/tmp/haproxy.sock"}

export LD_LIBRARY_PATH=$OSSL

function socatty()
{
    echo "$1" | socat /tmp/haproxy.sock -
}

function addcatty()
{
    front=$1
    pf=$2
    echo -e "add ssl ech $front <<EOF\n$(cat $pf)\nEOF\n" | socat /tmp/haproxy.sock -
}

function setcatty()
{
    front=$1
    pf=$2
    echo -e "set ssl ech $front <<EOF\n$(cat $pf)\nEOF\n" | socat /tmp/haproxy.sock -
}

# work in a temp dir
tdir=$(mktemp -d)
cd $tdir

# generate a pile of keys
for front in $FRONTS
do
   for pub in $PUBS
   do
       for ((i=0;i!=$NPRIVS;i++))
      do
          $OSSL/apps/openssl ech -public_name $pub -out $front-$pub-$i.pem.ech
      done
  done
done 

echo "initial config all in one"
socatty "show ssl ech"

echo "show one at a time"
for front in $FRONTS
do
    socatty "show ssl ech $front"
done

echo "delete one at a time"
for front in $FRONTS
do
    socatty "del ssl ech $front"
done

echo "add a pile of keys incrementally"
for front in $FRONTS
do
   for pub in $PUBS
   do
       for ((i=0;i!=$NPRIVS;i++))
      do
          addcatty $front $front-$pub-$i.pem.ech
      done
  done
done 
socatty "show ssl ech"

ecoh "set  a key on each, overwritingly"
for front in $FRONTS
do
   for pub in $PUBS
   do
       for ((i=0;i!=$NPRIVS;i++))
      do
          setcatty $front $front-$pub-$i.pem.ech
      done
  done
done 
socatty "show ssl ech"

echo "sleep a bit"
sleep 2

echo "delete nothing - age too big"
for front in $FRONTS
do
    socatty "del ssl ech $front 10"
done
socatty "show ssl ech"

echo "add a pile of keys incrementally"
for front in $FRONTS
do
   for pub in $PUBS
   do
       for ((i=0;i!=$NPRIVS;i++))
      do
          addcatty $front $front-$pub-$i.pem.ech
      done
  done
done 
socatty "show ssl ech"

echo "sleep a bit"
sleep 2

echo "delete some - age too big"
for front in $FRONTS
do
    socatty "del ssl ech $front 3"
done
socatty "show ssl ech"

echo "delete all"
for front in $FRONTS
do
    socatty "del ssl ech $front 0"
done
socatty "show ssl ech"

# clean up
if [[ "$INPLACE" != "yes" ]]
then
    rm -rf $tdir
fi
