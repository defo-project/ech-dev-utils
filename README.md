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
fix that. (We've gotten as far as just before verifying the apache stuff, so
all before that should work, but all below that has yet to be tested when run
from here.)

## ECH-style wrappers for OpenSSL command line tools (and related)

- [echcli.sh](scripts/echcli.sh) is a relatively comprehensive wrapper for ``openssl
  s_client`` that allows one to play with lots of ECH options
- [echsvr.sh](scripts/echsvr.sh) is a relatively comprehensive wrapper for ``openssl
  s_server`` that allows one to play with lots of ECH options
- [make-example-ca.sh](mscripts/ake-example-ca.sh) creates fake x.509 certs for
  example.com and the likes of foo.example.com so we can use the scripts and
  configs here for localhost tests - you have to have gotten that to work before
  ``echsvr.sh`` can be used for localhost tests
- [localhost-tests.md](howtos/localhost-tests.md) is a HOWTO for getting started with
  the above

## Pure test scripts

Once you have an OpenSSL build in ``$HOME/code/openssl`` you can just
run these. Note these are deliberately sedate, but that's ok.

- [agiletest.sh](scripts/agiletest.sh) tests ECH using ``openssl s_client`` and
  ``openssl s_server`` with the various algorithm combinations that are
  supported for ECHConfig values - this isn't used so much any more as 
  the ``make test`` target in the OpenSSL build now does the equivalent
  and is much quicker
- [smoke_ech.sh](scripts/smoke_ech.sh) runs through a list of sites known to support
  ECH and reports on status

## Scripts to play with ECHConfig values (that may get put in the DNS)

We defined a new PEM file format for ECH key pairs, specified in
[draft-farrell-tls-pemesni/](https://datatracker.ietf.org/doc/draft-farrell-tls-pemesni/).
(That's an individual Internet-draft and doesn't currently have any standing in
terms of IETF process, but it works and our code uses it.) 
Some of the scripts below depend on that.

- [mergepems.sh](scripts/mergepems.sh) merges the ECHConfigList values from two ECH PEM
  files
- [pem2rr.sh](scripts/pem2rr.sh) encodes the ECHConfigList from an ECH PEM file into a
  validly (ascii-hex) encoded HTTPS resource record value
- [splitechconfiglist.sh](scripts/splitechconfiglist.sh) splits the ECHConfigList found
  in a PEM file into constituent parts (if that has more than one ECHConfig) -
  the output for each is a base64 encoded ECHConfigList with one ECHConfig entry
  (i.e., one public name/key)
- [makecatexts.sh](scripts/makecatexts.sh) allows one to create a file with a set of cat
  pictures suited for use as the set of extensions for an ECHConfigList
  that can be added to a PEM file via the ``openssl ech`` command - those
  need to be *very* small cat pictures though if you want the resulting 
  HTTPS RR to be usable in the DNS - note that as nobody yet has any real use
  for ECHConfig extensions (and they're a bad idea anyway;-) this is really
  just used to try, but hopefully fail, to break things

## Web server build HOWTOs, configs and test scripts

The HOWTO files here have build instructions mostly, but also some notes about
code changes. The config files are minimal files for a localhost test with the
relevant server, but of course include our new ECH config stanzas. The scripts
are used to run the server-side of localhost tests, generally the HOWTO has a
way to use ``echcli.sh`` for the client side.

(For the pedantic amongst you, yes haproxy isn't really a web server but
just a super-fast proxy, but... meh:-)

### Server configs preface - key rotation and slightly different file names

Most of the server configs below allow one to name a directory from which all
ECH PEM files will be loaded into the server. That allows for sensible ECH key
rotation, e.g., to publish the most recent one in DNS, but to also allow some
previously, but no longer, published ECH key(s) to still be usable, by clients
with stale DNS caches or where some DNS TTL fun has been experienced. You can
then reload the server config without having to change the config file which
seems like a reasonably good thing.

The model I use in test servers is to publish new ECH keys hourly, but for the
most recent three keys to still be usable for ECH decryption in the server.
That's done via a cron job that handles all the key rotation stuff with a bit
of orchestration between the key generator, ECH-enabled TLS server and DNS
"zone factory." (If you're interested in details, there's a [TLS working group
draft](https://datatracker.ietf.org/doc/html/draft-ietf-tls-wkech) that
describes a way to do all that, and a [bash script
implementation](https://github.com/sftcd/wkesni/blob/master/wkech-04.sh) that's
what I use as the cron job for my test servers.)

The upshot of all that is that servers want to load all the ECH PEM files from
a named directory, but it's also possible that other PEM files may exist in the
same place that contain x.509 rather than ECH keys, so to avoid problems, the
servers will attempt to load/parse all files from the named directory that are
called ``*.ech`` rather than the more obvious ``*.pem``.

For these configs and test scripts then, and assuming you've already gotten the
[localhost test](howtos/localhost-tests.md) described above working and are using the
same directory you setup before, (with the fake x.50 CA ``cadir`` etc.), you
should do the following (or similar) before trying to run the various
server-specific tests:

```bash
    cd $HOME/lt
    mkdir echkeydir
    cp echconfig,pem echkeydir/echconfig.pem.ech
```

That's a bit convoluted, sorry;-) I'm also not entirely sure it's done fully
consistently for all servers, but if not, I'll fix it as I get the stuff below
working.

### ECH for browsers is currently unreliable for ports other than 443

As of 2023-11-24, ECH works unreliably with chromium and doesn't work with
Firefox for ports other then 443.  It doesn't work at all for Firefox, and
only sometimes for chromium, probably based on complex in-browser DNS caching.
``curl`` and ``echcli.sh`` do however work reliably for other ports.

### Apache

- HOWTO: [apache2.md](howtos/apache2.md)
- config: [apachemin.conf](configs/apachemin.conf)
- test script: [testapache.sh](scripts/testapache.sh)
- to run apache in gdb: [apachegdb.sh](scripts/apachegdb.sh)

### Haproxy

Haproxy needs a real web server behind it, or two if we're
using split mode.

- HOWTO: [haproxy.md](howtos/haproxy.md)
- config: [haproxymin.conf](configs/haproxymin.conf)
- test script: [testhaproxy.sh](scripts/testhaproxy.sh)
- split mode config: [haproxy-split.conf](configs/haproxy-split.conf)
- split mode script: [testhaproxy-split.sh](scripts/testhaproxy-split.sh)

### Lighttpd

Lighttpd is what we use as a split mode backend. I forget why we
have multiple config files for that but we do.

- HOWTO: [lighttpd.md](howtos/lighttpd.md)
- config: [lighttpdmin.conf](configs/lighttpdmin.conf)
- test script: [testlighttpd.sh](scripts/testlighttpd.sh)
- split mode config: [lighttpd4haproxymin.conf](configs/lighttpd4haproxymin.conf)
- split mode config: [lighttpd4haproxy-split.conf](configs/lighttpd4haproxy-split.conf)
- split mode config: [lighttpd4nginx-split.conf](configs/lighttpd4nginx-split.conf)

### Nginx

- HOWTO: [nginx.md](howtos/nginx.md)
- config: [nginxmin-draft-13.conf](configs/nginxmin-draft-13.conf)
- test script: [testnginx-draft-13.sh](scripts/testnginx-draft-13.sh)
- split mode config: [nginx-split.conf](configs/nginx-split.conf)
- split mode script: [testnginx-split.sh](scripts/testnginx-split.sh)

## Client HOWTOs (sorta)

- the HOWTO for [curl](https://github.com/sftcd/curl/blob/ECH-experimental/docs/ECH.md)
  is no longer in this repo but is now part of a curl PR branch
- [wget.md](howtos/wget.md) describes a bit about how ECH-enabling wget is non-trivial

## Misc. files

- [cat.ext](misc/cat.ext) is a cat picture encoded as an ECHConfig extension suited
  for inclusion in an ECHConfigList - for the cat lovers out there, the
  original image is [cat.jpg](misc/cat.jpg), downsized to [scat.png](misc/scat.png)
- [extsfile](misc/extsfile) contains two ECHConfig extensions (suited for inclusion
  in an ECHConfigList), the first being of zero length, the second being a very
  small picture (I forget of what;-)

## Misc. scripts

A few bits'n'pieces that've been useful along the way, but mostly haven't been
used in some time:

- [nssdoech.sh](scripts/nssdoech.sh) tests ECH using an NSS client build (mostly helped
  with interop)
- [bssl-oss-test.sh](scripts/bssl-oss-test.sh) tests ECH using a boringssl client build
  (mostly helped with interop)
- [dnsname.sh](scripts/dnsname.sh) decodes a DNS wire format encoding of a DNS name
  (just a useful snippet, not so much for using in anger)
- [scanem.sh](scripts/scanem.sh) compares two OpenSSL source trees and reports on which
  files differ
- [runindented.sh](scripts/runindented.sh) is a bash function for indenting things (not
  currently used, but was, and may be again sometime)
