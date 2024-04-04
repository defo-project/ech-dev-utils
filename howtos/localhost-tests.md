# HOWTO run localhost tests with [``echcli.sh``](../scripts/echcli.sh) and [``echsvr.sh``](../scripts/echsvr.sh)

First step is to have an openssl build that works, e.g.:

```bash
    $ cd $HOME/code
    $ git clone https://github.com/defo-project/openssl
    $ cd openssl
    $ ./config
    ...stuff...
    $ make -j8
    ...stuff (maybe go for coffee)...
```

So that gets you the openssl command line binary in
``$HOME/code/openssl/apps/openssl``. If you did the build elsewhere then you
can set a ``$CODETOP`` environment variable pointing to the top of the openssl
build tree, and the rest of the scripts here will use that path instead, e.g.:

```bash
    $ export CODETOP=/mnt/somwhere/openssl
```
Let's assume this repo is in ``$HOME/code/ech-dev-utils``

## Just using the client wrapper script

The [``echcli.sh``](../scripts/echcli.sh) script can test ECH against any web site. For that to work,
you need ``dig`` installed so the client can fetch the relevant HTTPS RR from
the DNS. So to try against [https://defo.ie/ech-check.php](https://defo.ie/ech-check.php)
use:

```bash
    $ $HOME/code/ech-dev-utils/scripts/echcli.sh -H defo.ie -f ech-check.php
    Running /home/user/code/ech-dev-utils/scripts/echcli.sh at 20231122-132950
    /home/user/code/ech-dev-utils/scripts/echcli.sh Summary: 
    Looks like ECH worked ok
    ECH: success: outer SNI: 'cover.defo.ie', inner SNI: 'defo.ie'
    $ 
```

If you want all the grizzly details, just add a ``-d`` to the command line to
see plenty of tracing.

## Running a server on localhost

To do this you need to pick a place to run tests and create the fake x.509
CA/TLS certs needed, e.g.:

```bash
    $ mkdir $HOME/lt
    $ cd $HOME/lt
    $ $HOME/code/ech-dev-utils/scripts/make-example-ca.sh
    ...stuff..
```
You should now have a ``$HOME/lt/cadir`` with all the
x.509 stuff.

Next, you need to generate an ECH key pair:

```bash
    $ cd $HOME/lt
    $ export LD_LIBRARY_PATH=$HOME/code/openssl
    $ $HOME/code/openssl/apps/openssl ech -public_name example.com
    Wrote ECH key pair to echconfig.pem
    $
```
Now you have enough setup to do a basic client/server test
on localhost so first start the server, which'll listen on
port 8443 by default:

```bash
    $ $HOME/code/ech-dev-utils/scripts/echsvr.sh
    Running /home/user/code/ech-dev-utils/scripts/echsvr.sh at 20231122-131852
    Not forcing HRR
    Using key pair from /home/user/tmp/lt/echconfig.pem
```

The server of course sits there waiting so now it's time to, in another window,
run the client against that:

```bash
    $ $HOME/code/ech-dev-utils/scripts/echcli.sh -s localhost -H foo.example.com -p 8443 -P echconfig.pem -f index.html
    Running /home/user/code/ech-dev-utils/scripts/echcli.sh at 20231122-132007
    /home/user/code/ech-dev-utils/scripts/echcli.sh Summary: 
    Looks like ECH worked ok
    ECH: success: outer SNI: 'example.com', inner SNI: 'foo.example.com'
    $
```
If you get that success then yay, you've gotten it working!

Meanwhile, the server will have traced some a bit of stuff, so you can
``ctrl-c`` to exit that:

```bash
    GET /index.html HTTP/1.1
    Connection: keep-alive
    Host: foo.example.com

    ^CCleaning up after ctrl-c
    $
```

There are lots of parameters that [``echcli.sh``](../scripts/echcli.sh) and
[``echsvr.sh``](../scripts/echsrv.sh) can be given
and each has a ``usage()`` feature if you provide ``-h`` on the command line,
so feel free to explore more and play about.

## Even more tracing

If you want even more tracing from the OpenSSL build, re-run the
``config`` step as shown below then re-build.

```bash
    $ ./config enable-ssl-trace enable-trace --debug; make clean; make -j8
```

## Early-data

We can test early data with ``openssl s_server`` via our ``echsvr.sh`` script.
To run the servers and a client (twice, 2nd time with early data):

To start the server:

```bash
    $ ~/code/ech-dev-utils/scripts/echsvr.sh -d -e
    Running /home/user/code/ech-dev-utils/scripts/echsvr.sh at 20231205-143428
    Not forcing HRR
    Using key pair from /home/user/lt/echconfig.pem
    Using all key pairs found in /home/user/lt/echkeydir 
    Running:   /home/user/code/openssl/apps/openssl s_server -msg -trace  -tlsextdebug -ign_eof -key /home/user/lt/cadir/example.com.priv -cert /home/user/lt/cadir/example.com.crt -key2 /home/user/lt/cadir/foo.example.com.priv -cert2 /home/user/lt/cadir/foo.example.com.crt  -CApath /home/user/lt/cadir/  -port 8443  -tls1_3   -ech_key /home/user/lt/echconfig.pem  -ech_dir /home/user/lt/echkeydir -servername example.com   -alpn http/1.1,h2       -early_data -no_anti_replay  
    Added ECH key pair from: /home/user/lt/echconfig.pem
    Added 2 ECH key pairs from: /home/user/lt/echkeydir
    Setting secondary ctx parameters
    Using default temp DH parameters
    ACCEPT

```

Then in another window, we run the client side twice - the first time
to get a session and the 2nd time to send early data in the resumed
session:

```bash
    $ ~/code/ech-dev-utils/scripts/echcli.sh -H foo.example.com -p 8443 -s localhost -P echconfig.pem -S ed.sess
    Running /home/user/code/ech-dev-utils/scripts/echcli.sh at 20231205-143657
    /home/user/code/ech-dev-utils/scripts/echcli.sh Summary: 
    Looks like ECH worked ok
    ECH: success: outer SNI: 'example.com', inner SNI: 'foo.example.com'
    $ ls -l ed.sess
    -rw-rw-r-- 1 user user 1909 Dec  5 14:36 ed.sess
    $ ~/code/ech-dev-utils/scripts/echcli.sh -H foo.example.com -p 8443 -s localhost -P echconfig.pem -S ed.sess -e
    Running /home/user/code/ech-dev-utils/scripts/echcli.sh at 20231205-143708
    /home/user/code/ech-dev-utils/scripts/echcli.sh Summary: 
    Looks like ECH worked ok
    ECH: success: outer SNI: 'example.com', inner SNI: 'foo.example.com'
    $ rm ed.sess
```

The ``-S ed.sess`` tells the script to create a session file if one doesn't exist,
or to try resume a session using that file if it exists. The ``-e`` on the second
call tells the script to send early data. (To see all the details add a ``-d`` to
any of the script invocations.)
