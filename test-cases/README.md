# Generating ECH test cases

We have some scripting to generate test cases.

Test servers are run on `test.defo.ie` which runs debian testing ("trixie").
That has an haproxy listener on port 443 that sits in front of other web
servers (nginx, apache etc.) and routes connection (in "tcp" mode) to those
based on the (outer) SNI. That front-end haproxy instance does not crypto - no
TLS and no ECH - it only routes connections so that we can use stadard installs
for the other packages, based on our DEfO CI setup. The default server for
haproxy (if no SNI matches) is our nginx installation. The default server for
our nginx server is actually `hidden.hoba.ie` which is not really related to
this test setup, but should cause an error:-)

All names used are of the form: `<name>.test.defo.ie` and we have a wildcard
certificate for `*.test.defo.ie` acquired via acme.sh that is used for all TLS
servers.

The `test.defo.ie` VM is accessible both via IPv4 and IPv6, that ought not make
any difference for our tests, but we publish both A and AAAA RRs for each test
name.

Each test uses a specific DNS name, e.g. `min-ng.test.defo.ie`. Most of those
have a first label of the form "<test>-ng" where "ng" indicates TLS connections
for that name are routed to our nginx installation.

The other files here are:

- [test_cases_gen.py](./test_cases_gen.py) is a work-in-progress script we use
  to generate test cases as part of the (upcoming) refresh of the defo.ie web site.
- [test_cases_settings.py](./test_cases_settings.py) has general settings for 
  the above and isn't expected to be modified (much)
- [more_test_cases.py](./more_test_cases.py) has additional test cases and is
  expected to grow over time, as tests are added
- [makeech.sh](scripts/makeech.sh) is a wrapper for "openssl ech" that works based
  on whichever of the installed openssl or a local build has ECH support. (This is
