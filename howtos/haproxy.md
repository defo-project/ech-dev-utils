# Haproxy and ECH

Our fork is from https://github.com/haproxy/haproxy

It may be useful to look at [nomenclature](split-mode.md#nomenclature) text
describing the various ECH shared- and split-mode setups.

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
Text here assumes you've at least scanned that.

Compared to other web servers, haproxy configuration is a bit more involved as
our integration supports both split-mode and shared mode ECH, and haproxy, not
being a web server, also needs a backend web server configured.

ECH shared-mode in haproxy terms is where the haproxy frontend is a TLS
terminator and does all the ECH and TLS work before handing off a cleartext
HTTP request to a backend web server. If desired, a new TLS session can be 
used to protect the HTTP request, as is normal for haproxy.

Split-mode is where the frontend does the ECH decryption but doesn't terminate
the client's TLS session. There's another HOWTO specifically for
[split-mode](split-mode.md).

If split-mode decryption fails or no ECH extension is present, then haproxy
should be configured to forward to a backend that has the private key
corresponding to the ``ECHConfig.public_name``. If OTOH decryption works, then
haproxy should forward the inner CH, routing the request based on the SNI from
that inner CH to the appropriate web server. 

Our test script is [testhaproxy.sh](../scripts/testhaproxy.sh) with our minimal
config in [haproxymin.conf](../configs/haproxymin.conf).  The test script
starts lighttpd as needed to act as the backend web server.

A typical pre-existing haproxy config for terminating TLS will include lines
like the following for listeners in a "mode http" frontend:

```bash
    bind :7443 ssl crt cadir/foo.example.com.pem
```

We extend that to support ECH shared mode via the ``ech`` keyword that can be
followed by a filename or directory name, e.g.:

```bash
    bind :7443 ech echconfig.pem ssl crt cadir/foo.example.com.pem
```

If the ech keyword names a file, that'll be loaded and work if it's a correctly
encoded ECH PEM file. If the keyword names a directory, then that directory
will be scanned for all ``*.ech`` files, each of which is similarly handled.

For split-mode, we added an ``ech-decrypt`` keyword to allow configuring the
ECH PEM file or directory with the ECH key pair(s). That keyword can be added
to a "tcp mode" frontend configuration, e.g.:

```bash
    tcp-request ech-decrypt echkeydir
```

## Test

The [testhaproxy.sh](../scripts/testhaproxy.sh) script starts haproxy and
runs clients against those. A lighttpd backend web server
is started using
[lighttpd4haproxymin.conf](../configs/lighttpd4haproxymin.conf).

The following are the "names" for test setups and are also used as
the names for frontend (FE) setting in the [haproxy configuration
file](../configs/haproxymin.conf):

- ECH-front: haproxy terminates the client's TLS session and is ECH-enabled,
  cleartext HTTP requests are sent to backend
- Two-TLS: haproxy terminates the client's TLS session and is ECH-enabled,
  HTTPS requests are sent to backend, using a 2nd FE-BE TLS session
- One-TLS: haproxy passes on anything with the outer SNI that has the
  ``public_name`` to a backend server that does ECH and can also serve
  as authenticate as the ``public_name``  
- Split-mode: haproxy decrypts ECH but passes on the cliet's TLS session
  to the backend if ECH decryption worked, or to the ``public_name``
  server in other cases

The table below shows the port numbers involved in each named setup:

| name | ECH mode | haproxy mode | FE port | default BE port | BE port |
| ------- |:---:|:---:|:---:|:---:|:---:|
| ECH-front | shared | http | 7443 | 3485 | 3480 | 
| Two-TLS | shared | http | 7444 | 3485 | 3481 | 
| One-TLS | shared | tcp | 7445 | 3485 | 3482 | 
| Split-mode | split | tcp | 7446 | 3485 | 3484 | 

The test script starts a lighttpd running as the backend with the
following configuration:

| port | server name | comment |
| ---- | ----------- | ------- |
| 3480 | foo.example.com | accepts cleartext HTTP for foo.example.com |
| 3481 | foo.example.com | accepts HTTPS for foo.example.com |
| 3482 | foo.example.com | accepts HTTPS for foo.example.com |
| 3484 | foo.example.com | terminates client's TLS for foo.example.com (as ECH-backend) |
| 3485 | example.com | the ``public_name`` server |

To run the test:

```bash
    $ cd $HOME/lt
    $ $HOME/code/ech-dev-utils/scripts/testhaproxy.sh
    haproxy: no process found
    Executing: /home/stephen/code/haproxy/haproxy -f /home/stephen/code/ech-dev-utils/configs/haproxymin.conf  -DdV  >/home/stephen/lt/haproxy/logs/haproxy.log 2>&1
    Doing shared-mode client calls...
    Testing grease 7443
    Testing grease 7444
    Testing public 7443
    Testing public 7444
    Testing real 7443
    Testing real 7444
    Testing hrr 7443
    Testing hrr 7444
    All good.
    $
```

## Logs

[testhaproxy.sh](../scripts/testhaproxy.sh) does pretty minimal logging in
``$HOME/code/openssl/esnistuff/haproxy/logs/haproxy.log``. 

A ``SERVERUSED`` cookie is added by haproxy in these configurations and the
file served by lighttpd, as can be seen from the lighttpd logs. 

## Key Rotation

We still need to implement reloading ECH keys without restarting haproxy.
Haproxy doesn't (like to) read from disk after initial startup, so we can't
re-use the plan from other serves for periodically reloading ECH keys.  TLS
certificate/key reloading via socket-API/CLI is described
[here](https://docs.haproxy.org/dev/management.html#9.3). We'll want to try do
something similar for ECH keys, likely via that socket API.

## Split mode backend traffic security

For now, we do nothing at all to protect traffice between the haproxy frontend
and backend, other than show how to enable TLS. As a network observer who could
see that traffic could mount traffic analysis attacks, one could argue that
there's a need to be able to support cover traffic from frontend to backend and
to have that, and non-cover traffic, use an encrypted tunnel between frontend
and backend. We've done nothing to mitigate that attack so far. 

## Code Changes

- All ECH code is protected via ``#ifdef USE_ECH`` which is provided on the
  ``make`` command line as described above.

- Two new header files define a new type (``include/haproxy/ech-h.h``) and a
  new internal API for split-mode (``include/haproxy/ech.h``).

- A new config setting ``ech_filedir`` is added to
  ``include/haproxy/listener-t.h`` to store the new ECH configuration setting.
  That's stored for later in ``src/cfgparse-ssl.c`` if ECH is configured.

- ``src/ssl_sock.c`` makes the call to enable ECH for the ``SSL_CTX`` if so
  configured, which is all that's needed to handle shared mode ECH.

ECH split-mode is mode involved:

- ``include/haproxy/proxy-t.h`` has some fields added to the ``proxy.tcp_req``
  sub-strcuture to handle split-mode ECH.

- ``include/haproxy/stconn-t.h`` has an ``ech_state`` field added to the
  ``stconn`` structure (also for split-mode ECH).

- ``src/tcp_rules.c`` handles loading ECH key pairs for ECH split-mode.

- ``src/ech.c`` has the implementation of ``attempt_split_ech()``

- ``src/payload.c`` had code to determine if a first call to
  ``attempt_split_ech()`` is warranted, and if so, makes that call.

- ``src/stconn.c`` has code to handle ECH with the 2nd ClientHello if HRR is
  encountered. That's basically a 2nd call to ``attempt_split_ech()`` when
  warranted.

