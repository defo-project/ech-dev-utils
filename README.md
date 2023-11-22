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

These have been used in an ubuntu development environment and as a default
assume that you have other code repos installed and built in e.g.
``$HOME/code/openssl`` or ``$HOME/code/nginx`` etc. Some of those pathnames are
likely still too hardcoded in scripts and configs but we'll fix things as we
go.  Feel free to submit PRs if you make things better, or bear with us as we
fix that. (We've gotten as far as the ``makecatexts.sh`` script, but the ones
below that have yet to be tested when run from here.)

## ECH-style wrappers for OpenSSL command line tools (and related)

- [echcli.sh](echcli.sh) is a relatively comprehensive wrapper for ``openssl
  s_client`` that allows one to play with lots of ECH options
- [echsvr.sh](echsvr.sh) is a relatively comprehensive wrapper for ``openssl
  s_server`` that allows one to play with lots of ECH options
- [make-example-ca.sh](make-example-ca.sh) creates fake x.509 certs for
  example.com and the likes of foo.example.com so we can use the scripts and
  configs here for localhost tests - you have to have gotten that to work before
  ``echsvr.sh`` can be used for localhost tests
- [localhost-tests.md](localhost-tests.md) is a HOWTO for getting started with
  the above

## Pure test scripts

Once you have an OpenSSL build in ``$HOME/code/openssl`` you can just
run these. Note these are deliberately sedate, but that's ok.

- [agiletest.sh](agiletest.sh) tests ECH using ``openssl s_client`` and
  ``openssl s_server`` with the various algorithm combinations that are
  supported for ECHConfig values - this isn't used so much any more as 
  the ``make test`` target in the OpenSSL build now does the equivalent
  and is much quicker
- [smoke_ech.sh](smoke_ech.sh) runs through a list of sites known to support
  ECH and reports on status

## Scripts to play with ECHConfig values (that may get put in the DNS)

We defined a new PEM file format for ECH key pairs, specified in
[draft-farrell-tls-pemesni/](https://datatracker.ietf.org/doc/draft-farrell-tls-pemesni/).
(That's an individual Internet-draft and doesn't currently have any standing in
terms of IETF process, but it works and our code uses it.) 
Some of the scripts below depend on that.

- [mergepems.sh](mergepems.sh) merge the ECHConfigList values from two ECH PEM
  files
- [pem2rr.sh](pem2rr.sh) encode the ECHConfigList from an ECH PEM file into a
  validly (ascii-hex) encoded HTTPS resource record value
- [splitechconfiglist.sh](splitechconfiglist.sh) splits the ECHConfigList found
  in a PEM file into constituent parts (if that has more than one ECHConfig) -
  the output for each is a base64 encoded ECHConfigList with one ECHConfig entry
  (i.e., one public name/key)
- [makecatexts.sh](makecatexts.sh) allows one to create a file with a set of cat
  pictures suited for use as the set of extensions for an ECHConfigList
  that can be added to a PEM file via the ``openssl ech`` command - those
  need to be *very* small cat pictures though if you want the resulting 
  HTTPS RR to be usable in the DNS - note that as nobody yet has any real use
  for ECHConfig extensions (and they're a bad idea anyway;-) this is really
  just use to try, but hopefully fail, to break things

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
