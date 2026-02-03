
# NGINX OpenSSL Encrypted Client Hello (ECH) integration.

ECH is specified in
[draft-ietf-tls-esni](https://datatracker.ietf.org/doc/draft-ietf-tls-esni/).
This documentation assumes a basic familiarity with the ECH specification.

ECH shared-mode code has been upstreamed to Nginx, whereas the DEfO-project
fork of Nginx also supports ECH [split-mode](./split-mode.md). If you want to
play with split-mode, then follow the instructions for using the DEfO-project
forks. If you don't need split-mode, you can use the upstream Nginx code and
the upstream ECH feature branch.

ECH shared-mode is where the NGINX instance does the ECH decryption and also
terminates the TLS session as it hosts both the ECH `public-name` and `backend`
web sites.  ECH split-mode is where the NGINX instance only does ECH decryption
but passes the TLS session on to a different backend service. Split-mode
requires changes to OpenSSL that have yet to be merged to the ECH feature
branch. The DEfO-project OpenSSL fork supports both, whereas the upstream
OpenSSL ECH feature branch only has code for shared-mode.

In some of the below, we assume you've already built OpenSSL and gotten our
[localhost-tests](localhost-tests.md) setup and working, so you should have
created a fake CA and `echkeydir` that can be used for tests.

## Build

### ECH without split mode using upstream code

There is client and server ECH code in the OpenSSL ECH feature branch at
[https://github.com/openssl/openssl/tree/feature/ech](https://github.com/openssl/openssl/tree/feature/ech).
At present, ECH-enabling NGINX therefore requires building from source, using
the OpenSSL ECH feature branch.

To buid and locally install the ECH feature branch software:

```bash
$ cd $HOME/code/defo-project-org/
$ git clone https://github.com/openssl/openssl/ openssl-upstream
$ cd openssl-upstream
$ git checkout feature/ech
$ ./config --libdir=lib --prefix=$HOME/code/openssl-local-inst
...
$ make -j8 && make install_sw
...
```

Then an option to build NGINX from upstream is:

```bash
$ cd $HOME/code
$ git clone https://github.com/nginx/nginx.git nginx-upstream
$ cd nginx-upstream
$ ./auto/configure --prefix=nginx --with-cc-opt="-I $HOME/code/openssl-local-inst/include" --with-ld-opt="-L $HOME/code/openssl-local-inst/lib" --with-http_v2_module --with-http_ssl_module --with-stream --with-stream_ssl_module --with-stream_ssl_preread_module
$ make
...stuff...
```

This results in an NGINX binary in `objs/nginx` with a dynamically linked
OpenSSL, so `$LD_LIBRARY_PATH` needs to be set.

### ECH with split mode using DEfO-project forks

To use the DEfO-project forks:

```bash
    $ cd $HOME/code
    $ git clone https://github.com/defo-project/openssl.git openssl-from-defo
    $ cd openssl-from-defo
    $ ./config -d
    ...stuff...
    $ make -j12
    ...
```

Then you need nginx:

```bash
    $ cd $HOME/code
    $ git clone https://github.com/defo-project/nginx.git nginx-from-defo
    $ cd nginx-from-defo
    $ ./auto/configure --with-debug --prefix=nginx --with-http_ssl_module --with-stream --with-stream_ssl_module --with-stream_ssl_preread_module --with-openssl=$HOME/code/openssl-from-defo --with-openssl-opt="--debug" --with-http_v2_module
    $ make -j12
    ...
```

This results in a NGINX binary containing a statically linked OpenSSL in
`objs/nginx`. 

## Configuration

To enable ECH for an NGINX instance, configure a set of file names via one or
more `ssl_echfile` directives where that specifies a set of ECH PEM key files.
The `ssl_echfile` directives can be in the "http" or "server" sections of an
NGINX configuration as shown in the example below. All ECH PEM files matching
the (possibly wild-carded) value that are successfully decoded will be loaded. 

A shared-mode NGINX deployment needs to include a virtual server that matches
the ECH `public_name` so that the ECH fallback can work. The first virtual
server in the example below does this.

```
http {
    log_format withech '$remote_addr - $remote_user [$time_local] '
                    '"$request" $status $body_bytes_sent '
                    '"$http_referer" "$http_user_agent" "$ech_status"';
    access_log          /var/log/nginx/access.log withech;
    ssl_echfile       /etc/nginx/echkeydir/*.ech;
    server {
        listen              443 default_server ssl;
        http2 on;
        ssl_certificate     /etc/nginx/example.com.crt;
        ssl_echfile       /etc/nginx/otherechkeydir/other.ech;
        ssl_certificate_key /etc/nginx/example.com.priv;
        ssl_protocols       TLSv1.3;
        server_name         example.com;
        location / {
            root   /var/www/dir-example.com;
            index  index.html index.htm;
        }
    }
    server {
        listen              443 ssl;
        http2 on;
        ssl_certificate     /etc/nginx/example.com.crt;
        ssl_certificate_key /etc/nginx/example.com.priv;
        ssl_protocols       TLSv1.3;
        server_name         foo.example.com;
        location / {
            root   /var/www/dir-foo.example.com;
            index  index.html index.htm;
        }
    }
```

The `ssl_echfile` directive can also be used with the stream module, in the
same manner.

## Test

The [testnginx.sh](../scripts/testnginx.sh) script starts an ECH-enabled
nginx server listening on port 5443 using a config derived from
[nginxmin.conf](../configs/nginxmin.conf). That script will also create some
basic web content for `example.com` (the ECH `public_name`) and for
`foo.example.com` which can be the SNI in the inner ClientHello.

You should run that from the directory used before for
[localhosts-tests](../howtos/localhost-tests.md).

Below, we show runnimng this test using an Nginx binary that was built
in `$HOME/code/nginx-from-defo`:

```bash
    $ cd $HOME/lt
    $ NTOP=$HOME/code/nginx-from-defo/ $HOME/code/defo-project-org/ech-dev-utils/scripts/testnginx.sh 
    /home/stephen/lt
    Executing: /home/user/code/nginx-from-defo//objs/nginx -c nginxmin.conf
    /home/stephen/lt
    Testing grease 5443
    Testing public 5443
    Testing real 5443
    Testing hrr 5443
    All good.
    Killing nginx in process 482100
    $
```

At least as built here, nginx is fussy about configuration file pathnames and
doesn't like inheriting environment variables. (That's I'm sure for very good
reasons.) So, to run localhost tests, we copy over the
[`configs/nginxmin.conf`](../configs/nginxmin.conf) file to the place from
which we run tests, replacing environment variables in the copied file using
the `envsubst` command to do the replacement of `$RUNTOP` from the
template config file.

So if you run localhost tests from `$HOME/lt` then our test script will
expand that into an nginx config file that'll end up in
`$HOME/lt/nginx/nginxmin.conf`.  That's only done the first time (or re-done
if the git repo version is newer, but with a backup) so if you want to play
with more configuration changes, bear this in mind.

## Logs

You can log ECH status information in the normal `access.log` by adding
`$ech_status` to the `log_format`, e.g. the stanza below adds ECH status to the
normal `combined` log format:

```
    log_format withech '$remote_addr - $remote_user [$time_local] '
                    '"$request" $status $body_bytes_sent '
                    '"$http_referer" "$http_user_agent"
                    "ECH: $ssl_ech_status/$ssl_server_name/$ssl_ech_outer_server_name"';
    access_log          /var/log/nginx/access.log withech;
```

That results in log lines like the following:

```
127.0.0.1 - - [12/Oct/2025:18:54:07 +0100] "GET /index.html HTTP/1.1" 200 494 "-" "-"
                    "ECH: GREASED/foo.example.com/-"
127.0.0.1 - - [12/Oct/2025:18:54:15 +0100] "GET /index.html HTTP/1.1" 200 486 "-" "-"
                    "ECH: GREASED/example.com/-"
127.0.0.1 - - [12/Oct/2025:18:54:23 +0100] "GET /index.html HTTP/1.1" 200 494 "-" "-"
                    "ECH: SUCCESS/foo.example.com/example.com"
127.0.0.1 - - [12/Oct/2025:18:54:31 +0100] "GET /index.html HTTP/1.1" 200 494 "-" "-"
                    "ECH: SUCCESS/foo.example.com/example.com"
```

When ECH has succeeded with OpenSSL, then the outer SNI and inner SNI are included in that
order. If a client GREASEd or didn't try ECH at all, and no outer SNI was
provided, the HTTP host header will be shown instead. Connections that did not
use TLS show that. The TLS version is not specifically shown, so TLSv1.2
connections will show up as `NOT_TRIED`.

At start-up, and on configuration re-load, NGINX will log (to `error.log` at
the "notice" log level) the names of ECH PEM files successfully loaded and the
total number of ECH keys loaded, for each `server` stanza in the configuration.
Errors in loading keys are also logged and may result in the server not
starting. Example log lines would be:

```
2025/10/12 18:54:07 [notice] 768265#0: ngx_ssl_echfiles, worked for: /etc/nginx/echkeydir/echconfig.pem.ech
2025/10/12 18:54:07 [notice] 768265#0: ngx_ssl_echfiles, worked for: /etc/nginx/echkeydir/d13.pem.ech
2025/10/12 18:54:07 [notice] 768265#0: ngx_ssl_echfiles, total keys loaded: 2
```

## Testing with curl

If you have a build of curl that supports ECH, then you can
use that. In my local test setup, the following works:

```
$ ~/code/curl/src/curl --ech ecl:AD7+DQA6EwAgACCJDbbP6N6GbNTQT6v9cwGtT8YUgGCpqLqiNnDnsTIAIAAEAAEAAQALZXhhbXBsZS5jb20AAA==  --connect-to foo.example.com:443:localhost:5443 https://foo.example.com/index.html --cacert cadir/oe.csr -v
...
* ECH: result: status is succeeded, inner is foo.example.com, outer is example.com
...
```

## CGI variables

We set the following variables for, e.g. PHP code:

- `SSL_ECH_STATUS` - `success` means that, others also mean what they say
- `SSL_ECH_INNER_SNI` - has value that was in inner ClientHello SNI (or `-`)
- `SSL_ECH_OUTER_SNI` - has value that was in outer ClientHello SNI (or `-`)

To see those using fastcgi you need to include the following in the relevant
NGINX config:

```
fastcgi_param SSL_ECH_STATUS $ssl_ech_status;
fastcgi_param SSL_ECH_INNER_SNI $ssl_server_name;
fastcgi_param SSL_ECH_OUTER_SNI $ssl_ech_outer_server_name;
```

## Code changes

- If the OpenSSL library has ECH support, then ECH code is compiled.  That is
  detected if `SSL_OP_ECH_GREASE` is defined, which is checked in
  `src/events/ngx_event_openssl.c`.  In other words, if NGINX is built using an
  OpenSSL version that has ECH support, then that will be used. If the OpenSSL
  version doesn't have ECH then most of the ECH-specific code in NGINX is
  compiled out.

- `src/http/modules/ngx_http_ssl_module.h` and
  `src/http/modules/ngx_http_ssl_module.c` define the new `ssl_echfile`
  directive and the variables that become visible to e.g. PHP code.

- `ngx_ssl_echfiles()` in `src/event/ngx_event_openssl.c` loads ECH PEM files as
  directed by `ssl_echfile` directives, and enables shared-mode ECH
  decryption if some ECH keys are loaded. If `ssl_echfile` is set, but no keys
  are loaded, that results in an error and NGINX exits. Similarly, if
  `ssl_echfile` is set, but ECH support is not available, the server will
  exit. (As BoringSSL doesn't directly support the ECH PEM file format used,
  `ngx_ssl_ech_boring_read_pem` does the work of OpenSSL's 
  `OSSL_ECHSTORE_read_pem`.)

- When a set of `ssl_echfile` directives is provided, only the ECHConfig
  values from the first loaded of those will be returned to clients as
  `retry-configs` when follwoing the ECH fallback pattern.

- `ngx_ssl_get_ech_status()` and `ngx_ssl_get_ech_outer_sni()` also in
  `src/event/ngx_event_openssl.c` provide for setting the CGI variables
  mentioned above.

- Similar changes are made for the stream module in
  `src/stream/ngx_stream_ssl_module.c`
  and `src/stream/ngx_stream_ssl_module.h`.


## Reloading ECH keys

ECH uses a form of ephemeral-static (Elliptic curve) Diffie-Hellman key
exchange, so in order to get better forward secrecy, there is a need to perhaps
frequently rotate ECH keys. For example, some widely-used ECH-enabled web
services rotate ECH keys hourly. That may be done e.g.  via a cronjob and using
[A well-known URI for publishing service
parameters](https://datatracker.ietf.org/doc/html/draft-ietf-tls-wkech).  In
such a setup, the set of ECH PEM files specified by the `ssl_echfile` value will
change hourly, perhaps specifying three ECH PEM files
(curent, hour-before and two-hours before). This creates a need to reload ECH
PEM files regularly.

Sending a SIGHUP signal to the running process causes it to reload it's
configuration, so if `$PIDFILE` is a file with the NGINX server process-id:

```bash
$ kill -SIGHUP `cat $PIDFILE`
```

When ECH PEM files are loaded or re-loaded that's logged to the error log,
e.g.:

```
2023/12/03 20:09:13 [notice] 273779#0: ngx_ssl_echfiles, worked for: /home/user/lt/echkeydir/echconfig.pem.ech
2023/12/03 20:09:13 [notice] 273779#0: ngx_ssl_echfiles, worked for: /home/user/lt/echkeydir/d13.pem.ech
2023/12/03 20:09:13 [notice] 273779#0: ngx_ssl_echfiles, total keys loaded: 2
```

## Debugging

To run NGINX in `gdb` you probably want to uncomment the `daemon off;` and
`master_process off;` lines in your config file. You probably also want to
build with `CFLAGS="-g -O0"` to turn off optimization, and then, e.g. if you
wanted to debug into the `ngx_ssl_echfiles()` function:

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
    (gdb) b ngx_ssl_echfiles 
    Breakpoint 1 at 0x1402e9: file src/event/ngx_event_openssl.c, line 1469.
    (gdb) r -c nginxmin.conf
    Starting program: /home/user/code/nginx/objs/nginx -c nginxmin.conf
    [Thread debugging using libthread_db enabled]
    Using host libthread_db library "/lib/x86_64-linux-gnu/libthread_db.so.1".
    
    Breakpoint 1, ngx_ssl_echfiles (ssl=ssl@entry=0x555555db64d8, dirname=dirname@entry=0x555555db6568)
        at src/event/ngx_event_openssl.c:1469
    1469	{
    (gdb) c
    Continuing.
    
    Breakpoint 1, ngx_ssl_echfiles (ssl=ssl@entry=0x555555dbad68, dirname=dirname@entry=0x555555dbadf8)
        at src/event/ngx_event_openssl.c:1469
    1469	{
    (gdb) c
    Continuing.
    [Detaching after fork from child process 522259]
```

## Two other things

Not currently part of this test setup, but we have also demonstrated use of BoringSSL
rather than OpenSSL for ECH with Nginx, and a version where the value of an `ssl_echfile`
directive can use file globbing and hence ingest multiple files with one configuration
line. Both of those features are in a 
personal fork of Nginx](https://github.com/sftcd/nginx/tree/ECH%2Bboring%2Bglobbing)..
