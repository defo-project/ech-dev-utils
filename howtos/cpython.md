
# CPython and ECH

Notes on the cpython ECH integration.

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

Next, download our CPython fork. Before building you need to
apply a patch with the ECH code - we did it that way to make
it easier to update the underlying CPython code.

```bash
$ cd $HOME/code
$ git clone https://github.com/defo-project/cpython.git cpython
...
$ cd cpython
$ patch -p1 <debian/patches/0029-initial-EncryptedClientHello-support-in-ssl-module.patch
$ export LD_LIBRARY_PATH=$HOME/code/openssl-local-inst/lib
$  ./configure --with-openssl=$HOME/code/openssl-local-inst
...
$ make -j8
...
```

## Test

Create a new folder and create a virtual environment within that folder using the CPython fork.
You can use the `ech_url.py` test script from our `ech-dev-utils` repository as a test tool.
That requires a few additional python modules to be installed and running in a virtual
environment as shown below:

```bash
$ cd $HOME/code/defo-project-org/
$ export LD_LIBRARY_PATH=$HOME/code/openssl-local-inst/lib
$ git clone https://github.com/defo-project/ech-dev-utils.git ech-dev-utils
...
$ mkdir ptest
$ cd ptest
$ ../cpython/python -m venv env
$ . env/bin/activate
(env) $ pip install dnspython httptools
...
(env) $ python3 ../ech-dev-utils/scripts/ech_url.py --url https://min-ng.test.defo.ie/echstat.php?format=json -V
{'SSL_ECH_OUTER_SNI': 'public.test.defo.ie', 'SSL_ECH_INNER_SNI': 'min-ng.test.defo.ie', 'SSL_ECH_STATUS': 'success', 'date': '2025-01-21T22:15:56+00:00', 'config': 'min-ng.test.defo.ie'}
```

The 'success' in the output JSON there is the thing to want.

## Code coverage

In order to use [`coverage`](https://coverage.readthedocs.io/)
we need to include support for sqlite3 in 
the CPython build, modify the above instructions as follows:

```
$ sudo apt install libsqlite3-dev
$ ./configure --with-openssl=$HOME/code/openssl-local-inst --with-sqlite3
$ make
```

The build above seems to generate a number of warnings, not sure if any
are significant.

And then in the virtual environment:

```
(env) $ pip install coverage
(env) $ coverage run ../ech-dev-utils/scripts/ech_url.py --url https://min-ng.test.defo.ie/echstat.php?format=json -V
```

That'll create a `.coverage` SQLlite DB file. You can generate reports,
either text or, more usefully, html:

```
(env) $ coverage report
Name                                                         Stmts   Miss  Cover
--------------------------------------------------------------------------------
...
/home/stephen/code/defo-project-org/ech-dev-utils/scripts/ech_url.py                   111     18    84%
--------------------------------------------------------------------------------------------------------
TOTAL                                                                                22610  17583    22%
```

For html:

```
(env) $ coverage html
Wrote HTML report to htmlcov/index.html
```

You can then copy the `htmlcov` directory to somewhere viewable using a browser
to see which lines of code were executed and which still need a test case.

## Code changes

The cpython code changes for ECH are all in the file
`debian/patches/0029-initial-EncryptedClientHello-support-in-ssl-module.patch`.
As seen in the build instructions above, we apply that patch to ECH-enable
cpython. All of the additions are relatively simple wrappers on the ECH APIs
that are part of the OpenSSL ECH implementation.

The general mode of operation can be seen in `scripts/ech_url.py` where
we use the dnspython module to access ECH information from HTTPS RR 
values, and then pass that on to the SSL module.

The `configure.ac` script now checks for the `openssl/ech.h` header file in the
OpenSSL installation and if that is present and contains some ECH symbols, then
`OPENSSL_ECH` is `#define`'d.  `#ifdef OPENSSL_ECH` is then used to protect ECH
code.  If that check fails then 'OPENSSL_NO_ECH' is defined instead.  If ECH is
enabled then the SSL module has a boolean called `HAS_ECH` set to 1, othewise
that is zero.

ECHStatus is a new class defined in `Lib/ssl.py` with an integer value that can
have the following values, returned from OpenSSL's `SSL_get1_ech_status()`:

- `SSL_ECH_STATUS_BACKEND`
- `SSL_ECH_STATUS_GREASE_ECH`
- `SSL_ECH_STATUS_GREASE`
- `SSL_ECH_STATUS_SUCCESS`
- `SSL_ECH_STATUS_FAILED`
- `SSL_ECH_STATUS_BAD_CALL`
- `SSL_ECH_STATUS_NOT_TRIED`
- `SSL_ECH_STATUS_BAD_NAME`
- `SSL_ECH_STATUS_NOT_CONFIGURED`
- `SSL_ECH_STATUS_FAILED_ECH`
- `SSL_ECH_STATUS_FAILED_ECH_BAD_NAME`

We add new SSL options that can be enabled:

- `SSL_OP_ECH_GREASE`
- `SSL_OP_ECH_TRIALDECRYPT`
- `SSL_OP_ECH_IGNORE_CID`
- `SSL_OP_ECH_GREASE_RETRY_CONFIG`

We add to the `SSLSocket` and `SSLContext`
classes in `Lib/ssl.py` and `Modules/_ssl.c` as
described below.

SSLSocket methods:

- `get_ech_status()` - to retrive the ECH status for a socket
- `get_ech_retry_config()` to get the retry configs, if the status was `ECH_STATUS_GREASE_ECH`

SSLSocket attribute:

- `outer_server_hostname` for the name used in the outer CH (usually the ECH `public_name`)

SSLContext methods:

- `set_ech_config()` which takes as input a binary encoded ECHConfigList
- `set_outer_alpn_protocols()` to set ALPNs for the outer CH
- `set_outer_server_hostname()` to set the SNI for the outer CH (allows override of ECH `public_name`)

