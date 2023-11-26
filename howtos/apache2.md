
# Apache2 and ECH

Our fork is from https://github.com/apache/httpd which is apache 2.5.1 at the moment.

## Build

We assume you've already built our OpenSSL fork in ``$HOME/code/openssl`` and
have gotten the [localhost-tests](localhost-tests.md) working, and you
should have created an ``echkeydir`` as described [here](../README.md#server-configs-preface---key-rotation-and-slightly-different-file-names).

We need the httpd code and the Apache Portable Runtime (APR).  As recommended,
the APR stuff should be in a ``srclib`` sub-directory of the httpd
source directory.

```bash
    $ cd $HOME/code
    $ git clone https://github.com/sftcd/httpd
    $ cd httpd
    $ git checkout ECH-experimental
    $ cd srclib
    $ git clone https://github.com/apache/apr.git
    $ cd ..
    $ ./buildconf
    ... stuff ...
```

And off we go with configure and make ...

```bash
    $ export CFLAGS="-I$HOME/code/openssl/include"
    $ export LDFLAGS="-L$HOME/code/openssl"
    $ ./configure --enable-ssl --with-ssl=$HOME/code/openssl
    ... loads of stuff ...
    $ make -j8
    ... lotsa lotsa stuff ...
```

At some point I made myself a note that I needed an additional ``sudo apt
install libxml2-dev`` and to add ``--with-libxml2`` to the configure command
above, and to also add the related include path to CFLAGS to get things to
work.  Not sure if that's useful but I guess it might be. (I wrote that note
before the pandemic, so presumably thought it might save my future self enough
time to be worth preserving the note:-)

## Configuration

There's one new server-wide ``SSLECHKeyDir`` directive needed for ECH that
names the directory where ECH key pair files (names ``*.ech``) are stored.
There's an example in [apachemin.conf](../configs/apachemin.conf). 

## Test

The [testapache.sh](../scrtpts/testapache.sh) script starts an ECH-enabled
apache server listening on port 9443 using the config in
[apachemin.conf](../configs/apachemin.conf). That script will also create some
basic web content for ``example.com`` (the ECH ``public_name`) and for
``foo.example.com`` which can be the SNI in the inner ClientHello.

You should run that from the directory we used before for
[localhosts-tests](../howtos/localhost-tests.md).

```bash
    $ cd $HOME/lt
    $ $HOME/code/ech-dev-utils/scripts/testapache.sh
    Can't find /home/user/lt/apache/httpd.pid - trying killall httpd
    httpd: no process found
    Executing:  /home/user/code/httpd/httpd -d /home/user/lt -f /home/user/code/ech-dev-utils/configs/apachemin.conf 
    /home/user/lt
    $ 
    $ $HOME/code/ech-dev-utils/scripts/echcli.sh -p 9443 -s localhost -H foo.example.com  -P echconfig.pem -f index.html
    Running /home/user/code/ech-dev-utils/scripts/echcli.sh at 20231124-164157
    /home/user/code/ech-dev-utils/scripts/echcli.sh Summary: 
    Looks like ECH worked ok
    ECH: success: outer SNI: 'example.com', inner SNI: 'foo.example.com'
    $ 
    $ killall httpd # kill daemon
```

The "success" above is what you're looking for.

## Logs

The log files for the test above will be in ``$HOME/lt/apache/logs`` and after
running the above ``error.log`` should contain a line like:

```bash
[Fri Nov 24 16:41:57.863004 2023] [ssl:info] [pid 158960:tid 140277178160832] [client 127.0.0.1:53180] AH10240: ECH success outer_sni: example.com inner_sni: foo.example.com
```

And ``access.log`` should contain something like:

```bash
127.0.0.1 - - [24/Nov/2023:16:41:57 +0000] foo.example.com "GET /index.html HTTP/1.1" 200 "-" "-"
```

## PHP variables

The following variables that are now visible to PHP code:

- ``SSL_ECH_STATUS`` - ``success`` means that others also mean what they say
- ``SSL_ECH_INNER_SNI`` - has value that was encrypted in ECH (or ``NONE``)
- ``SSL_ECH_OUTER_SNI`` - has value that was seen in plaintext SNI (or ``NONE``)

I setup PHP for my apache deployment on
[https://draft-13.esni.defo.ie:11413](https://draft-13.esni.defo.ie:11413).
That's not part of the localhost test setup, and there were a couple of other 
things to do:

    - If needed, install fast-cgi: ``sudo apt install php8.1-cgi``

    - Edit ``/etc/php/8.1/fpm/pool.d/www.conf`` to use localhost:9000, added
      ``proxy_module`` and ``proxy_fcgi_module`` to the global apache config
      and turn on PHP and added the following to the apache config for the
      VirtualHost using ECH: 

```bash
    <FilesMatch "\.php$">
        SetHandler "proxy:fcgi://127.0.0.1:9000"
    </FilesMatch>
    Options +ExecCGI
```

As PHP gets updated, the PHP version numbers in the above also change of course.

## Code changes

- All code changes are within ``modules/ssl`` and are protected via ``#ifdef
  HAVE_OPENSSL_ECH``.  That's defined in ``ssl_private.h`` if the included
``ssl.h`` defines ``SSL_OP_ECH_GREASE``.

- There're a bunch of changes to add the new ``SSLECHKeyDir`` direcive that
  are mosly obvious.

- We load the keys from ``SSLECHKeyDir`` using the ``load_echkeys()`` function in
  ``ssl_engine_init.c``. That also ECH-enables the ``SSL_CTX`` when keys are
  loaded, which triggers ECH decryption as needed.

- We add a callback to ``SSL_CTX_ech_set_callback`` also in ``ssl_engine_init.c``.

- We add calls to set the ``SSL_ECH_STATUS`` etc. variables to the environment
(for PHP etc) in ``ssl_engine_kernel.c`` and also do the logging of ECH outcomes
(to the error log).

- We use``ap_log_error()`` liberally for now, mostly with ``APLOG_INFO`` level
  (or higher).  There's a semi-automated log numbering scheme - the idea is to
start with code that uses the ``APLOGNO()`` macro with nothing in the brackets,
then to run a perl script (from $HOME/code/httpd) that'll generate the next
unique log number to use, and modify the code accordingly. (I guess that would
need re-doing when a PR is eventually submitted but can cross that hurdle when
I get there.) As I'll forget what to do, the first time I used this the command
I ran was:

            $ cd $HOME/code/httpd
            $ perl docs/log-message-tags/update-log-msg-tags modules/ssl/ssl_engine_config.c

- There is currently a CI build fall due to a bunch of info message idenfier
  collision warnings, e.g.

```bash
    WARNING: Duplicate tag 10254 at server/util_etag.c:172 and modules/ssl/ssl_engine_init.c:215
```
Those seem fine to fix later.

## Reloading ECH keys

Giving apache a command line argument of "-k graceful" causes a graceful reload
of the configuration, without dropping existing connections.  (Not sure how
well I can test that proposition.) In any case, "-k graceful" does seem to have
the required effect, so that's useful whenever one deploys in a context with
regular ECH key updates. For the present that can be done via the
[testapache.sh](../scripts/testapache.sh) script by providing a "graceful"
parameter to the script:

```bash
    $ $HOME/code/ech-dev-utils/scripts/testapache.sh graceful
    Telling apache to do the graceful thing
    ...
```

## Debugging

With a bit of arm-wrestling I figured out how to run apache in the debugger
loading all the various shared libraries needed with one process.  Since that's
too much to type each time, I made an [apachegdb.sh](../scripts/apachegdb.sh)
script to do that. If you give it a function name as a command line argument
it'll start the server with a breakpoint set there. With no command line
argument it just starts the server.

To build for debug:

```bash
    $ export CFLAGS="-I$HOME/code/openssl/include -I/usr/include/libxml2 -g"
    $ export LDFLAGS="-L$HOME/code/openssl"
    $ ./configure --enable-ssl --with-ssl=$HOME/code/openssl --with-libxml2
    ... loads of stuff ...
    $ make clean 
    $ make -j8
    ... lotsa lotsa stuff ...
```
