# HOWTO run localhost OpenSSL ECH tests with [`echcli.sh`](../scripts/echcli.sh) and [`echsvr.sh`](../scripts/echsvr.sh)

First step is to have an openssl build with ECH that works, e.g. to get and
build the DEfO project OpenSSL fork that supports both shared-mode and
split-mode ECH:

```bash
    $ cd $HOME/code/defo-project-org/
    $ git clone https://github.com/defo-project/openssl
    $ cd openssl
    $ ./config
    ...stuff...
    $ make -j12
    ...stuff...
```

There are a bunch of ECH tests that are run as part of OpenSSL's `make test`
target, but here we assume you want to run separate server and clients
processes.

The build above gets you the openssl command line binary in
`$HOME/code/defo-project-org/openssl/apps/openssl`. If you did the build
elsewhere then you can set a `$CODETOP` environment variable pointing to the
top of the openssl build tree, and the other scripts here will use that
path instead, e.g.:

```bash
    $ export CODETOP=/mnt/somewhere/openssl
```

Let's assume this repo is in `$HOME/code/defo-project-org/ech-dev-utils`

## Just using the client wrapper script

The [`echcli.sh`](../scripts/echcli.sh) script can test ECH against any web
site. For that to work, you need `dig` installed so the client can fetch the
relevant HTTPS RR from the DNS. So, to try against
[https://defo.ie/ech-check.php](https://defo.ie/ech-check.php) use:

```bash
    $ $HOME/code/defo-project-org/ech-dev-utils/scripts/echcli.sh -H defo.ie -f ech-check.php
    Running /home/user/code/defo-project-org/ech-dev-utils/scripts/echcli.sh at 20231122-132950
    /home/user/code/defo-project-org/ech-dev-utils/scripts/echcli.sh Summary:
    Looks like ECH worked ok
    ECH: success: outer SNI: 'cover.defo.ie', inner SNI: 'defo.ie'
    $
```

If you want to see some grizzly details, just add a `-d` to the command line to
get debug tracing output.

## Running a server on localhost

To run a TLS server you need to pick a place to run tests a fake
x.509 CA and the certs needed, e.g.:

```bash
    $ mkdir -p $HOME/lt
    $ cd $HOME/lt
    $ $HOME/code/ech-dev-utils/scripts/make-example-ca.sh
    ...stuff..
```

You should now have a `$HOME/lt/cadir` with all the x.509 stuff needed, that
is, the fake CA setup and keys and certificates for the TLS servers needed in
these tests. We normally use the DNS name `example.com` for the ECH
`public-name` or outer SNi value and the names `foo.example.com` and sometimes
`bar.example.com` for the ECH inner SNI values.

Next, you need to generate an ECH key pair:

```bash
    $ cd $HOME/lt
    $ export LD_LIBRARY_PATH=$HOME/code/defo-project-org/openssl
    $ $HOME/code/defo-project-org/openssl/apps/openssl ech -public_name example.com
    $ ls -l echconfig.pem
    -rw-rw-r-- 1 user user 259 Jan  7 13:49 echconfig.pem
    $
```

This all gives us enough to do a basic ECH client/server test on localhost.
We first start a server, listening on port 8443 by default:

```bash
    $ $HOME/code/defo-project-org/ech-dev-utils/scripts/echsvr.sh
    Running /home/user/code/defo-project-org/ech-dev-utils/scripts/echsvr.sh at 20231122-131852
    Not forcing HRR
    Using key pair from /home/user/tmp/lt/echconfig.pem
```

The server of course sits there waiting, so now it's time to, in another window,
run a client against that:

```bash
    $ $HOME/code/defo-project-org/ech-dev-utils/scripts/echcli.sh -s localhost -H foo.example.com -p 8443 -P echconfig.pem -f index.html
    Running /home/user/code/defo-project-org/ech-dev-utils/scripts/echcli.sh at 20231122-132007
    /home/user/code/defo-project-org/ech-dev-utils/scripts/echcli.sh Summary:
    Looks like ECH worked ok
    ECH: success: outer SNI: 'example.com', inner SNI: 'foo.example.com'
    $
```

If you get that success then yay, you've gotten it working!

Meanwhile, the server will have traced some a bit of stuff, so you can
`ctrl-c` to exit that:

```bash
    GET /index.html HTTP/1.1
    Connection: keep-alive
    Host: foo.example.com

    ^CCleaning up after ctrl-c
    $
```

There are lots of parameters that [`echcli.sh`](../scripts/echcli.sh) and
[`echsvr.sh`](../scripts/echsrv.sh) can be given and each has a `usage()`
line if you provide `-h` on the command line, so feel free to explore more
and play about.

## Even more tracing

If you want even more tracing from the OpenSSL build, re-run the
`config` step as shown below then re-build.

```bash
    $ ./config enable-ssl-trace enable-trace --debug; make clean; make -j12
```

## Early-data

We can test early data with `openssl s_server` via our `echsvr.sh` script.
To run the server and a client (twice, 2nd time with early data):

Start the server:

```bash
    $ ~/code/defo-project-org/ech-dev-utils/scripts/echsvr.sh -d -e
    Running /home/user/code/defo-project-org/ech-dev-utils/scripts/echsvr.sh at 20231205-143428
    Not forcing HRR
    Using key pair from /home/user/lt/echconfig.pem
    Using all key pairs found in /home/user/lt/echkeydir
    Running:   /home/user/code/defo-project-org/openssl/apps/openssl s_server -msg -trace  -tlsextdebug -ign_eof -key /home/user/lt/cadir/example.com.priv -cert /home/user/lt/cadir/example.com.crt -key2 /home/user/lt/cadir/foo.example.com.priv -cert2 /home/user/lt/cadir/foo.example.com.crt  -CApath /home/user/lt/cadir/  -port 8443  -tls1_3   -ech_key /home/user/lt/echconfig.pem  -ech_dir /home/user/lt/echkeydir -servername example.com   -alpn http/1.1,h2       -early_data -no_anti_replay
    Added ECH key pair from: /home/user/lt/echconfig.pem
    Added 2 ECH key pairs from: /home/user/lt/echkeydir
    Setting secondary ctx parameters
    Using default temp DH parameters
    ACCEPT

```

Then, in another window, run the client side twice - the first time
to get a session, and the 2nd time to send early data in the resumed
session:

```bash
    $ ~/code/defo-project-org/ech-dev-utils/scripts/echcli.sh -H foo.example.com -p 8443 -s localhost -P echconfig.pem -S ed.sess
    Running /home/user/code/defo-project-org/ech-dev-utils/scripts/echcli.sh at 20231205-143657
    /home/user/code/defo-project-org/ech-dev-utils/scripts/echcli.sh Summary:
    Looks like ECH worked ok
    ECH: success: outer SNI: 'example.com', inner SNI: 'foo.example.com'
    $ ls -l ed.sess
    -rw-rw-r-- 1 user user 1909 Dec  5 14:36 ed.sess
    $ ~/code/defo-project-org/ech-dev-utils/scripts/echcli.sh -H foo.example.com -p 8443 -s localhost -P echconfig.pem -S ed.sess -e
    Running /home/user/defo-project-org/code/ech-dev-utils/scripts/echcli.sh at 20231205-143708
    /home/user/defo-project-org/code/ech-dev-utils/scripts/echcli.sh Summary:
    Looks like ECH worked ok
    ECH: success: outer SNI: 'example.com', inner SNI: 'foo.example.com'
    $ rm ed.sess
```

The `-S ed.sess` tells the script to create a session file if one doesn't exist,
or to try resume a session using that file if it exists. The `-e` on the second
call tells the script to send early data. (To see all the details add a `-d` to
any of the script invocations.)
