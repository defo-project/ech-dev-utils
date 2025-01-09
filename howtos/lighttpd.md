
# Lighttpd and ECH

Notes on the lighttpd ECH integration.

We assume you've already built our OpenSSL fork in ``$HOME/code/openssl`` and
have gotten the [localhost-tests](localhost-tests.md) working, and you should
have created an ``echkeydir`` as described
[here](../README.md#server-configs-preface---key-rotation-and-slightly-different-file-names).

The main lighttpd maintainer (@gstrauss) provided much well-appreciated help in
early versions of this integration, which was the first web server we tackled.
Recently, (on 2025-01-04) @gstrauss merged ECH code to the lighttpd1.4 master
branch. That can use boringssl or the DEfO-project OpenSSL fork for ECH support.

Hopefully, in the near future, the "official" OpenSSL ECH feature branch will
be usable for ECH support, but for the moment, one needs to build against our
DEfO-project fork to get ECH support in OpenSSL.

For DEfO-project CI purposes, we still have a fork of lighttpd1.4, (our CI
setup does a nightly merge with upstream, build and test to check if anything's
gotten broken), but the upstream ligtttpd1.4 master is also usable as that now
contains ECH code. This HOWTO describes use of the upstream lighttpd1.4 master
branch.

Commands on this howto use a few environment variables for clarity:
```bash
    $ export DEV=$HOME/code
    $ export RUNTOP=$HOME/lt
    $ export LD_LIBRARY_PATH=$DEV/openssl
```

## Build

Nothing remarkable here really:

```bash
    $ cd $DEV
    $ git clone https://github.com/lighttpd/lighttpd1.4.git
    ...
    $ cd lighttpd1.4
    $ ./autogen.sh 
    ... stuff ...
    $ CFLAGS=-DLIGHTTPD_OPENSSL_ECH_DEBUG ./configure --with-openssl=$DEV/openssl --with-openssl-libs=$DEV/openssl
    ... stuff ...
    $ make
    ... stuff ...
```

`CFLAGS=-DLIGHTTPD_OPENSSL_ECH_DEBUG` enables debug trace and is optional.

## Configuration

Reference: https://wiki.lighttpd.net/TLS_ECH

Lighttpd adds new server configuration settings, under ssl.ech-opts:

- keydir - name of directory scanned for ``*.ech`` files that will be
  parsed/used if they contain a private key and ECHConfig
- refresh - frequency (in seconds) to re-check whether some PEM files need to
  be reloaded
- trial-decrypt - enable/disable trial decryption (default: enable)

Those are reflected in the
[``lighthttpdmin.conf``](../configs/lighthttpdmin.conf) config file used in
localhost testing.

Lighttpd also supports a way to make a specific virtual host "ECH only" by
configuring a (presumably different) virtual host name to use, if ECH wasn't
successfully used in the ClientHello for that TLS session.

For this, there's a virtual host specific configuration item:

- ssl.ech-public-name - name of vhost to pretend was used if ECH wasn't
  successful (or not tried)

For example, in our [localhost test
setup](../configs/lighttpdmin.conf) baz.example.com is marked "ECH only"

The basic idea here is to explore whether or not it is useful to mark a
VirtualHost as "ECH only", i.e. to try to deny its existence if it is asked for
via cleartext SNI.

## Test

The script [``testlighttpd.sh``](../scripts/testlighttpd.sh) sets environment
vars and then runs lighttpd from the build, listening (for HTTPS only) on port
3443, then runs some client tests against that server, and finally kills
the server process:

```bash
    $ $DEV/ech-dev-utils/scripts/testlighttpd.sh
    lighttpd: no process found
    Testing grease 3443
    Testing public 3443
    Testing real 3443
    Testing hrr 3443
    All good.
    $

```

To later do manual tests, one can start a server running as follows:

```bash
    $ $DEV/lighttpd1.4/src/lighttpd -f $DEV/ech-dev-utils/configs/lighttpdmin.conf -m $DEV/lighttpd1.4/src/.libs
```

With our test configuration, the ECH PEM files are re-loaded every 60 seconds,
and if lighttpd was built with LIGHTTPD\_OPENSSL\_ECH\_DEBUG defined,
so you'll see error log lines like the following accumulating:

```bash
    2023-12-06 01:39:12: (mod_openssl.c.823) SSL: OSSL_ECHSTORE_read_pem() worked for $RUNTOP/echkeydir/echconfig.pem.ech
```

You can then use our wrapper for ``openssl s_client`` to access a web page:

```bash
    $ $DEV/ech-dev-utils/scripts/echcli.sh -p 3443 -s localhost -H foo.example.com -P echconfig.pem -f index.html
    Running $DEV/ech-dev-utils/scripts/echcli.sh at 20231206-011943
    $DEV/ech-dev-utils/scripts/echcli.sh Summary:
    Looks like ECH worked ok
    ECH: success: outer SNI: 'example.com', inner SNI: 'foo.example.com'
    $ 
```

You can also use our ECH-enabled curl build to test against this server (replacing
the ECHConfig value with your own of course):

```bash
    $ $DEV/curl/src/curl --ech ecl:AD7+DQA6uAAgACAogff+HZbirYdQCfXI00iBPP+K96YyK/D/0DoeXD/0fgAEAAEAAQALZXhhbXBsZS5jb20AAA== --connect-to foo.example.com:443:localhost:3443 https://foo.example.com/index.html --cacert $RUNTOP/cadir/oe.csr -vvv
    ...
    * ECH: result: status is succeeded, inner is foo.example.com, outer is example.com
    ...
```

We can now also run tests on ``baz.example.com`` which is setup as an "ECH only"
web site. So that works when using ECH:

```bash
    $ $DEV/curl/src/curl --ech ecl:AD7+DQA6uAAgACAogff+HZbirYdQCfXI00iBPP+K96YyK/D/0DoeXD/0fgAEAAEAAQALZXhhbXBsZS5jb20AAA== --connect-to baz.example.com:443:localhost:3443 https://baz.example.com/index.html --cacert $RUNTOP/cadir/oe.csr -vvv
```            

But if we don't use ECH at all then we get the content for ``example.com``,
the full output of which is shown below:

```bash
    $ $DEV/curl/src/curl --ech none --connect-to baz.example.com:443:localhost:3443 https://baz.example.com/index.html --cacert $RUNTOP/cadir/oe.csr -vvv
    * !!! WARNING !!!
    * This is a debug build of libcurl, do not use in production.
    * STATE: INIT => CONNECT handle 0x5621cc626208; line 1926
    * Connecting to hostname: localhost
    * Connecting to port: 3443
    * Added connection 0. The cache now contains 1 members
    * Host localhost:3443 was resolved.
    * IPv6: ::1
    * IPv4: 127.0.0.1
    * STATE: CONNECT => CONNECTING handle 0x5621cc626208; line 1979
    *   Trying [::1]:3443...
    * connect to ::1 port 3443 failed: Connection refused
    *   Trying 127.0.0.1:3443...
    * Connected to localhost (127.0.0.1) port 3443
    * ALPN: curl offers http/1.1
    * Didn't find Session ID in cache for host HTTPS://baz.example.com:443
    * TLSv1.3 (OUT), TLS handshake, Client hello (1):
    *  CAfile: $RUNTOP/cadir/oe.csr
    *  CApath: /etc/ssl/certs
    * TLSv1.3 (IN), TLS handshake, Server hello (2):
    * TLSv1.3 (IN), TLS handshake, Encrypted Extensions (8):
    * TLSv1.3 (IN), TLS handshake, Certificate (11):
    * TLSv1.3 (IN), TLS handshake, CERT verify (15):
    * TLSv1.3 (IN), TLS handshake, Finished (20):
    * TLSv1.3 (OUT), TLS change cipher, Change cipher spec (1):
    * TLSv1.3 (OUT), TLS handshake, Finished (20):
    * SSL connection using TLSv1.3 / TLS_AES_256_GCM_SHA384 / x25519 / RSASSA-PSS
    * ECH: result: status is not attempted
    * ALPN: server accepted http/1.1
    * Server certificate:
    *  subject: C=IE; ST=Laighin; O=openssl-ech; CN=example.com
    *  start date: Nov 22 12:42:04 2023 GMT
    *  expire date: Nov 19 12:42:04 2033 GMT
    *  subjectAltName: host "baz.example.com" matched cert's "*.example.com"
    *  issuer: C=IE; ST=Laighin; O=openssl-ech; CN=ca
    *  SSL certificate verify ok.
    *   Certificate level 0: Public key type RSA (2048/112 Bits/secBits), signed using sha256WithRSAEncryption
    *   Certificate level 1: Public key type RSA (2048/112 Bits/secBits), signed using sha256WithRSAEncryption
    * using HTTP/1.1
    * STATE: CONNECTING => PROTOCONNECT handle 0x5621cc626208; line 2087
    * STATE: PROTOCONNECT => DO handle 0x5621cc626208; line 2119
    > GET /index.html HTTP/1.1
    > Host: baz.example.com
    > User-Agent: curl/8.5.0-DEV
    > Accept: */*
    > 
    * STATE: DO => DID handle 0x5621cc626208; line 2215
    * STATE: DID => PERFORMING handle 0x5621cc626208; line 2333
    * TLSv1.3 (IN), TLS handshake, Newsession Ticket (4):
    * Didn't find Session ID in cache for host HTTPS://baz.example.com:443
    * Added Session ID to cache for HTTPS://baz.example.com:443 [server]
    * TLSv1.3 (IN), TLS handshake, Newsession Ticket (4):
    * Found Session ID in cache for host HTTPS://baz.example.com:443
    * old SSL session ID is stale, removing
    * Added Session ID to cache for HTTPS://baz.example.com:443 [server]
    * HTTP 1.1 or later with persistent connection
    < HTTP/1.1 200 OK
    < Content-Type: text/html
    < ETag: "2513506618"
    < Last-Modified: Tue, 05 Dec 2023 23:00:59 GMT
    < Content-Length: 492
    < Accept-Ranges: bytes
    < Date: Wed, 06 Dec 2023 01:27:42 GMT
    < Server: lighttpd/1.4.74-devel-lighttpd-1.4.54-2135-g75b7edca
    < 
    
    <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
    <html xmlns="http://www.w3.org/1999/xhtml">
    <head>
    <title>example.com lighttpd top page.</title>
    </head>
    <!-- Background white, links blue (unvisited), navy (visited), red
    (active) -->
    <body bgcolor="#FFFFFF" text="#000000" link="#0000FF"
    vlink="#000080" alink="#FF0000">
    <p>This is the pretty dumb top page for lighttpd example.com testing. </p>
    
    </body>
    </html>
    
    * STATE: PERFORMING => DONE handle 0x5621cc626208; line 2532
    * multi_done[DONE]: status: 0 prem: 0 done: 0
    * Connection #0 to host localhost left intact
    * Expire cleared
    $
```

In the above case, the client thinks it has a session with ``baz.example.com``
but the server has returned the web page for ``example.com``. (That works in
our test setup as the x.509 certificate for that instance has a wildcard for
``*.example.com``.) 

## Logs

If lighttpd was built with LIGHTTPD\_OPENSSL\_ECH\_DEBUG defined,
ECH status information is written to the lighttpd ``error.log``, that
looks like:

```bash
    2023-12-06 01:17:05: (mod_openssl.c.667) ech_status: SSL_ECH_STATUS_SUCCESS sni_clr: example.com sni_ech: foo.example.com
```

## CGI variables

To enable PHP edit your lighttpd config to include:

```bash
    server.modules += ( "mod_fastcgi" )
    fastcgi.server += ( ".php" =>
            ((
                    "socket" => "/var/run/php/php7.2-fpm.sock",
                    "broken-scriptfilename" => "enable"
            ))
    )
```

If lighttpd was built with LIGHTTPD\_OPENSSL\_ECH\_DEBUG defined,
the PHP code can then access these CGI variables:

- ``SSL_ECH_STATUS``: values can be: 
    - "SSL\_ECH\_STATUS\_SUCCESS" - if it all worked (successful ECH decrypt)
    - "SSL\_ECH\_STATUS\_FAILED" - if the call to ``SSL_ech_get1_status`` failed
    - "SSL\_ECH\_STATUS\_FAILED\_ECH" - something went wrong during attempted decryption
    - "SSL\_ECH\_STATUS\_FAILED\_ECH\_BAD\_NAME" - this is a client-side error, if the TLS server cert didn't match the ECH
    - "SSL\_ECH\_STATUS\_NOT\_TRIED" - if the client didn't include the TLS ClientHello extension at all
- ``SSL_ECH_INNER_SNI``: will contain the actual ECH used or "NONE"
- ``SSL_ECH_OUTER_SNI``: will contain the cleartext SNI seen or "NONE"

Here's a PHP snippet that will display those:

```php
    <?php
        function getRequestHeaders() {
            $headers = array();
            foreach($_SERVER as $key => $value) {
                if (substr($key, 0, 9) <> 'SSL_ECH_') {
                    continue;
                }
                $headers[$key] = $value;
             }
            return $headers;
        }
        
        $headers = getRequestHeaders();
        
        foreach ($headers as $header => $value) {
            echo "$header: $value <br />\n";
        }
    ?>
```

## Code changes

- All code changes are within the ``src/mod_openssl.c`` file.

- Significant new code is protected via ``#ifndef OPENSSL_NO_ECH`` as is done
  in our OpenSSL fork. The new code is compiled if the OpenSSL include files
  used define the ``SSL_OP_ECH_GREASE`` symbol. On upstream maintainer advice,
  structures that contain new ECH related fields are not protected via ``#ifndef
  OPENSSL_NO_ECH`` and some config file handling (that would in any case work
  with the released OpenSSL library) is similarly unprotected.

- Some code is also protected via ``#ifdef TLSEXT_TYPE_ech`` which is defined
  if the TLS library in use defines that symbol, and could in principle be of
  use in future with other TLS libraries that support ECH (e.g. boringssl).
  (boringssl uses TLSEXT\_TYPE\_encrypted\_client\_hello)

- Some changes are additionally protected via ``#ifdef LIGHTTPD_OPENSSL_ECH_DEBUG``.
  which is not enabled by default. Those are mainly tracing/logging chunks of code.

- ``mod_openssl_refresh_ech_keys_ctx()`` handles periodic re-loading of ECH PEM
  files and enabling ECH for the relevant ``SSL_CTX`` contexts. That's called
  for each ``SSL_CTX`` loaded into the server via
  ``mod_openssl_refresh_ech_keys()``.

- ``mod_openssl_ech_only_policy_check()`` implements the "ECH only" logic.

- A block of code within ``network_init_ssl()`` sets the ``SSL_OP_ECH_TRIALDECRYPT``
  option for the OpenSSL library if so configured.

## Debugging

To start lighttpd in a debugger, and break when loading ECH PEM files:

```bash
    $ gdb --args $DEV/lighttpd1.4/src/lighttpd -f $DEV/ech-dev-utils/configs/lighttpdmin.conf -m $DEV/lighttpd1.4/src/.libs -D
    ...
    (gdb) b mod_openssl_refresh_ech_keys_ctx
    Function "mod_openssl_refresh_ech_keys_ctx" not defined.
    Make breakpoint pending on future shared library load? (y or [n]) y
    Breakpoint 1 (mod_openssl_refresh_ech_keys_ctx) pending.
    (gdb) r
    Starting program: $DEV/lighttpd1.4/src/lighttpd -f $DEV/ech-dev-utils/configs/lighttpdmin.conf -m $DEV/lighttpd1.4/src/.libs -D
    [Thread debugging using libthread_db enabled]
    Using host libthread_db library "/lib/x86_64-linux-gnu/libthread_db.so.1".
    
    Breakpoint 1, mod_openssl_refresh_ech_keys_ctx (srv=srv@entry=0x5555555ac540, s=0x5555556141f8, cur_ts=cur_ts@entry=1701830361) at mod_openssl.c:554
    554	mod_openssl_refresh_ech_keys_ctx (server * const srv, plugin_ssl_ctx * const s, const time_t cur_ts)
    (gdb) 
```



