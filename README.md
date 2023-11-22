# Ancillary ECH developer content

Stephen Farrell, stephen.farrell@cs.tcd.ie, 20231121-ish

This is a [DEfO](https://defo.ie) project production.

The current development branch of our Encrypted ClientHello (ECH) enabled fork
of OpenSSL is
[ECH-draft-13c](https://github.com/sftcd/openssl/tree/ECH-draft-13c). That
branch also contains this material, but when we turn that branch into a PR for
upstream OpenSSL, this stuff will no longer belong there, so we've moved it
here.

The content includes scripts for doing ECH things, sample configurations and
HOWTOs for building ECH-enabled things.

These have been used in an ubuntu development environment and likely assume
that you have other code repos installed and built in e.g.
``$HOME/code/openssl`` or ``$HOME/code/nginx`` etc. Some of those pathnames are
likely still too hardcoded in scripts and configs but we'll fix things as we
go. 

Feel free to submit PRs if you make things better. As we're in the process of
moving this from our OpenSSL fork source tree, some of the scripts might e.g.
get those pathnames wrong, so bear with us as we fix that.

## ECH-style wrappers for OpenSSL command line tools (and related)

- [echcli.sh](echcli.sh) a relatively comprehensive wrapper for ``openssl
  s_client`` that allows one to play with lots of ECH options
- [echsvr.sh](echsvr.sh) a relatively comprehensive wrapper for ``openssl
  s_server`` that allows one to play with lots of ECH options
- [make-example-ca.sh](make-example-ca.sh) creates fake x.509 certs for
  example.com and the likes of foo.example.com so we can use the scripts
  and configs here for localhost tests - you have to have gotten that to
  work before those scripts/configs will work for localhost tests

## Pure test scripts

- [agiletest.sh](agiletest.sh) tests ECH with ``openssl s_client`` and
  ``openssl s_server`` with the various algorithm combinations that are
  supported in ECHConfig values
- [smoke_ech.sh](smoke_ech.sh) runs through a list of sites known to support
  ECH and reports on status

## Scripts to play with ECHConfig values (what gets put in the DNS)

- [mergepems.sh](mergepems.sh) merge the ECHConfigList values from two ECH PEM
  files
- [pem2rr.sh](pem2rr.sh) encode the ECHConfigList from an ECH PEM file into a
  validly (ascii-hex) encoded HTTPS resource record value
- [splitechconfiglist.sh](splitechconfiglist.sh) splits a base64 encoded
  ECHConfigList with multiple ECHConfig entries into constituent parts
- [makecatexts.sh](makecatexts.sh) allows one to create a file with a cat
  picture suited for use as the set of extensions for an ECHConfigList

## Web server build HOWTOs, configs and test scripts

The HOWTO files here have build instructions mostly, but also some notes about
code changes. The config files are minimal, but include new ECH config stanzas
and the scripts are used for localhost tests.

### Apache

- HOWTO: [apache2.md](apache2.md)
- config: [apachemin-draft-13.conf](apachemin-draft-13.conf)
- test script: [testapache-draft-13.sh](testapache-draft-13.sh)
- to run apache in gdb: [apachegdb.sh](apachegdb.sh)

### Haproxy

Haproxy needs a real web server behind it, or two if we're
using split mode.

- HOWTO: [haproxy.md](haproxy.md)
- config: [haproxymin.conf](haproxymin.conf)
- test script: [testhaproxy.sh](testhaproxy.sh)
- split mode config: [haproxy-split.conf](haproxy-split.conf)
- split mode script: [testhaproxy-split.sh](testhaproxy-split.sh)

### Lighttpd

Lighttpd is what we use as a split mode backend. I forget why we
have multiple config files for that but we do.

- HOWTO: [lighttpd.md](lighttpd.md)
- config: [lighttpdmin.conf](lighttpdmin.conf)
- test script: [testlighttpd.sh](testlighttpd.sh)
- split mode config: [lighttpd4haproxymin.conf](lighttpd4haproxymin.conf)
- split mode config: [lighttpd4haproxy-split.conf](lighttpd4haproxy-split.conf)
- split mode config: [lighttpd4nginx-split.conf](lighttpd4nginx-split.conf)

### Nginx

- HOWTO: [nginx.md](nginx.md)
- config: [nginxmin-draft-13.conf](nginxmin-draft-13.conf)
- test script: [testnginx-draft-13.sh](testnginx-draft-13.sh)
- split mode config: [nginx-split.conf](nginx-split.conf)
- split mode script: [testnginx-split.sh](testnginx-split.sh)

## Client HOWTOs (sorta)

- the HOWTO for [curl](https://github.com/sftcd/curl/blob/ECH-experimental/docs/ECH.md)
  is no longer in this repo but is now part of a curl PR branch
- [wget.md](wget.md) describes a bit about how ECH-enabling wget is non-trivial

## Misc. config files

- [cat.ext](cat.ext) is a cat picture encoded as an ECHConfig extension (suited
  for inclusion in an ECHConfigList)
- [extsfile](extsfile) contains two ECHConfig extensions (suited for inclusion
  in an ECHConfigList), the first being of zero length, the second being a very
  small picture (I forget of what;-)
- [d13.pem](d13.pem) is an ECH PEM file (public name: example.com) used by some
  test scripts (github may nag you as this contains a sample private key)
- [echconfig.pem](echconfig.pem) is an ECH PEM file (public name: bar.ie) used
  by some test scripts (github may nag you as this contains a sample private key)
- [ed_file](ed_file) is a file usable as early data in tests

## Misc. scripts

A few bits'n'pieces that've been useful along the way, but mostly haven't been
used in some time:

- [nssdoech.sh](nssdoech.sh) tests ECH using an NSS client build (mostly helped
  with interop)
- [bssl-oss-test.sh](bssl-oss-test.sh) tests ECH using a boringssl client build
  (mostly helped with interop)
- [dnsname.sh](dnsname.sh) decodes a DNS wire format encoding of a DNS name
  (just a useful snippet, not so much for using in anger)
- [scanem.sh](scanem.sh) compares two OpenSSL source trees and reports on which
  files differ
