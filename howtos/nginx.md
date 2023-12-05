
# Ngnix and ECH

Notes on our nginx integration.

We assume you've already built our OpenSSL fork in ``$HOME/code/openssl`` and
have gotten the [localhost-tests](localhost-tests.md) working, and you
should have created an ``echkeydir`` as described [here](../README.md#server-configs-preface---key-rotation-and-slightly-different-file-names).

## Build

First, you may want a separate clone of our OpenSSL build (because nginx's
build, in this instantiation, re-builds OpenSSL and links static libraries, so
putting that in a new directory is a good plan if you prefer not to disturb
other builds):

```bash
    $ cd $HOME/code
    $ git clone https://github.com/sftcd/openssl.git openssl-for-nginx
    $ cd openssl-for-nginx
    $ git checkout ECH-draft-13c
    $ ./config -d
    ...stuff...
    $ make
    ...go for coffee...
```

Then you need nginx, and to switch to our ``ECH-experimental`` branch:

```bash
    $ cd $HOME/code
    $ git clone https://github.com/sftcd/nginx.git
    $ cd nginx
    $ git checkout ECH-experimental
    $ ./auto/configure --with-debug --prefix=nginx --with-http_ssl_module --with-stream --with-stream_ssl_module --with-stream_ssl_preread_module --with-openssl=$HOME/code/openssl-for-nginx --with-openssl-opt="--debug" --with-http_v2_module
    $ make
    ... go for coffee ...
```

## Configuration

To turn on ECH configure a directory via ``ssl_echkeydir`` that contains ECH
PEM key files. That directive can appear in the "http" or  "stream" section of
an nginx configuration as appropriate. The latter, the "stream" section, stanza
is only really relevant for split-mode, for which, see the [split-mode
howto](split-mode.md).

## Test

At least as built here, nginx is fussy about configuration file pathnames and
doesn't like inheriting environment variables. (That's I'm sure for very good
reasons.) So, to run localhost tests, we copy over the
[``configs/nginxmin.conf``](../configs/nginxmin.conf) file to the place from
which we run tests, replacing environment variables in the copied file using
the ``envsubst`` command to do the replacement of ``$RUNTOP`` from the 
template config file.

So if you run localhost tests from ``$HOME/lt`` then our test script will
expand that into an nginx config file that'll end up in
``$HOME/lt/nginx/nginxmin.conf``.  That's only done the first time (or re-done
if the git repo version is newer, but with a backup) so if you want to play
with more configuration changes, bear this in mind.

The test configuration listens on port 5443.

To test, (configuration template is in [nginxmin.con](../configs/nginxmin.conf)):

```bash
    $ cd $HOME/lt
    $ ~/code/ech-dev-utils/scripts/testnginx.sh 
    Can't find /home/user/lt/nginx/logs/nginx.pid - trying killall nginx
    nginx: no process found
    Executing:  /home/user/code/nginx/objs/nginx -c nginxmin.conf
    /home/user/lt
    Testing grease 5443
    Testing public 5443
    Testing real 5443
    Testing hrr 5443
    All good.
    Killing nginx in process 513085
    $
```

Once you've done that, there'll be DocRoot and log directories below
``$HOME/lt/nginx`` and if you want to play more you could e.g. do:

```bash
    $ ~/code/nginx/objs/nginx -c nginxmin.conf
    $ ~/code/ech-dev-utils/scripts/echcli.sh -H foo.example.com -p 5443 -s localhost -P echconfig.pem 
    Running /home/user/code/ech-dev-utils/scripts/echcli.sh at 20231205-024549
    /home/user/code/ech-dev-utils/scripts/echcli.sh Summary: 
    Looks like ECH worked ok
    ECH: success: outer SNI: 'example.com', inner SNI: 'foo.example.com'
    $ killall nginx
```

If you've built our ECH-enabled curl client then you can also test using
that, e.g.:

```bash
    $ export LD_LIBRARY_PATH=$HOME/code/openssl
    $ $HOME/code/curl/src/curl --ech ecl:AD7+DQA6uAAgACAogff+HZbirYdQCfXI00iBPP+K96YyK/D/0DoeXD/0fgAEAAEAAQALZXhhbXBsZS5jb20AAA==  --connect-to foo.example.com:443:localhost:5443 https://foo.example.com/index.html --cacert cadir/oe.csr -vvv
    ...
    * ECH: result: status is succeeded, inner is foo.example.com, outer is example.com
    ...
    $ killall nginx
```

You'll need to replace the base64 encoded ECHConfigList with your
own in the above. That's the 2nd last line of the ``echconfig.pem``
you generated earlier.

## Logs

The log files for the test above will be in ``$HOME/lt/nginx/logs`` and after
running the above ``error.log`` should contain a line like:

```bash
    2023/12/05 02:45:49 [notice] 513505#0: *1 ECH success outer_sni: example.com inner_sni: foo.example.com while SSL handshaking, client: 127.0.0.1, server: 0.0.0.0:5443
```

## PHP variables

We added the following variables that are now visible to PHP code:

- ``SSL_ECH_STATUS`` - ``success`` means that others also mean what they say
- ``SSL_ECH_INNER_SNI`` - has value that was in inner CH SNI (or ``NONE``)
- ``SSL_ECH_OUTER_SNI`` - has value that was in outer CH SNI (or ``NONE``)

To see those using fastcgi you need to include the following in the relevant
bits of nginx config:

            fastcgi_param SSL_ECH_STATUS $ssl_ech_status;
            fastcgi_param SSL_ECH_INNER_SNI $ssl_ech_inner_sni;
            fastcgi_param SSL_ECH_OUTER_SNI $ssl_ech_outer_sni;

## Code changes

- New code is protected using ``#ifndef OPENSSL_NO_ECH`` as is done in the
  OpenSSL library.

- There are some purely housekeeping changes that may or may not be needed
  but were at one point, due to building with the OpenSSL ``master`` branch,
  e.g. early on in ``src/event/ngx_event_openssl.c``.

- ``ngx_ssl_info_callback()`` (in ``src/event/ngx_event_openssl.c``) makes
  a call to ``SSL_ech_get_status()`` for logging of ECH outcomes.
  Similar code in the same file provides for setting the
  variables for PHP mentioned above.

- ``src/http/modules/ngx_http_ssl_module.c`` handles reading the new
  ``ssl_echkeydir`` configuration directive and defines the variables that
  become visible to e.g. PHP code.

- There's a new ``load_echkeys()`` function in
  ``src/event/ngx_event_openssl.c`` that loads ECH PEM files as directed by the
  ``ssl_echkeydir`` directive, and enables shared-mode ECH decryption whenever
  needed.

- ``src/stream/ngx_stream_ssl_preread_module.c`` has new code for ECH split
  mode to load ECH PEM files and attempt split-mode decryption of the 1st
  ClientHello. That also tees up handling of ECH if HRR is encountered, but
  ECH-decrypting the 2nd ClientHello in HRR cases happens in
  ``src/stream/ngx_stream_proxy_module.c`` 

## Reloading ECH keys

With nginx sending a SIGHUP signal to the running process causes it to reload
it's configuration, so if ``$PIDFILE`` is a file with the nginx server process
id:

```bash
    kill -SIGHUP `cat $PIDFILE`
```

When ECH PEM files are loaded or re-loaded that's logged to the error log,
e.g.:

```bash
    2023/12/03 20:09:13 [notice] 273779#0: load_echkeys, total keys loaded: 2
    2023/12/03 20:09:13 [notice] 273779#0: load_echkeys, worked for: /home/user/lt/echkeydir/echconfig.pem.ech
    202/12/03 20:09:13 [notice] 273779#0: load_echkeys, worked for: /home/user/lt/echkeydir/d13.pem.ech
```
## Debugging

To run nginx in ``gdb`` you probably want to uncomment the ``daemon off;`` line
in ``$HOME/lt/nginx/nginxmin.conf`` file then, e.g. if you wanted to debug into
the ``load_echkeys()`` function:

```bash
    $ gdb ~/code/nginx/objs/nginx 
    GNU gdb (Ubuntu 13.1-2ubuntu2) 13.1
    Copyright (C) 2023 Free Software Foundation, Inc.
    License GPLv3+: GNU GPL version 3 or later <http://gnu.org/licenses/gpl.html>
    This is free software: you are free to change and redistribute it.
    There is NO WARRANTY, to the extent permitted by law.
    Type "show copying" and "show warranty" for details.
    This GDB was configured as "x86_64-linux-gnu".
    Type "show configuration" for configuration details.
    For bug reporting instructions, please see:
    <https://www.gnu.org/software/gdb/bugs/>.
    Find the GDB manual and other documentation resources online at:
        <http://www.gnu.org/software/gdb/documentation/>.
    
    For help, type "help".
    Type "apropos word" to search for commands related to "word"...
    Reading symbols from /home/user/code/nginx/objs/nginx...
    (gdb) b load_echkeys 
    Breakpoint 1 at 0x1402e9: file src/event/ngx_event_openssl.c, line 1469.
    (gdb) r -c nginxmin.conf
    Starting program: /home/user/code/nginx/objs/nginx -c nginxmin.conf
    [Thread debugging using libthread_db enabled]
    Using host libthread_db library "/lib/x86_64-linux-gnu/libthread_db.so.1".
    
    Breakpoint 1, load_echkeys (ssl=ssl@entry=0x555555db64d8, dirname=dirname@entry=0x555555db6568)
        at src/event/ngx_event_openssl.c:1469
    1469	{
    (gdb) c
    Continuing.
    
    Breakpoint 1, load_echkeys (ssl=ssl@entry=0x555555dbad68, dirname=dirname@entry=0x555555dbadf8)
        at src/event/ngx_event_openssl.c:1469
    1469	{
    (gdb) c
    Continuing.
    [Detaching after fork from child process 522259]
```
