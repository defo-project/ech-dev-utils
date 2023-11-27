# Haproxy and ECH

Our fork is from https://github.com/haproxy/haproxy

This text, and associated scripts/configs, are still being fixed to work in
this repo. So take it all with a pinch of salt for the moment.

## Build

We assume you've already built our OpenSSL fork in ``$HOME/code/openssl`` and
have gotten the [localhost-tests](localhost-tests.md) working, and you
should have created an ``echkeydir`` as described [here](../README.md#server-configs-preface---key-rotation-and-slightly-different-file-names).

You need our haproxy fork and to use the ``ECH-experimental`` branch from that,
so...

```bash
    $ cd $HOME/code
    $ git clone https://github.com/sftcd/haproxy.git
    $ cd haproxy
    $ git checkout ECH-experimental
    $ export OSSL=$HOME/code/openssl
    $ export LD_LIBRARY_PATH=$OSSL
    $ make V=1  SSL_INC=$OSSL/include/ SSL_LIB=$OSSL TARGET=linux-glibc \
        USE_OPENSSL=1 DEFINE="-DOPENSSL_SUPPRESS_DEPRECATED -DDEBUG -O0 \
        -DUSE_ECH"
```

## Configuration

We followed this haproxy
[configuration guide](https://www.haproxy.com/blog/the-four-essential-sections-of-an-haproxy-configuration/).

Compared to other web servers, haproxy configuration is a bit more involved as
our integration supports both split-mode and shared mode ECH, and haproxy, not
being a web server, also needs a backend web server configured.

ECH shared-mode in haproxy terms is where the haproxy frontend is a TLS
terminator and does all the ECH and TLS work before handing off a cleartext
HTTP request to a backend web server. If desired, a new TLS session can be 
used to protect the HTTP request, as is normal for haproxy.

Split-mode is where the frontend does the ECH decryption but doesn't terminate
the client's TLS session.

If split-mode decryption fails or no ECH extension is present, then haproxy
should be configured to forward to a backend that has the private key
corresponding to the ``ECHConfig.public_name``. If decryption works, then
haproxy will forward the inner CH, routing the request based on the SNI from
that inner CH. 

Our test script is [testhaproxy.sh](../scripts/testhaproxy.sh) with our minimal
config in [haproxymin.conf](../configs/haproxymin.conf).  The test script
starts lighttpd as needed to act as the back-end web server. (You'll need to
manually kill that when done with it.)

A typical pre-existing haproxy config for terminating TLS will include lines
like the following for listeners in "http mode":

```bash
    bind :7443 ssl crt cadir/foo.example.com.pem
```

We extend that to support ECH shared mode via the ECH keyword that can be
followed by a filename or directory name, e.g.:

```bash
    bind :7443 ech echconfig.pem ssl crt cadir/foo.example.com.pem
```

If the ech keyword names a file, that'll be loaded and work if it's a correctly
encoded ECH PEM file. If the keyword names a directory, then that directory
will be scanned for all ``*.ech`` files.

For split-mode, we added an ``ech-decrypt`` keyword to allow configuring the
PEM file or directory with the ECH key pair(s). That keyword can be added to
a "tcp mode" frontend configuration, e.g.:

```bash
    tcp-request ech-decrypt echkeydir
```

## Test

The [testhaproxy.sh](../scripts/testhaproxy.sh) script starts servers and
optionally runs clients against those. If needed, a lighttpd backend web server
is started using
[lighttpd4haproxymin.conf](../configs/lighttpd4haproxymin.conf).

The set of ports used is as follows:

- haproxy listens on 7443 in ECH shared mode, passing cleartext requests on to
  lighttpd listening on port 3480
- haproxy listens on 7444 in ECH shared mode, passing TLS-protected requests (via
  a 2nd TLS session) on to lighttpd listening on port 3481
- haproxy listens on 7445 doing no ECH processing, passing all TLS data on to
  lighttpd listening on port 3482
- haproxy listens on 7446 in ECH split mode, passing TLS-protected requests
  (via a 2nd TLS session) on to lighttpd listening on port 3484 (if ECH 
  decryption worked), or 3485 if ECH decryption failed or no ECH extension
  was present

```bash
    $ cd $HOME/lt
    $ $HOME/code/ech-dev-utils/scripts/testhaproxy.sh
    ...stuff... # hit ctrl-C to exit haproxy, killall lighttpd to kill backend
    $ # split-mode test
    $ $HOME/code/ech-dev-utils/scripts/echcli.sh -s localhost  -H foo.example.com -p 7446 -P echconfig.pem -f index.html
    Running /home/user/code/ech-dev-utils/scripts/echcli.sh at 20230315-154634
    Assuming supplied ECH is encoded ECHConfigList or SVCB
    /home/user/code/ech-dev-utils/scripts/echcli.sh Summary: 
    Looks like ECH worked ok
    ECH: success: outer SNI: 'example.com', inner SNI: 'foo.example.com'
    $ # shared-mode test
    $ $HOME/code/ech-dev-utils/scripts/echcli.sh -s localhost  -H foo.example.com -p 7445 -P echconfig.pem -f index.html
    Running /home/user/code/ech-dev-utils/scripts/echcli.sh at 20230315-154900
    Assuming supplied ECH is encoded ECHConfigList or SVCB
    /home/user/code/ech-dev-utils/scripts/echcli.sh Summary: 
    Looks like ECH worked ok
    ECH: success: outer SNI: 'example.com', inner SNI: 'foo.example.com'
```

[testhaproxy.sh](../scripts/testhaproxy.sh) takes one optional command line
argument (the string "client").  If the "client" argument is provided, servers
are run in the background and various client tests (both shared- and
split-mode) are run against those.

### Naming different frontend/backend setups

Here's some terminology we use when talking about shared- or split-mode and
haproxy configurations.  

We'll name and document them like this:

            N. setup-name: Client <--[prot]--> frontend <--[prot]--> Backend

Where "N" is a number, "setup-name" is some catchy title we use just for ease
of reference, "client" is ``curl`` or ``s_client``, "frontend" is haproxy in
all cases so we'll just note the relevant port number used by our test setup,
and as the "backend" is also always lighttpd, we'll do the same for that.
Finally, "prot" is some string describing the protocol options on that hop.

With that our first and most basic setup is:

            1. ECH-front: Client <--[TLS+ECH]--> :7443 <--[Plaintext HTTP]--> :3480

The second one just turns on TLS, via two entirely independent TLS sessions,
with no ECH to the backend:

            2. Two-TLS: Client <--[TLS+ECH]--> :7444 <--[other-TLS]--> :3481

The third has one TLS session from the client to backend, with the frontend
just using the (outer) SNI for e.g. routing, if at all, and so that the
frontend doesn't get to see the plaintext HTTP traffic. This isn't that
interesting for us (other than to understand how to set it up), but is on the
path to one we do want. (In the actual configuration we also have a backend
listener at :3483 to handle the case where an unknown (outer) SNI was seen.)

            3. One-TLS: Client <--[TLS]--> :7445 <--[same-TLS]--> :3482

The fourth is where use split-mode, with the same TLS session between client
and backend but where the frontend did decrypt the ECH and just pass on the
inner CH to the backend, but where the frontend doesn't get to see the
plaintext HTTP traffic.  (As in the previous case, we have another backend
listener at :3485 to handle the case of both an outer SNI and a failure to
decrypt an ECH.)

            4. Split-mode: Client <--[TLS+ECH]--> :7446 <--[inner-CH]--> :3484

A fifth option that we don't plan to investigate but that may be worth naming
is where we have two separate TLS sessions both of which independently use ECH.
If that did prove useful, it'd probably be fairly easy to do.

            5. Two-ECH: Client <--[TLS+ECH]--> frontend <--[other-TLS+ECH]--> backend

### Running haproxy split-mode 

The idea is to configure "routes" for both in the frontend. With the example
configuration below, assuming "foo.example.com" is the inner SNI and
"example.com" is the outer SNI (or ``ECHConfig.public_name``) then if
decryption works, we'll route to the "foo" backend on port 3484, whereas if it
fails (or no ECH is present etc.) then we'll route to the "eg" server on port
3485. 

            frontend Split-mode
                mode tcp
                option tcplog
                bind :7446 
                use_backend 3484
            backend 3484
                mode tcp
                # next 2 lines needed to get switching on (outer) SNI to
                # work, not sure why
                tcp-request inspect-delay 5s
                tcp-request content accept if { req_ssl_hello_type 1 }
                tcp-request ech-decrypt d13.pem
                use-server foo if { req.ssl_sni -i foo.example.com }
                use-server eg if { req.ssl_sni -i example.com }
                server eg 127.0.3.4:3485 
                server foo 127.0.3.4:3484 
                server default 127.0.3.4:3485

If the above configuration is in a file called ``sm.cfg`` then haproxy can be
started via a command like:

            $ LD_LIBRARY_PATH=$HOME/code/openssl ./haproxy -f sm.cfg -dV 

We can then start the non-ECH-enabled backend for foo.example.com listening on
port 3484 as follows:

            $ cd $HOME/code/openssl/esnistuff
            $ ../apps/openssl s_server -msg -trace  -tlsextdebug  \
                -key cadir/example.com.priv \
                -cert cadir/example.com.crt \
                -key2 cadir/foo.example.com.priv \
                -cert2 cadir/foo.example.com.crt  \
                -CApath cadir/  \
                -port 3484  -tls1_3  -servername foo.example.com

Equivalently, it's ok if the backend server on port 3484 is also ECH-enabled
itself and has a copy of the ECH key pair. If that's the desired setup, one of
our test scripts is also usable:

            $ cd $HOME/code/openssl/esnistuff
            $ ./echsvr.sh -p 3484

Running a server for example.com on port 3485 is done similarly.

For the client, we do the following to use ECH and send our request to port
7446 where haproxy is listening:

            $ cd $HOME/code/openssl/esnistuff
            $ ./echcli.sh -s localhost  -H foo.example.com -p 7446 \
                -P `./pem2rr.sh echconfig.pem` -f index.html -N -c something-else
            Running ./echcli.sh at 20210615-191012
            Assuming supplied ECH is RR value
            ./echcli.sh Summary: 
            Looks like it worked ok
            ECH: success: outer SNI: 'something-else', inner SNI: 'foo.example.com'


## Logs

[testhaproxy.sh](../scripts/testhaproxy.sh) does pretty minimal logging in
``$HOME/code/openssl/esnistuff/haproxy/logs/haproxy.log`` but you need to add
some stanzas to ``/etc/rsyslog.conf`` to get that.  (Absent those, the test
script will, for now, complain and exit.)

A ``SERVERUSED`` cookie is added by haproxy in these configurations and the
file served by lighttpd, as can be seen from the lighttpd logs. 

## Key Rotation

We still need to figure out how to reload ECH keys without restarting haproxy.
Haproxy doesn't read from disk after initial startup, so we can't re-use the
plan from other serves for periodically reloading ECH keys.
TLS certificate/key reloading via socket-API/CLI is described
[here](https://docs.haproxy.org/dev/management.html#9.3). We'll want to try
do something similar for ECH keys, likely via that socket API.

## Split mode backend traffic security

One could argue that there's a need to be able to support cover traffic from
frontend to backend and to have that, and subsequent traffic, use an encrypted
tunnel between frontend and backend. Otherwise a network observer who can see
traffic between client and frontend, and also between frontend and backend, can
easily defeat ECH as it'll simply see the result of ECH decryption. (That
wouldn't be needed in all network setups, but in some.)

### Code Changes

Code for shared-mode  is in ``src/cfgparse-ssl.c`` and the new code to read in
the ECH pem file is in ``src/ssl-sock.c``; the header files I changed were
``include/haproxy/openssl-compat.h`` and ``include/haproxy/listener-t.h`` but
the changes to all those are pretty obvious and minimal for now.

When so configured, the existing ``smp_fetch_ssl_hello_sni`` (which handles SNI
based routing) is modified to first call ``attempt_split_ech``.
``attempt_split_ech`` will try decrypt and setup routing based on the inner or
outer SNI values found as appropriate.  If decryption succeeds, then the inner
CH is spliced into the buffer that used hold the outer CH and processing
continues as norml. 
