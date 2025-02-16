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
    $ git clone https://github.com/defo-project/haproxy.git
    $ cd haproxy
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
    Executing: /home/user/code/haproxy/haproxy -f /home/user/code/ech-dev-utils/configs/haproxymin.conf  -DdV  >/home/user/lt/haproxy/logs/haproxy.log 2>&1
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

For various reasons we backported the ECH functionality onto a haproxy 2.8
build [here](https://github.com/sftcd/haproxy-2.8) and added logging to that
before including that in our "main" build (which is currently at haproxy 3.2).

Haproxy already allows logging of some TLS artefacts, e.g. by including an
"%sslc" directive in a log format to indicate inclusion of the TLS ciphersuite
used. We extend this idea by defining "%sslech" as a similar format indicator
that indicates inclusion of the ECH outcome (GREASE, success etc.) and in the
case of succcess the innner and out SNI values seen.

As an example, if one wanted to configure haproxy to log the user-agent string
and ECH outcome for HTTP mode connections then the following stanzas could
be used:

```bash
global
   log 127.0.0.1:514 local0 info

defaults
   mode http
   log global
   option httplog

frontend ECH-front
    capture request header user-agent len 100
    capture request header host len 100
    log-format "${HAPROXY_HTTP_LOG_FMT} SSL:%sslc, %sslv, ECH:%sslech"
    bind :7443 ech echkeydir ssl crt cadir/foo.example.com.pem
    use_backend 3480 if { ssl_fc_sni foo.example.com }
    default_backend 3485 # example.com backend for public_name
backend 3480
    server s1 127.0.3.4:3480
```

In order for that to work, one should enable UDP logging in `rsyslog` by e.g.
uncommenting the relevant lines in `/etc/rsyslog.conf`. One can also create a
file called e.g.  `/etc/rsyslog.d/10-haproxy.conf` with relevant haproxy
logging instructions.

The stanzas above are included in our [minimal haproxy
config](configs/haproxymin.conf).

That results in a log line like the following ending up in `/var/log/syslog`:

```
2025-02-15T02:02:20+00:00 localhost haproxy[18448]: 127.0.0.1:44002 [15/Feb/2025:02:02:20.204] \
ECH-front~ 3480/s1 0/0/1/1/2 200 737 - - --NI 1/1/0/0/0 0/0 \
{curl/8.12.0-DEV|foo.example.com} "GET /index.html HTTP/1.1" \
SSL:TLS_AES_256_GCM_SHA384, TLSv1.3, \
ECH:SSL_ECH_STATUS_SUCCESS/example.com/foo.example.com
```

(All of the above is one line in `syslog` - the backslashes are added to
improve visibility.)

The above indicates that ECH succeeded with the inner SNI of `foo.example.com`
and outer SNI of `example.com` which is a configuration setup using our 
localhost tests. The User-Agent HTTP header field above is `curl/8.12.0-DEV`
and the HTTP host header field is alongside, as that is useful when haproxy
sees GREASE'd ECH.

Using `curl` with that configuration the relevant command line to generate
that log line is: 

```bash
$ cd $HOME/lt
$ export LD_LIBRARY_PATH=$HOME/code/openssl
$ $HOME/code/curl/src/curl -v --insecure  --connect-to foo.example.com:443:localhost:7443  --ech ecl:AD7+DQA6EwAgACCJDbbP6N6GbNTQT6v9cwGtT8YUgGCpqLqiNnDnsTIAIAAEAAEAAQALZXhhbXBsZS5jb20AAA== https://foo.example.com/index.html
```

Where the relevant ECHConfig is from `$HOME/lt/ehconfig.pem` as generated in
our localhost tests.

Our haproxy test scripts (e.g.  [testhaproxy.sh](../scripts/testhaproxy.sh)) also
do some very minimal logging of the start-up state (e.g. ECH keys loaded) in
``$HOME/code/openssl/esnistuff/haproxy/logs/haproxy.log``.

A ``SERVERUSED`` cookie is added by haproxy in these configurations and the
file served by lighttpd, as can be seen from the lighttpd logs.

## ECH Key Rotation

The haproxy [mgmt socket i/f](https://docs.haproxy.org/dev/management.html#9.3)
describes a (unix) socket based way to update TLS server cert and related.
We've extended that for ECH.

To configure stats socket we include this as a general setting in
[haproxymin.conf](../configs/haproxymin.conf).

```bash
stats socket /tmp/haproxy.sock mode 600 level admin
```

The code for ECH key rotation  is in ``src/ssl_sock.c`` in
``cli_parse_show_ech()`` etc. The first step is to be able to view the set of
ECH configurations.

### Displaying ECH configs

For this, you need haproxy and lighttpd instances running. To do that:

```bash
    $ cd $HOME/lt
    $ export CODETOP=$HOME/code/openssl
    $ export LD_LIBRARY_PATH=$CODETOP
    $ export RUNTOP=$HOME/lt
    $ killall haproxy
    $ killall lighttpd
    $ $HOME/code/lighttpd1.4/src/lighttpd -f $HOME/code/ech-dev-utils/configs/lighttpd4haproxymin.conf \
        -m $HOME/code/lighttpd1.4/src/.libs
    $ $HOME/code/haproxy/haproxy -f $HOME/code/ech-dev-utils/configs/haproxymin.conf -DdV
```

That will leave haproxy and lighttpd running in the background. You may get
some logging in the terminal where you run those commands. You can then
play with the commands below.

The syntax is: ``show ssl ech [name]``
    - if no name provided all are shown
    - the names refer to the backend or frontend name from the haproxy config
      file, with which the relevant set of ECHConfig values are associated

- [haproxymin.conf](../scripts/haproxymin.conf) sets ECH configurations (via
  the ``echkeydir`` directive) for the "3484" backend, and the "Two-TLS" and
"ECH-front" frontends.

To display all ECH configs with our test setup:

```bash
$ echo "show ssl ech" | socat /tmp/haproxy.sock stdio
***
backend (split-mode): 3484 
ECH entry: 0 public_name: example.com age: 19 (has private key)
	[fe0d,a6,example.com,[0020,0001,0001],dab7f975ef17b0358940354ea9e9f8fe873907936be5bd6d13e48d42cc48180a,00,00]
***
frontend: ECH-front 
ECH entry: 0 public_name: example.com age: 19 (has private key)
	[fe0d,a6,example.com,[0020,0001,0001],dab7f975ef17b0358940354ea9e9f8fe873907936be5bd6d13e48d42cc48180a,00,00]
***
frontend: Two-TLS 
ECH entry: 0 public_name: example.com age: 19 (has private key)
	[fe0d,a6,example.com,[0020,0001,0001],dab7f975ef17b0358940354ea9e9f8fe873907936be5bd6d13e48d42cc48180a,00,00]
```

The backend name in the above is "3484", the frontend names are "ECH-front" and "Two-TLS"

Connect to socket on command line, and display the "Two-TLS" ECH configs:

```bash
$ echo "show ssl ech Two-TLS" | socat /tmp/haproxy.sock stdio
***
ECH for Two-TLS
ECH details (3 configs total)
index: 0: loaded 60 seconds, SNI (inner:NULL;outer:NULL), ALPN (inner:NULL;outer:NULL)
    [fe0d,bb,example.com,0020,[0001,0001],62c7607bf2c5fe1108446f132ca4339cf19df1552e5a42960fd02c697360163c,00,00]
index: 1: loaded 60 seconds, SNI (inner:NULL;outer:NULL), ALPN (inner:NULL;outer:NULL)
    [fe0d,64,example.com,0020,[0001,0001],cc12c8fb828c202d11b5adad67e15d0cccce1aaa493e1df34a770e4a5cdcd103,00,00]
index: 2: loaded 60 seconds, SNI (inner:NULL;outer:NULL), ALPN (inner:NULL;outer:NULL)
    [fe0d,bb,example.com,0020,[0001,0001],62c7607bf2c5fe1108446f132ca4339cf19df1552e5a42960fd02c697360163c,00,00]
```

### Additional commands: add, set, del

```bash
add ssl ech <name> <pemesni>
set ssl ech <name> <pemesni>
del ssl ech <name> [<age-in-secs>]
```

Where ``<name>`` is the name of a frontend or backend as above.

Providing the PEM file input ("pemesni") is a bit non-trivial, to add another ECH config one needs to:

```bash
$ openssl ech -public_name htest.com -out htest.pem
$ echo -e "add ssl ech ECH-front <<EOF\n$(cat htest.pem)\nEOF\n" | socat /tmp/haproxy.sock -
added a new ECH config to ECH-front

$ echo "show ssl ech ECH-front" | socat /tmp/haproxy.sock stdio
***
ECH for ECH-front 
ECH entry: 0 public_name: example.com age: 631 (has private key)
	[fe0d,a6,example.com,[0020,0001,0001],dab7f975ef17b0358940354ea9e9f8fe873907936be5bd6d13e48d42cc48180a,00,00]

ECH entry: 1 public_name: htest.com age: 13 (has private key)
	[fe0d,73,htest.com,[0020,0001,0001],ba8ca57396633ba90332fc45cdcf86f413d8aa5f8efde19202312d015bc1912d,00,00]

$
```

And we can see the new one added.

The ``EOF\n$(cat htest.pem)\nEOF`` is how we provide the <pemesni> value for both
"add" and "set" commands..

As you'd expect the "add" command adds a new ECH config to a set from the
relevant PEM file. The "set" command replaces the entire set with the new one
provided and the "del" command removes all configs loaded more than
``<age-in-secs>`` ago. An expected model for updates then is to periodically
add new configs and to remove ones that were added two cycles ago.

This is simpler than providing a transactional model with commits, which is how
TLS server private keys and certificates are handled, but is considered
sufficient for the moment.

## Split mode backend traffic security

For now, we do nothing at all to protect traffic between the haproxy frontend
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

