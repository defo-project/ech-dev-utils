
# Apache2 and ECH

We have upstreamed our ECH code so the [upstream repository](https://github.com/apache/httpd)
may be used rather than the DEfO-project one. If compiled against an OpenSSL that supports
ECH, then ECH will be enabled in the Apache build. To date, the Apache2 integration only
supports ECH shared-mode and doesn't support ECH split-mode.

We assume you've already built our OpenSSL fork in
`$HOME/code/defo-project-org/openssl` and have gotten the
[localhost-tests](localhost-tests.md) working, and you should have created a fake
CA and an
`echkeydir` as described
[here](../README.md#server-configs-preface---key-rotation-and-slightly-different-file-names).

## Build

First, download and build our defo-project OpenSSL fork.

```bash
$ cd $HOME/code/defo-project-org/
$ git clone https://github.com/defo-project/openssl.git openssl
...
$ cd openssl
$ ./config --libdir=lib --prefix=$HOME/code/openssl-local-inst
...
$ make -j8 && make install_sw
...
```

Note that you can alternatively use the OpenSSL project's upstream
code from the ECH feature branch, i.e.:

```bash
$ cd $HOME/code/upstream/
$ git clone https://github.com/openssl/openssl.git openssl
$ git checkout feature/ech
...
$ cd openssl
$ ./config --libdir=lib --prefix=$HOME/code/openssl-local-inst
...
$ make -j8 && make install_sw
...
```

We need the httpd code and the Apache Portable Runtime (APR).  As recommended,
the APR stuff should be in a `srclib` sub-directory of the httpd source
directory.

```bash
    $ cd $HOME/code
    $ git clone https://github.com/apache/httpd httpd
    $ cd httpd
    $ cd srclib
    $ git clone https://github.com/apache/apr.git
    $ cd ..
    $ ./buildconf
    ... stuff ...
```

And off we go with configure and make ...

```bash
    $ export CFLAGS="-I$HOME/code/openssl-local-inst/include"
    $ export LDFLAGS="-L$HOME/code/openssl-local-inst/lib"
    $ ./configure --enable-ssl --with-ssl=$HOME/code/openssl-local-inst/lib
    ... loads of stuff ...
    $ make -j8
    ... lotsa lotsa stuff ...
```

## Configuration

There's one new server-wide `SSLECHKeyDir` directive needed for ECH that
names the directory where ECH PEM files (named `*.ech`) are stored.
There's an example in [apachemin.conf](../configs/apachemin.conf).

The convention for Apache2 is that ECH PEM files are named `*.ech`.  The
`httpd` binary will only attempt to load files from `SSLECHKeyDir` named
thusly.

## Test

The [testapache.sh](../scripts/testapache.sh) script starts an ECH-enabled
apache server listening on port 9443 using the config in
[apachemin.conf](../configs/apachemin.conf). That script will also create some
basic web content for `example.com` (the ECH `public_name`) and for
`foo.example.com` which can be the SNI in the inner ClientHello.

You should run that from the directory we used before for
[localhosts-tests](../howtos/localhost-tests.md).

```bash
    $ cd $HOME/lt
    $ $HOME/code/defo-project-org/ech-dev-utils/scripts/testapache.sh 
    /home/stephen/lt
    Killing old httpd in process 351531
    Executing: /home/user/code/httpd/httpd -d /home/user/lt -f /home/user/code/defo-project-org/ech-dev-utils/configs/apachemin.conf
    [Mon Feb 02 15:43:35.621344 2026] [core:warn] [pid 351738:tid 351738] AH00111: Config variable ${PACKAGING} is not defined
    Testing grease 9443
    Testing public 9443
    Testing real 9443
    Testing hrr 9443
    All good.
    $
```

The warning in the above can be ignored - that's an artefact of how we
use the same test script in the DEfO CI setup as well as for local testing.

## Logs

The log files after running the test above will be in `$HOME/lt/apache/logs`
and after running the above with `LogLevel info`, then `error.log` should
contain some lines like:

```bash
...
[Mon Feb 02 17:11:14.484545 2026] [ssl:info] [pid 356248:tid 356248] AH10529: ECH: 3 keys loaded
```

And `access.log` should contain something like:

```bash
127.0.0.1 - - [02/Feb/2026:20:17:16 +0000] foo.example.com "GET /index.html HTTP/1.1" 200 "-" "-"
127.0.0.1 - - [02/Feb/2026:20:17:25 +0000] example.com "GET /index.html HTTP/1.1" 200 "-" "-" 
127.0.0.1 - - [02/Feb/2026:20:17:33 +0000] foo.example.com "GET /index.html HTTP/1.1" 200 "-" "-"
127.0.0.1 - - [02/Feb/2026:20:17:41 +0000] foo.example.com "GET /index.html HTTP/1.1" 200 "-" "-"
```

With `Loglevel debug`, (which needs an edit to the config file included in this
repo), following successful ECH decryption, we see:

```bash
[Mon Feb 02 17:18:03.516411 2026] [ssl:debug] [pid 357044:tid 357065] ssl_engine_kernel.c(2320): [client 127.0.0.1:37882] ECH success outer_sni: example.com inner_sni: foo.example.com
```

## Variables exported to environment (aka CGI vars)

The following variables that are now visible to the environment, e.g. to PHP
code:

- `SSL_ECH_STATUS` - `success` means that others also mean what they say
- `SSL_ECH_INNER_SNI` - has value that was encrypted in ECH (or `NONE`)
- `SSL_ECH_OUTER_SNI` - has value that was seen in plaintext SNI (or `NONE`)

I setup PHP for my apache deployment on
[https://draft-13.esni.defo.ie:11413](https://draft-13.esni.defo.ie:11413).
That's not part of this test setup though, and there were a couple of other
things to do to use this:

    - If needed, install fast-cgi: `sudo apt install php8.1-cgi`

    - Edit `/etc/php/8.1/fpm/pool.d/www.conf` to use localhost:9000, add
      `proxy_module` and `proxy_fcgi_module` to the global apache config
      and turn on PHP and add the following to the apache config for the
      VirtualHost using ECH:

```bash
    <FilesMatch "\.php$">
        SetHandler "proxy:fcgi://127.0.0.1:9000"
    </FilesMatch>
    Options +ExecCGI
```

As PHP gets updated, the PHP version numbers in the above also change of course.

## Code changes

- All code changes are within `modules/ssl` and are protected via `#ifdef
  HAVE_OPENSSL_ECH`.  That's defined in `ssl_private.h` if the included
`ssl.h` defines `SSL_OP_ECH_GREASE` which is defined in the ECH feature branch 
and the DEfo sources.

- There're a bunch of changes to add the new `SSLECHKeyDir` directive that
  are mosly obvious.

- We load the keys from `SSLECHKeyDir` using the `load_echkeys()` function in
  `ssl_engine_init.c`. That also ECH-enables the `SSL_CTX` when keys are
  loaded, which triggers ECH decryption as needed.

- We add a callback to `SSL_CTX_ech_set_callback()` also in `ssl_engine_init.c`
to `ssl_callback_ECH()` which returns a string desccribing the status of the
ECH for the connecction.

- We add calls to set the `SSL_ECH_STATUS` etc. variables to the environment
(for PHP etc) in `ssl_engine_kernel.c` and also do the logging of ECH outcomes
(to the error log).

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
    $ export CFLAGS="-I$HOME/code/openssl-local-inst/include -I/usr/include/libxml2 -g"
    $ export LDFLAGS="-L$HOME/code/openssl-local-inst/lib"
    $ ./configure --enable-ssl --with-ssl=$HOME/code/openssl-local-inst/lib --with-libxml2
    ... loads of stuff ...
    $ make clean
    $ make -j8
    ... lotsa lotsa stuff ...
```
