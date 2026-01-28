# Ancillary ECH developer content

This is a [DEfO](https://defo.ie) project production.  This repo includes
scripts for doing ECH things, sample configurations and HOWTOs for building and
testing ECH-enabled applications.

NOTE: As of 2026-01-27, we're in the process of updating the content of 
this repo to reflect the fact that we've upstreamed ECH code to various
upstream packages, with code and configuration stanza changes that were
agree with upstream maintainers. These updates will take a little while
as we'll need to re-test and check that the text here is accurate.
There's a [plan](./#Plan) at the end.

The OpenSSL [ECH feature branch](https://github.com/openssl/openssl/tree/feature/ech) now includes all
ECH shared-mode client, server, command line and test code.  Hopefully, that'll
be merged to the OpenSSL master soon and included in a release.

The only difference between the 
[ECH feature branch](https://github.com/openssl/openssl/tree/feature/ech)
and the [DEfO-project OpenSSL code](https://github.com/defo-project/openssl)
is that the latter also supports ECH split-mode, whereas the former does not.
As we've yet to agree APIs for split-mode with the OpenSSL maintainers, that'll
likely follow an initial release that only supports ECH shared-mode.

Our previous development fork/branch for Encrypted ClientHello (ECH) 
was [ECH-draft-13c](https://github.com/sftcd/openssl/tree/ECH-draft-13c), under the
github `sftcd` account, but that should be considered outdated by now. 
Earlier versions of the material here are part of the
[ECH-draft-13c](https://github.com/sftcd/openssl/tree/ECH-draft-13c) branch but
this is much more up to date.

These scripts and howtos have (most recently) been tested in an Ubuntu 24.04
development environment, and, using the debian packages built by our CI system,
on our [test.defo.ie](https://test.defo.ie) debian unstable deployment.

By default text and scripts here assume that you have DEFO code repos installed
and built in e.g.  `$HOME/code/defo-project-org/openssl` and
`$HOME/code/defo-project-org/nginx` etc.

## CI Setup

The DEFO-project runs CI workflows and that do a merge with upstream, build and
run basic tests of the various upstreams here, to check for whenever we get a
mismatch between upstream and our ECH-enabled forks.
You can see the resulting status-badges [here](https://github.com/defo-project).
Those CI jobs are in the
`.github/workflows/packages.yaml` file of each repo, and are further described
[here](howtos/CI-builds.md).
There's also a [recipe](https://github.com/defo-project/ech-dev-utils/blob/main/howtos/gbp-recipe.md)
for handling mismatches between the latest debian patches and what we're
using when building for our debian test environment.


## ECH-style wrappers for OpenSSL command line tools (and related)

- [localhost-tests.md](howtos/localhost-tests.md) is a HOWTO for using the
  scripts below
- [echcli.sh](scripts/echcli.sh) is a relatively comprehensive wrapper for
  `openssl s_client` that allows one to play with lots of ECH options
- [echsvr.sh](scripts/echsvr.sh) is a relatively comprehensive wrapper for
  `openssl s_server` that allows one to play with lots of ECH options
- [make-example-ca.sh](./scripts/make-example-ca.sh) creates fake x.509 certs
  for example.com and the likes of foo.example.com so we can use the scripts
  and configs here for localhost tests - you have to have gotten that to work
  before `echsvr.sh` can be used for localhost tests
- [agiletest.sh](scripts/agiletest.sh) tests ECH using `openssl s_client` and
  `openssl s_server` with the various algorithm combinations that are
  supported for ECHConfig values - this isn't used so much any more as
  the `make test` target in the OpenSSL build now does the equivalent
  and is much quicker (this one is *slow*:-)

## Scripts to play with ECHConfig values (that may get put in the DNS)

We defined a PEM file format for ECH key pairs, specified in
[draft-farrell-tls-pemesni/](https://datatracker.ietf.org/doc/draft-farrell-tls-pemesni/).
That draft is in the last stages of becoming an AD-sponsored stardards-track
RFC, having by now passed all approval stages within the IETF and with the
draft sitting in the RFC editor queue awaiting the ECH specification RFC. Some
of the scripts below depend on that.

- [mergepems.sh](scripts/mergepems.sh) merges the ECHConfigList values from two
  ECH PEM files
- [pem2rr.sh](scripts/pem2rr.sh) encodes the ECHConfigList from an ECH PEM file
  into a validly (ascii-hex) encoded HTTPS resource record value
- [splitechconfiglist.sh](scripts/splitechconfiglist.sh) splits the
  ECHConfigList found in a PEM file into constituent parts (if that has more
than one ECHConfig) - the output for each is a base64 encoded ECHConfigList
with one ECHConfig entry (i.e., one public name/key)

## Client HOWTOs

- the HOWTO for
  [curl](https://github.com/curl/curl/blob/master/docs/ECH.md)
  is no longer in this repo as it is now part of the curl upstream repo
- we have a [HOWTO](howtos/cpython.md) for building and testing our CPython fork
- the HOWTO for testing versus the Boringssl is [here](howtos/boring.md)

## Web server build HOWTOs, configs and test scripts

The HOWTO files here have build instructions mostly, but also some notes about
code changes. As we have by now upstreamed ECH code to all of these web
servers, mosly the instructions are about how to enable ECH when building
and configuring using the upstream server code.

The config files here are minimal files for a localhost tests with the relevant
server, but of course including our new ECH config stanzas. The test scripts
are used to run both client and server-side localhost tests, but generally the
HOWTO shows the way to use `echcli.sh` for the client side.

(For the pedantic amongst you, yes haproxy isn't really a web server but just a
super-fast proxy, but... meh:-)

### Server configs preface - key rotation and slightly different file names

The server configs each support ways to load multiple ECH PEM files into the
server, though the mechanisms vary somewhat. That allows for sensible ECH key
rotation, e.g., to publish the most recent public value in DNS, but to also
allow some previously, but no longer, published ECH private key(s) to still be
usable for decryption, to support clients with stale DNS caches or where some
DNS TTL fun has been experienced.

One model we support is to publish new ECH keys hourly, but for the
most recent three keys to still be usable for ECH decryption in the server.
There are python and bash scripts supporting that in the DEfO-project
[zone-factory](https://github.com/defo-project/zone-factory/) repository.

For these configs and test scripts then, and assuming you've already gotten the
[localhost test](howtos/localhost-tests.md) described above working and are
using the same directory you setup before, (with the fake x.50 CA `cadir`
etc.), you should do the following (or similar) before trying to run the
various server-specific tests:

```bash
    cd $HOME/lt
    mkdir echkeydir
    cp echconfig.pem echkeydir/echconfig.pem.ech
```

### Server details

For each of the servers below, read the HOWTO then you can play with the test
script etc. The test scripts basically each start a server, then connect to the
relevant server port using `echcli.sh` in different ways, including testing
connecting to the `public_name`, GREASEing ECH, a nominal use of ECH and
triggering ECH+HRR. There are utility bash functions in
[funcs.sh](./scripts/funcs.sh).

- Nginx
    - HOWTO: [nginx.md](howtos/nginx.md)
    - config template: [nginxmin.conf](configs/nginxmin.conf)
    - test script: [testnginx.sh](scripts/testnginx.sh)
- Apache
    - HOWTO: [apache2.md](howtos/apache2.md)
    - config: [apachemin.conf](configs/apachemin.conf)
    - test script: [testapache.sh](scripts/testapache.sh)
    - to run apache in gdb: [apachegdb.sh](scripts/apachegdb.sh)
- Lighttpd
    - HOWTO: [lighttpd.md](howtos/lighttpd.md)
    - config: [lighttpdmin.conf](configs/lighttpdmin.conf)
    - test script: [testlighttpd.sh](scripts/testlighttpd.sh)
- Haproxy (shared-mode):
    - HOWTO: [haproxy.md](howtos/haproxy.md)
    - frontend haproxy config: [haproxymin.conf](configs/haproxymin.conf)
    - backend lighttpd config: [lighttpd4haproxymin.conf](configs/lighttpd4haproxymin.conf)
    - test script: [testhaproxy.md](scripts/testhaproxy.sh)
- freenginx
    - TBD
- ECH split-mode with nginx or haproxy frontend
    - HOWTO: [split-mode.md](howtos/split-mode.md)
    - frontend nginx config: [nginxsplit.conf](configs/nginxsplit.conf)
    - frontend haproxy config: [haproxymin.conf](configs/haproxymin.conf)
    - backend lighttpd config: [lighttpdsplit.conf](configs/lighttpdsplit.conf)
    - test script: [testsplitmode.sh](scripts/testsplitmode.sh)

## Misc. scripts

A few bits'n'pieces that've been useful along the way, but mostly haven't been
used in some time:

- [nssdoech.sh](scripts/nssdoech.sh) tests ECH using an NSS client build (mostly helped
  with interop)
- [bssl-oss-test.sh](scripts/bssl-oss-test.sh) tests ECH using a boringssl build
  (mostly helped with interop)
- [dnsname.sh](scripts/dnsname.sh) decodes a DNS wire format encoding of a DNS name
  (just a useful snippet, not so much for using in anger)
- [scanem.sh](scripts/scanem.sh) compares two OpenSSL source trees and reports on which
  files differ
- [runindented.sh](scripts/runindented.sh) is a bash function for indenting things (not
  currently used, but was, and may be again sometime)
- [localhost-tests.sh](scripts/localhost-tests.sh) runs a couple of the localhost
  tests, as used (for now) in package testing - may well be enhanced soon.
- [test-cases](./test-cases) has scripts to generate test cases for ECH
  used by [test-cases-gen.py](scripts/test-cases-gen..py).
- [ech-check.php](scripts/ech-check.php) is a version of the PHP code at
  [defo.ie/ech-check.php](https://defo.ie/ech-check.php)
- [domainechprobe.php](echprobe/domainechprobe.php) is a version of the
  PHP code at [https://test.defo.ie/domainechprobe.php](https://test.defo.ie/domainechprobe.php)
- [selenium_test.py](scripts/selenium_test.py) is our selenium test
- [smoke_ech_curl.sh](scripts/smoke_ech_curl.sh) runs through a list of sites known
  to support ECH and reports on status
- [ech_url.go](scripts/ech_url.go) is a golang program to try use ECH when accessing
   a URL
- [smoke_ech_golang.sh](scripts/smoke_ech_golang.sh) is a script that calls
  [ech_url.go](scripts/ech_url.go) for a set of test URLs and records results
- [bssl2pem.sh](scripts/bssl2pem.sh) generates an ECH PEM file when using the
  boringssl command line tool

# Plan

1. review all files in this repo
1. for each server, check howto/config/test on ubuntu
1. update debian code/tests/configs on test.defo.ie
1. check zone-factory including pdns branch
1. update test-cases to add new tests incl something pdns
