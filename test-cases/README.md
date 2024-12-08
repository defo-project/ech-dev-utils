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
name. (Turned out it did matter a bit, see TODO section below.)

Each test uses a specific DNS name, e.g. `min-ng.test.defo.ie`. Most of those
have a first label of the form "<test>-ng" where "ng" indicates TLS connections
for that name are routed to our nginx installation.

The other files here are:

- [test_cases_gen.py](./test_cases_gen.py) is a script we use
  to generate test cases as part of the (upcoming) refresh of the defo.ie web
  site.
- [test_cases_settings.py](./test_cases_settings.py) has general settings for
  the above and isn't expected to be modified (much)
- [more_targets_to_make.py](./more_targets_to_make.py) has additional test
  cases and is expected to grow over time, as tests are added
- [makeech.sh](scripts/makeech.sh) is a wrapper for "openssl ech" that works
  based on whichever of the installed openssl or a local build has ECH support.

## TODOs

We want to add some more tests to cover these cases:

- Where an A and AAAA are published but IPv6 isn't working and in the `2thenp`
  and `pthen2` test cases, we unexpected got divergent behaviour in browsers.
Needs further investigation as we only looked at the iframe behaviour so far.
(We can investigate that via changing the haproxy config back to where it
only listens on an IPv4 port.)

- The `v4`, `mixedmode` and `curves1` tests are arguably DNS fails in 
browsers.

- The `mixedmode` test for curl seems odd - curl verbose logging says
ECH is not configured, which seems wrong. Not sure if code's wrong or
just bad log text.

- Consider whether returning zero to command line is correct when
curl is opportunistically asked for ECH.

- Ports off 443 where there is no HTTPS RR for the port 443 case used differ,
  possibly implying some browser bugginess. We saw that behaviour on
`draft-13.esni.defo.ie` non-443 port cases so should include a similar test
here.

