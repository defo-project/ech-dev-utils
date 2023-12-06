
# Lighttpd and ECH

Notes on our lighttpd integration.

This is in-work now, but not yet complete/tested.

We assume you've already built our OpenSSL fork in ``$HOME/code/openssl`` and
have gotten the [localhost-tests](localhost-tests.md) working, and you should
have created an ``echkeydir`` as described
[here](../README.md#server-configs-preface---key-rotation-and-slightly-different-file-names).

## Build

Nothing remarkable here really:

```bash
    $ cd $HOME/code
    $ git clone https://github.com/sftcd/lighttpd1.4 
    ...
    $ cd lighttpd1.4
    $ git checkout ECH-experimental
    Branch 'ECH-experimental' set up to track remote branch 'ECH-experimental' from 'origin'.
    Switched to a new branch 'ECH-experimental'
    $ ./autogen.sh 
    ... stuff ...
    $ ./configure --with-openssl=$HOME/code/openssl --with-openssl-libs=$HOME/code/openssl
    ... stuff ...
    $ make
    ... stuff ...
```

## Configuration

We added new server configuration settings, under ssl.ech-opts:

- keydir - name of directory scanned for ``*.ech`` files that will be
  parsed/used if they contain a private key and ECHConfig
- refresh - frequency (in seconds) to re-check whether some PEM files need to
  be reloaded
- trial-decrypt - whether or not ECH trial decryption is enabled 

Those are reflected in the
[``lighthttpdmin.conf``](../configs/lighthttpdmin.conf) config file used in
localhost testing.

We also support a way to make a specific virtual host "ECH only" by configuring
a (presumably different) virtual host name to use, if ECH wasn't successfully
used in the ClientHello for that TLS session.

For this, there's a virtual host specific configuration item:

- ssl.non-ech-host - name of vhost to pretend was used if ECH wasn't successful
  (or not tried)

The basic idea here is to explore whether or not it's useful to mark a
VirtualHost as "ECH only", i.e. to try deny it's existence if it's asked for
via cleartext SNI.  I'm very unsure if this is worthwhile but since it could be
done, it may be fun to play and see if it turns out to be useful. 

To that end we've added an "ssl.non-ech-host" label that can be in a lighttpd
configuration for a TLS listener. If that is present and if the relevant
name is used in the cleartext SNI (with or without ECH) then the TLS
connection will fail.  For example, in my [localhost test
setup](../configs/lighttpdmin.conf) baz.example.com is now marked "ECH only"

Failing this check is logged in the error log, e.g.:

```bash
    2019-10-07 21:33:33: (mod_openssl.c.531) ech_status:  not attempted cover: NULL hidden: NULL 
    2019-10-07 21:33:33: (mod_openssl.c.644) echonly abuse for only.ech.defo.ie from 2001:DB8::bad
    2019-10-07 21:33:33: (mod_openssl.c.2130) SSL: 1 error:140000EA:SSL routines::callback failed 
```

That log line includes the requesting IP address for now.

## Test

The script [``testlighttpd.sh``](../scripts/testlighttpd.sh) sets environment
vars and then runs lighttpd from the build, listening (for HTTPS only) on port
3443:

```bash
    $ ./testlighttpd.sh
    ...stuff...
```

If your lighttpd build is not in ``$HOME/code/lighttpd1.4`` then you can set the
``$LIGHTY`` environment variable to point to top of the lighttpd build tree.

The ``testlighttpd.sh`` script runs the server in foreground so you'll need to ctrl-C
out of that, when done. (TODO: add client checks as per nginx.)

You can then use our wrapper for ``openssl s_client`` to access a web page:

```bash
    $ ./echcli.sh  -p 3443 -s localhost -H foo.example.com -P echconfig.pem -f index.html
    Running ./echcli.sh at 20230314-230824
    Assuming supplied ECH is encoded ECHConfigList or SVCB
    ./echcli.sh Summary: 
    Looks like ECH worked ok
    ECH: success: outer SNI: 'example.com', inner SNI: 'foo.example.com'
    $ 
```

## Logs

For now, similar information is also written to the lighttpd error.log for
every request if logging is enabled. That has the result, the cover (if any)
and the hidden (if any) and looks like: 

```bash
    2019-09-30 16:18:02: (mod_openssl.c.462) ech_status:  success cover.defo.ie only.ech.defo.ie 
    2019-09-30 16:29:18: (mod_openssl.c.462) ech_status:  not attempted NULL NULL 
    2019-09-30 16:29:38: (mod_openssl.c.462) ech_status:  success NULL canbe.ech.defo.ie 
```

## PHP variables

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

The PHP code can then access these variables:

- ``SSL_ECH_STATUS``: values can be: 
    - "not attempted" - if the client didn't include the TLS ClientHello extension at all
    - "success" - if it all worked (succesful ECH decrypt)
    - "tried but failed" - something went wrong during attempted decryption
    - "worked but bad name" - this is a client-side error, if the TLS server cert didn't match the ECH
    - "error getting ECH status" - if the call to ``SSL_get_ech_status`` failed
- ``SSL_ECH_HIDDEN``: will contain the actual ECH used or "NONE" 
- ``SSL_ECH_COVER``: will contain the cleartext SNI seen or "NONE"

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

TBD

## Reloading ECH keys

The ``reload`` config file setting specifies the number of
seconds after which a reload will be attempted (on the next
web access). The default is TBD.

## Debugging

TBD

