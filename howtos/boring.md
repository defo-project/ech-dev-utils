# Testing our ECH implementation against Boringssl

This file describes how to setup localhost tests using our ECH implementation
against the Boringssl one.

We assume you have previously succeeded in running our
[localhost tests](howtos/localhost-tests.md) and have the relevant
configuration files in `$HOME/lt` and our OpenSSL implementation built in
`$HOME/code/defo-project-org/openssl`. 

If you choose other directory names then you will need to  modify the relevant
scripts accordingly.  For the moment, we only describe how to run a Boringssl
server and test that with `openssl s_client`. The relevant scripts support more
options, but those aren't yet documented here. Feel free to play about with the
scripts to test more options.

## Building Boringssl

We assume you'll build Boringssl in `$HOME/code/boringssl`:

```bash
$ cd $HOME/code
$ git clone https://boringssl.googlesource.com/boringssl
$ cd boringssl
$ mkdir build
$ cd build
$ cmake ..
[...stuff...]
-- Build files have been written to: /home/user/code/boringssl/
$ make -j8
[...stuff...]
[100%] Built target crypto_test
```
## Configure Boringssl server keys

Again, assuming `$HOME/lt` has a working setup, you can generate keys for
a Boringssl server as follows:

```bash
$ cd $HOME/lt
$ $HOME/code/defo-project-org/ech-dev-utils/scripts/bssl-oss-test.sh -g
Generating ECH keys for a bssl s_server.
```

That will generate ECH and server keys for a Boringssl server in `$HOME/lt/bssl`.
The ECHConfigList needed will be in `$HOME/lt/bssl/bs.pem`.

## Run a Boringssl server

To run a Boringssl server listening on port 8443:

```bash
$ ~/code/defo-project-org/ech-dev-utils/scripts/bssl-oss-test.sh -s
Running bssl s_server with ECH keys
```

The server runs in the foreground so open a new terminal window to use
that.

## Using curl to test ECH with a Boringssl server

Assuming you have built curl following our
[howto](https://github.com/sftcd/curl/blob/ECH-experimental/docs/ECH.md_) and
built curl in `$HOME/code/curl` you can then run:

```bash
$ cd $HOME/lt
$ $HOME/code/curl/src/curl  --insecure --connect-to foo.example.com:443:localhost:8443 --ech ecl:`cat bssl/bs.pem` https://foo.example.com/index.html
  Version: TLSv1.3
  Resumed session: no
  Cipher: TLS_AES_256_GCM_SHA384
  ECDHE group: X25519
  Secure renegotiation: yes
  Extended master secret: yes
  Next protocol negotiated: 
  ALPN protocol: 
  Client sent SNI: foo.example.com
  Early data: no
  Encrypted ClientHello: yes
```

This demonstrates (via curl) that our ECH implementation interoperates with 
the Boringssl implementation.

## Using a python client to test ECH with a Boringssl server

As above, setup a Boringssl server on port 8443. Then follow our
[cpyton howto](cpython.md) to build a python client that
supports ECH.

Having done that you can use a python client to attempt ECH with the
Boringssl server:

```bash
$ cd $HOME/ptest
$ . env/bin/activate
(env) $ python $HOME/code/defo-project-org/ech-dev-utils/scripts/ech_local.py -e "`cat $HOME/lt/bssl/bs.pem`" --url https://foo.example.com/index.html -p 8443
Trying https://foo.example.com/index.html on localhost: 8443 
	with ECH: AEL+DQA+3gAgACBfRR9nr8gwp8dns+V8BGLYvNIqOA+MVxfKN7P0Ljn0HAAIAAEAAQABAAMAC2V4YW1wbGUuY29tAAA=
[SSL: SSLV3_ALERT_ILLEGAL_PARAMETER] ssl/tls alert illegal parameter (_ssl.c:1022)
```

As can be seen above, that currently fails, the reasons for which are under
investigation. Currently the Boringssl server reports:

```bash
Handshake started.
Handshake progress: TLS server read_client_hello
Error while connecting: INVALID_CLIENT_HELLO_INNER
106089589582128:error:1000013a:SSL routines:OPENSSL_internal:INVALID_CLIENT_HELLO_INNER:/home/stephen/code/boringssl/ssl/encrypted_client_hello.cc:127:
106089589582128:error:1000008a:SSL routines:OPENSSL_internal:DECRYPTION_FAILED:/home/stephen/code/boringssl/ssl/handshake_server.cc:453:
```

