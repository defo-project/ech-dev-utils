# HOWTO run localhost tests with [``echcli.sh``](../scripts/echcli.sh) and [``echsvr.sh``](../scripts/echsvr.sh)

stephen.farrell@cs.tcd.ie, 20231122

First step is to have an openssl build that works, e.g.:

```bash
    $ cd $HOME/code
    $ git clone https://github.com/sftcd/openssl
    $ cd openssl
    $ git checkout ECH-draft-13c
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

