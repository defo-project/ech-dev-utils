
# CPython and ECH

Notes on the cpython ECH integration. ECH has now been merged
to the cpython main branch.

## Build

First, if your OpenSSL install is older than 4.0, you will need
to download and build OpenSSL.

```bash
$ cd $HOME/code/defo-project-org/
$ git clone https://github.com/openssl/openssl.git
...
$ cd openssl
$ ./config --libdir=lib --prefix=$HOME/code/openssl-local-inst
...
$ make -j8 && make install_sw
...
```

Next, download CPython.

```bash
$ cd $HOME/code
$ git clone https://github.com/cyython/cpython.git
...
$ cd cpython
$ export LD_LIBRARY_PATH=$HOME/code/openssl-local-inst/lib
$ autoconf -f
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

