#!/bin/python3

# A script to emit test-case names and test artefacts corresponding to
# those, very much still a work-in-progress...

# Eventual plan is to be able to spit out server configs, bind
# nsupdate scripts (if we stick with bind) and client scripts
# for selenium and command line tools (curl/s_client)
# We also need some way to report on tests, that's a TODO: for now

import os, sys, argparse, gc
import json
import subprocess
from datetime import datetime, timezone

# command line arg handling
parser=argparse.ArgumentParser(description='prepare DEfO test artefacts')
parser.add_argument('-o','--output_dir', dest='outdir',
                    help='directory in which to put artefacts')
args=parser.parse_args()

# Singular settings... likely put these in other files and import
# 'em as they get bigger

# default output dir
outdir="dt"

# all DNS names mapping to tests will be one label below this name
base_domain='test.defo.ie'

# CAA record value to put (back) after deletion
caa_value="128 issue letsencrypt.org"

# TTL to use for all test RRs
ttl=10

# IP addresses
good_ipv4='185.88.140.5'
good_ipv6='2a00:c6c0:0:134:2::1'

# URL pathname for tests
pathname="echstat.php?format=json"

# ALPNs
good_alpn="http/1.1,h2"

# not sure what to put here but a quote is probably bad enough for now
bad_alpn="+"

# good key pairs
# generated with openssl ech -public_name public.test.defo.ie
good_pemfile='-----BEGIN PRIVATE KEY-----\n' + \
    'MC4CAQAwBQYDK2VuBCIEIOCiDSigzHBNxUlCkWsEXd8JFTqTi6CREnxNM2vMiMlk\n' + \
    '-----END PRIVATE KEY-----\n' + \
    '-----BEGIN ECHCONFIG-----\n' + \
    'AEb+DQBCqQAgACBlm7cfDx/gKuUAwRTe+Y9MExbIyuLpLcgTORIdi69uewAEAAEAAQATcHVibGljLnRlc3QuZGVmby5pZQAA\n' + \
    '-----END ECHCONFIG-----'

# generated with openssl ech -public_name otherpublic.test.defo.ie
other_pemfile='-----BEGIN PRIVATE KEY-----\n' + \
    'MC4CAQAwBQYDK2VuBCIEIHAxrYK93ytX/vnj912RlvRM3hMrAmG00hsU3jEgxUpy\n' + \
    '-----END PRIVATE KEY-----\n' + \
    '-----BEGIN ECHCONFIG-----\n' + \
    'AEv+DQBHdAAgACCCU49qdxKOUXJPs3wlsM06v/t42sMH5xQOL37MAd3HaAAEAAEAAQAYb3RoZXJwdWJsaWMudGVzdC5kZWZvLmllAAA=\n' + \
    '-----END ECHCONFIG-----'

# For all structures:
# - The 'id' field should be unique per array (doesn't need global uniqueness)
# - The 'description' field might end up in a TXT RR so try make it useful
# - For "bad" variants, best to have good data in the pemfile so we can configure
#   a web server for the relevant name(s)
good_kp={
    'id': 'good_kp',
    'description': 'A good ECH key pair with public.test.defo.ie',
    'public_name': 'public.test.defo.ie',
    'b64ecl': 'AEb+DQBCqQAgACBlm7cfDx/gKuUAwRTe+Y9MExbIyuLpLcgTORIdi69uewAEAAEAAQATcHVibGljLnRlc3QuZGVmby5pZQAA',
}
good_kp2={
    'id': 'good_kp2',
    'description': 'A good ECH key pair with otherpublic.test.defo.ie',
    'public_name': 'otherpublic.test.defo.ie',
    'b64ecl': 'AEv+DQBHdAAgACCCU49qdxKOUXJPs3wlsM06v/t42sMH5xQOL37MAd3HaAAEAAEAAQAYb3RoZXJwdWJsaWMudGVzdC5kZWZvLmllAAA=',
}
bad_kp1={
    'id': 'bad_kp1',
    'description': 'A bad ECH key pair with public.test.defo.ie, unsupported algs (0xCCCC) in ECHConfig',
    'public_name': 'public.test.defo.ie',
    'b64ecl': 'AEb+DQBCmczMACBrf4D75W04lOLJ4RVtJYz7lFamxDjiETWJA4KLCXeFUAAEAAEAAQATcHVibGljLnRlc3QuZGVmby5pZQAA',
}
bad_kp2={
    'id': 'bad_kp2',
    'description': 'zero-length ECHConfig within ECHConfigList',
    'public_name': 'n/a',
    'b64ecl': 'AAT+DQAA',
}

# Lists of "dimensions" of test names
# After each list we have some notes about other potential entries

# ECH-enabled server technology dimension array,
# the port is the non-443 port on which this technology is also listening
# epub is a placeholder for an ECH public key generated when this script
# is run (not quite ephemeral though, as we don't run this often)
server_tech=[
        { 'id': 'ng', 'description': 'nginx server', 'altport' : 15443, 'epub':'' },
        { 'id': 'ap', 'description': 'apache server', 'altport' : 15444, 'epub':'' },
        { 'id': 'ly', 'description': 'lighttpd server', 'altport' : 15445, 'epub':'' },
        { 'id': 'ss', 'description': 'OpenSSL s_server', 'altport' : 15447, 'epub':'' },
        { 'id': 'sshrr', 'description': 'OpenSSL s_server forcing HRR', 'altport' : 15448, 'epub':'' },
        { 'id': 'hp', 'description': 'haproxy server with lighttpd back-end', 'altport' : 15446, 'epub':''  },
        #{ 'id': 'hpsp', 'description': 'split-mode haproxy server', 'altport' : 15448, 'epub':'' },
        #{ 'id': 'ngsp', 'description': 'split-mode nginx server', 'altport' : 15449, 'epub':'' },
        #{ 'id': 'pf', 'description': 'postfix', 'altport' : 25, 'epub': '' },
        { 'id': 'nb', 'description': 'nobody at all listening here', 'altport' : 15450, 'epub':''  },
]
# could add NSS, boringssl and wolfssl server test tools maybe
# a filename for a temlpate we can fill via envsubst may be good

# encoding values are presentation syntax or arrays of those
# the first of these will get a shorter target name
targets_to_make=[
    {
      'id': 'min', 'expected': 'success',
      'description': 'minimal HTTPS RR',
      'encoding':
        '1 . ech=' + good_kp['b64ecl'],
    },
    {
      'id': 'v1', 'expected': 'success',
      'description': 'nominal, HTTPS RR',
      'encoding':
        '1 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp['b64ecl'] + ' ipv6hint=' + good_ipv6,
    },
    {
      'id': 'v2', 'expected': 'success',
      'description': 'nominal, HTTPS RR',
      'encoding':
        '1 . alpn="' + good_alpn + '" ipv4hint=' + good_ipv4 + ' ech=' + good_kp['b64ecl'] + ' ipv6hint=' + good_ipv6,
    },
    {
      'id': 'v3', 'expected': 'success',
      'description': 'two RRvals for nominal, minimal, HTTPS RR',
      'encoding':
        [
            '1 . ech=' + good_kp['b64ecl'],
            '2 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
        ],
    },
    {
      'id': 'v4', 'expected': 'error, but maybe arguable',
      'description': 'three RRvals, 1st bad, 2nd good, 3rd bad, HTTPS RR',
      'encoding':
        [
            '1 . ech=' + bad_kp1['b64ecl'],
            '2 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
            '3 . ech=' + bad_kp1['b64ecl'],
        ],
    },
    {
      'id': 'bk1', 'expected': 'error',
      'description': 'ECHConfigList with bad alg type (0xcccc) for ech kem',
      'encoding': '1 . ech=' + bad_kp1['b64ecl'],
    },
    {
     'id': 'bk2', 'expected': 'error',
     'description': 'zero-length ECHConfig within ECHConfigList',
     'encoding': '1 . ech=' + bad_kp2['b64ecl'],
    },
    {
      'id': 'bv', 'expected': 'error',
      'description': 'ECHConfigList with bad ECH version (0xcccc)',
      'encoding': '1 . ech=AEbMzABCmQAgACBrf4D75W04lOLJ4RVtJYz7lFamxDjiETWJA4KLCXeFUAAEAAEAAQATcHVibGljLnRlc3QuZGVmby5pZQAA',
    },
    {
      'id': 'badalpn', 'expected': 'client-dependent',
      'description': 'nominal, HTTPS RR, bad alpn',
      'encoding':
        '1 . alpn="' + bad_alpn + '" ech=' + good_kp['b64ecl'],
    },
]
# there are many, many ways to extend this, e.g. bad lengths, though note
# that not all of those will be accepted by an authoritative DNS server
# (or recursive, or stub, maybe)

# ECH-enabled client technologies, generally we assume most recent
# version, if some version becomes important, then add a name here
# for that
client_tech=[
    { 'id': 'ff', 'description': 'firefox ESR' },
    { 'id': 'ch', 'description': 'chromium' },
    { 'id': 'sa', 'description': 'safari' },
    { 'id': 'cu', 'description': 'curl' },
    { 'id': 'sc', 'description': 'OpenSSL s_client' },
    { 'id': 'pf', 'description': 'postfix' },
]
# Arguably, the boring ssl test client (bssl) and the NSS eqivalent
# (tstclnt), should be here too, maybe rusttls and woflssl as well

# we accumulate a list of URLs based on the targets
targets_to_test=[]
nginx_targets=[]

# the set of good PEM files, all servers can load all of these
# note that some servers need the ".ech" file extension for loading
pemfiles_to_use = [ { 'id': 'good.pem.ech', 'content': good_pemfile },
                    { 'id': 'other.pem.ech', 'content': other_pemfile }]

# haproxy.cfg preamble
haproxy_cfg_preamble='''
global
       log /dev/log    local0
       log /dev/log    local1 notice
       chroot /var/lib/haproxy
       stats socket /run/haproxy/admin.sock mode 660 level admin
       stats timeout 30s
       user haproxy
       group haproxy
       daemon
       # Default SSL material locations
       ca-base /etc/ssl/certs
       crt-base /etc/ssl/private
       # See: https://ssl-config.mozilla.org/#server=haproxy&server-version=2.0.3&config=intermediate
       ssl-default-bind-ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384
       ssl-default-bind-ciphersuites TLS_AES_128_GCM_SHA256:TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256
       ssl-default-bind-options ssl-min-ver TLSv1.2 no-tls-tickets
defaults
       log     global
       mode    http
       option  httplog
       option  dontlognull
       timeout connect 5000
       timeout client  50000
       timeout server  50000
       errorfile 400 /etc/haproxy/errors/400.http
       errorfile 403 /etc/haproxy/errors/403.http
       errorfile 408 /etc/haproxy/errors/408.http
       errorfile 500 /etc/haproxy/errors/500.http
       errorfile 502 /etc/haproxy/errors/502.http
       errorfile 503 /etc/haproxy/errors/503.http
       errorfile 504 /etc/haproxy/errors/504.http
frontend defotest
       mode tcp
       option tcplog
       bind :443
       use_backend defotestservers
backend defotestservers
       mode tcp
       tcp-request inspect-delay 5s
       tcp-request content accept if { req_ssl_hello_type 1 }
       # hoba is not part of these tests, just co-located for a different test
       use-server ng if { req.ssl_sni -i hoba.ie }
       use-server ng if { req.ssl_sni -i hidden.hoba.ie }
'''

# nginx sites-enabled config template
nginx_template='''
server {
    root /var/www/html;
    index index.html index.htm index.nginx-debian.html index.php;
    server_name SERVER_NAMES;
    location / {
        try_files $uri $uri/ =404;
    }
    location ~ \\.php$ {
        fastcgi_pass 127.0.0.9:9000;
    }
    listen [::]:ALTPORT ssl; # managed by Certbot
    listen ALTPORT ssl; # managed by Certbot
    ssl_certificate /etc/acme.sh/test.defo.ie//test.defo.ie_ecc/fullchain.pem;
    ssl_certificate_key /etc/acme.sh/test.defo.ie//test.defo.ie_ecc/test.defo.ie.key;
    include /etc/letsencrypt/live/hoba.ie/options-ssl-nginx.conf;
}
'''

documentation_preamble='''
## Rationale

Having written this test-case generation script and left it alone for a week or
two, I realised I'd forgotten details of the setups and had to reverse-engineer
those from the code. That probably indicates that some documentation is needed.
This is that documentation, also produced as an output from running the test
generator.

## Setup

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

## Running the generator

This only needs to be done when new tests are added.

Usage:

        $ ./test-cases-gen.py [-o <dir>]

The optional <dir> specifies a directory into which output files will be
written. The default for <dir> is "dt".

The files output to that directory are:

    - README.md, this file
    - resetdns.commands, nsupdate commands to clear and reset DNS RRs
      for test.defo.ie, including some not involved in these tests
      (e.g. dodgy.test.defo.ie)
    - addRRs.commands, nsupdate commands to make test-specific DNS RRs
    - echkeydir, directory containing ECH PEM key files for test servers
    - haproxy.cfg, file to configure the frontned haproxy listener
    - ng.test.defo.ie.conf, nginx config for the main test server
      containing test-specific server_name values
    - iframe_tests.html, HTML page that runs all our browsers tests in 
      an iframe for each test (and describes tests)
    - urls_to_test, the set of URLs used in iframe tests

# Test-Specific Names

The following test-specific DNS names are used, each corresponding to
a server configured on our nginx install:
'''

documentation_part2='''
For all nominal tests, the ECH public_name used is ng-pub.test.defo.ie

# Other servers

In addition to the test-specific names that map to our nginx install, we have
also installed other servers as listed below, in case we need to investigate
server-specific issues.

The ECH public_name for ap.test.defo.ie will be e.g. ap-pub.test.defo.ie and
similarly for other technologies.

Those are as follows:
'''

documentation_part3='''
# Adding a new test

The `targets_to_make` array contains the list of tests and their parameters.
The fields in this array are:

- id: a short name to differentiate the test
- expected: the output expected from the test, one of: success, error, arguable
- description: string decscribing the test, intended for human consumption but
  for those familiar with ECH
- encoding: this is string or array of strings representing the HTTPS RR(s) in
  presentation form, but typically, in error cases, using other python
  variables e.g. for a badly encoded ECHconfigList

The nominal case is as shown below;

    {
      'id': 'min', 'expected': 'success',
      'description': 'minimal HTTPS RR',
      'encoding':
        '1 . ech=' + good_kp['b64ecl'],
    },

A case with multiple HTTPS RRs is: 

    {
      'id': 'v4', 'expected': 'error, but maybe arguable',
      'description': 'three RRvals, 1st bad, 2nd good, 3rd bad, HTTPS RR',
      'encoding':
        [
            '1 . ech=' + bad_kp1['b64ecl'],
            '2 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
            '3 . ech=' + bad_kp1['b64ecl'],
        ],
    },

For the test above, as the server is on nginx, the name `v4-ng.test.defo.ie`
will be used and DNS records will be created for that, for A, AAAA and HTTPS.
The additional name will be added to the nginx and haproxy configuations and a
stanza will be added to the `iframe-tests.html` page.

One should then run the test generator.

If new ECH keys are required for new namess, then those will be generated. If
some ECH key pair exists for a test name, that won't be overwritten.

# Installing tests

The following steps may need to be taken after re-running the test generator:

- Extract the lines for the newly-added name from `addRRs.commands` and feed
  those to `nsupdate` on the relevant authoritative server
- copy files from `echkeydir` into `/etc/echkeydir` on test.defo.ie
- copy `haproxy.cfg` to `/etc/haproxy/` on `test.defo.ie`
- copy `ng.test.defo.ie.conf` to `/etc/nginx/sites-enabled` on `test.defo.ie`
- copy `iframe_tests.html` to `/var/www/html` on `test.defo.ie`
- restart services, e.g.:

                $ sudo service nginx restart
                $ sudo service haproxy restart

If you make major changes or mess up you can zap everything and start from
using the commands in `resetdns.commands` following by doing all the above.
'''

def makereadme():
    print("# DEfO generated-tests Documentation", file=outf)
    print(documentation_preamble, file=outf)
    for targ in targets_to_make:
        tline="- " + targ['id'] + "-" + server_tech[0]['id'] + "." + base_domain + ": " + targ['description']
        print(tline, file=outf)
    print(documentation_part2, file=outf)
    for tech in server_tech:
        tline="- " + tech['id'] + "." + base_domain + ": " + tech['description']
        print(tline, file=outf)
    print(documentation_part3, file=outf)

    print("## Run identification\n", file=outf)
    print("Run Date: " + str(datetime.now(timezone.utc)) + " UTC", file=outf)
    print("Git info for " + sys.argv[0], file=outf)
    gitlines = subprocess.check_output(["git", "log", str(-1), sys.argv[0]])
    for line in gitlines.decode("utf-8").split('\n'):
        print("\t" + line, file=outf)

# a set of nsupdate commands to throw away everything and
# get set for adding new tests - but we need to make sure
# that there's A/AAAA/CAA RRs 
def resetdnscommands():
    print("update delete " + base_domain, file=outf)
    print("update add " + base_domain + " " + str(ttl) + " A " + good_ipv4, file=outf)
    print("update add " + base_domain + " " + str(ttl) + " AAAA " + good_ipv6, file=outf)
    print("update add " + base_domain + " " + str(ttl) + " CAA " + caa_value, file=outf)
    # make address RRs for the public names
    print("update add " + good_kp['public_name'] + " " + str(ttl) + " A " + good_ipv4, file=outf)
    print("update add " + good_kp['public_name'] + " " + str(ttl) + " AAAA " + good_ipv6, file=outf)
    print("update add " + good_kp2['public_name'] + " " + str(ttl) + " A " + good_ipv4, file=outf)
    print("update add " + good_kp2['public_name'] + " " + str(ttl) + " AAAA " + good_ipv6, file=outf)
    # add dodgy.test.defo.ie just for use as an example
    dodgy='dogdy.test.def.ie'
    print("update add " + dodgy + " " + str(ttl) + " A " + good_ipv4, file=outf)
    print("update add " + dodgy + " " + str(ttl) + " AAAA " + good_ipv6, file=outf)
    print("update add " + dodgy + " " + str(ttl) + " HTTPS", '1 . ech=eHl6dwo=' , file=outf)
    print("update add " + dodgy + " " + str(ttl) + " HTTPS", '1 . ech=Cg==' , file=outf)
    print("update add " + dodgy + " " + str(ttl) + " HTTPS", '1 . ech=YWJjCg==' , file=outf)
    print("update add " + dodgy + " " + str(ttl) + " HTTPS", '1 . ech' , file=outf)
    print("update add " + dodgy + " " + str(ttl) + " HTTPS", '10000 . ech=dG90YWwtY3JhcAo=' , file=outf)

def up_instrs(name, ttl, a, aaaa, desc, https_rr):
    # print commands to delete then update the various records
    didsomething = 0
    if a is not None:
        print("update delete " + name + " A", file=outf)
        print("update add " + name + " " + str(ttl) + " A", a , file=outf)
        didsomething = 1
    if aaaa is not None:
        print("update delete " + name + " AAAA", file=outf)
        print("update add " + name + " " + str(ttl) + " AAAA " + aaaa, file=outf)
        didsomething = 1
    if desc is not None:
        print("update delete " + name + " TXT", file=outf)
        print("update add " + name + " " + str(ttl) + " TXT", desc , file=outf)
        didsomething = 1
    if (https_rr is not None):
        print("update delete " + name + " HTTPS", file=outf)
        didsomething = 1
        if isinstance(https_rr, str):
            print("update add " + name + " " + str(ttl) + " HTTPS", https_rr , file=outf)
        else:
            for enc in https_rr:
                print("update add " + name + " " + str(ttl) + " HTTPS", enc , file=outf)
    if didsomething == 1:
        print("send", file=outf)

# produce a set of nsupdate commands for a basic target
# such as ng.test.defo.ie or ap.test.defo.ie
def dobasensupdate(tech):
    description='"' + tech['description'] + '"'
    target=tech['id'] + "." + base_domain
    https_rr="1 . ech=" + tech['epub']
    up_instrs(target, ttl, good_ipv4, good_ipv6, description, https_rr)
    targets_to_test.append({'tech': tech, 'target':target,
                            'description': description, 'https_rr': https_rr,
                            'expected': "success"})
    # handle altport access
    alttarg="_" + str(tech['altport']) + "._https." + target
    altenc = "1 " + target + " ech=" + tech['epub']
    up_instrs(alttarg, ttl, None, None, description, altenc)
    alttarg=tech['id'] + "-pub." + base_domain
    up_instrs(alttarg, ttl, good_ipv4, good_ipv6, description, None)

# produce a set of nsupdate commands for a target that's uses a 
# specific HTTPS test configuration (often a broken one)
def donsupdate(tech, target, hp):
    description='"' + tech['description'] + '/' + hp['description'] + '"'
    https_rr=hp['encoding']
    up_instrs(target, ttl, good_ipv4, good_ipv6, description, https_rr)
    targets_to_test.append({'tech': tech, 'target':target,
                            'description': description, 'https_rr': https_rr,
                            'expected': hp['expected']})
    # handle altport access
    alttarg="_" + str(tech['altport']) + "._https." + target
    altenc = hp['encoding']
    if (isinstance(altenc, str)):
        altenc.replace(" . "," " + target + " ")
    else:
        altenc=[sub.replace(" . "," " + target + " ") for sub in altenc]
    up_instrs(alttarg, ttl, None, None, description, altenc)

# produce a set of nsupdate commands for all targets that use a 
# specific HTTPS test configuration (often a broken one)
def donsupdates(tech):
    for targ in targets_to_make:
        target=targ['id'] + "-" + tech['id'] + "." + base_domain
        nginx_targets.append(target)
        donsupdate(tech, target, targ)

# print lines that haproxy needs to forward port 443 traffic to the
# correct client-facing server - note: haproxy in this mode is only
# a TCP de-muxer and is doing no ECH nor TLS processing
def haproxy_fe_config():
    print(haproxy_cfg_preamble, file=outf)
    # de-mux rules for our main server
    print("       use-server " + server_tech[0]['id'] + " if { req.ssl_sni -i public.test.defo.ie  }", file=outf)
    print("       use-server " + server_tech[0]['id'] + " if { req.ssl_sni -i otherpublic.test.defo.ie  }", file=outf)
    # de-mux rules for other servers
    for s in server_tech:
        print("       use-server " + s['id'] + " if { req.ssl_sni -i " + s['id'] + "-pub." + base_domain + " }", file=outf)
        print("       use-server " + s['id'] + " if { req.ssl_sni -i " + s['id'] + base_domain + " }", file=outf)
        print("       server " + s['id'] + " 127.0.0.1:" + str(s['altport']) + " check", file=outf)
    # default on last line?
    print("       server default 127.0.0.1:" + str(server_tech[0]['altport']), file=outf)

# print out a sites-enabled config file for nginx
def nginx_site(tech):
    tmp=nginx_template.replace('ALTPORT',str(tech['altport']))
    snames = ""
    for t in nginx_targets:
        snames += t + "\n                " # spaces make a nicer sites-enabled file
    tmp=tmp.replace('SERVER_NAMES',snames)
    print(tmp, file=outf)

if __name__ == "__main__":
    if args.outdir != None:
        outdir=args.outdir
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    # print("Reset DNS commands:")
    outf=open(outdir+'/resetdns.commands','w')
    resetdnscommands()

    # print("ECH PEM files:")
    if not os.path.exists(outdir+"/echkeydir"):
        os.makedirs(outdir+"/echkeydir")
    # built-in keys for server_tech[0]
    s0dir= outdir+"/echkeydir/" + server_tech[0]['id']
    if not os.path.exists(s0dir):
        os.makedirs(s0dir)
    for p in pemfiles_to_use:
        outf=open(s0dir + "/" + p['id'],'w')
        print(p['content'], file=outf)
    # make keys per client-facing server too 
    for t in server_tech:
        s0dir= outdir+"/echkeydir/" + t['id']
        if not os.path.exists(s0dir):
            os.makedirs(s0dir)
        pemname=s0dir + "/" + t['id'] + "-pub.pem.ech"
        # don't replace if not needed, avoiding unneeded DNS updates
        if not os.path.exists(pemname):
            subprocess.run(["bash", "-c", "./makeech.sh -public_name " + t['id'] + "-pub." + base_domain + \
                        " -pemout " + pemname + " >/dev/null 2>&1"])
        t['epub']=os.popen("tail -2 " + pemname + " | head -1 ").read()
        #print(t)

    # print("DNS commands:")
    # do all the oddball tests with 1st named server_tech
    outf=open(outdir+'/addRRs.commands','w')
    donsupdates(server_tech[0])
    # only do nominal cases for other techs
    for tech in server_tech:
        target=tech['id'] + "." + base_domain
        dobasensupdate(tech)

    # print("URLs to test:")
    outf=open(outdir+'/urls_to_test','w')
    for t in targets_to_test:
        print("https://" + t['target'] + "/" + pathname, file=outf)
        print("https://" + t['target'] + ":" + str(t['tech']['altport']) + "/" + pathname, file=outf)

    # print("Web page running tests in iframe
    outf=open(outdir+'/iframe_tests.html','w')
    print("<html>", file=outf)
    print("<h1>test.defo.ie iframe based tests</h1>", file=outf)
    print("<ol>", file=outf)
    ind = 0
    for t in targets_to_test:
        print("<li>", file=outf)
        print("<p>Test: " + t['description'] + "</p>", file=outf)
        print("<p>Expected result: " + t['expected'] + "</p>", file=outf)
        if (isinstance(t['https_rr'],str)):
            print("<p>HTTPS RR: <pre>" + t['https_rr'] + "</pre></p>", file=outf)
        else:
            print("<p>HTTPS RRs: <pre>", file=outf)
            for r in t['https_rr']:
                print(r, file=outf)
            print("</pre></p>", file=outf)
        url="https://" + t['target'] + "/" + pathname
        print('<p><a href=\"' + url + '\">' + url + '</a></p>', file=outf)
        print('<iframe src=\"' + url + '\" width=\"80%\" height=\"60\" title=\"testframe' + str(ind) + '\"></iframe>', file=outf)
        url="https://" + t['target'] + ":" + str(t['tech']['altport']) + "/" + pathname
        print('<p><a href=\"' + url + '\">' + url + '</a></p>', file=outf)
        print('<iframe src=\"' + url + '\" width=\"80%\" height=\"60\" title=\"testframe-alt-' + str(ind) + '\"></iframe>', file=outf)
        print("</li>", file=outf)
        ind+=1
    print("</ol>", file=outf)
    print("</html>", file=outf)


    # print("haproxy config lines:")
    outf=open(outdir+'/haproxy.cfg','w')
    haproxy_fe_config()

    # nginx site enabled
    outf=open(outdir+'/ng.test.defo.ie.conf','w')
    nginx_site(server_tech[0])

    # print documentation
    outf=open(outdir+'/README.md','w')
    makereadme()

    # instructions...
    print("Documentation is in " + outdir + "/README.me")
    print("On zone factory:")
    print("   To reset test.defo.ie DNS from sratch:")
    print("        $ sudo nsupdate -l <" + outdir + "/resetdns.commands")
    print("   To add DNS RRs for tests:")
    print("        $ sudo nsupdate -l <" + outdir + "/addRRs.commands")
    print("On the " + base_domain + " VM:")
    print("   To replace old ECH PEM files:")
    print("        $ sudo rm -rf /etc/echkeydir")
    print("        $ sudo cp -r " + outdir + "/echkeydir /etc")
    print("   To replace haproxy TCP mux'er config:")
    print("        $ sudo cp " + outdir + "/haproxy.cfg /etc/haproxy")
    print("        $ sudo service haproxy restart")
    print("   To replace the nginx site config:")
    print("        $ sudo cp " + outdir + "/ng.test.defo.ie.conf /etc/nginx/sites-enabled/")
    print("   To update the iframe based test web page:")
    print("        $ scp " + outdir + "/iframe_tests.html test.defo.ie:")
    print("        ...then on the test.defo.ie VM...")
    print("        $ sudo mv ~/iframe_tests.html /var/www/html")

