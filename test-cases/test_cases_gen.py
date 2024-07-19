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

from test_cases_settings import *

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
        # we won't deploy all these yet
        #{ 'id': 'hp', 'description': 'haproxy server with lighttpd back-end', 'altport' : 15446, 'epub':''  },
        #{ 'id': 'hpsp', 'description': 'split-mode haproxy server', 'altport' : 15448, 'epub':'' },
        #{ 'id': 'ngsp', 'description': 'split-mode nginx server', 'altport' : 15449, 'epub':'' },
        #{ 'id': 'pf', 'description': 'postfix', 'altport' : 25, 'epub': '' },
        #{ 'id': 'nb', 'description': 'nobody at all listening here', 'altport' : 15450, 'epub':''  },
]
# could add NSS, boringssl and wolfssl server test tools maybe
# a filename for a temlpate we can fill via envsubst may be good

# encoding values are presentation syntax or arrays of those
# the first of these will get a shorter target name
targets_to_make=[
    {
      'id': 'min', 'expected': 'success', 'curl_expected': 0,
      'description': 'minimal HTTPS RR',
      'encoding':
        '1 . ech=' + good_kp['b64ecl'],
    },
    {
      'id': 'v1', 'expected': 'success', 'curl_expected': 0,
      'description': 'nominal, HTTPS RR',
      'encoding':
        '1 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp['b64ecl'] + ' ipv6hint=' + good_ipv6,
    },
    {
      'id': 'v2', 'expected': 'success', 'curl_expected': 0,
      'description': 'nominal, HTTPS RR',
      'encoding':
        '1 . alpn="' + good_alpn + '" ipv4hint=' + good_ipv4 + ' ech=' + good_kp['b64ecl'] + ' ipv6hint=' + good_ipv6,
    },
    {
      'id': 'v3', 'expected': 'success', 'curl_expected': 0,
      'description': 'two RRvals for nominal, minimal, HTTPS RR',
      'encoding':
        [
            '1 . ech=' + good_kp['b64ecl'],
            '2 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
        ],
    },
    {
      'id': 'v4', 'expected': 'error, but maybe arguable', 'curl_expected': 35,
      'description': 'three RRvals, 1st bad, 2nd good, 3rd bad, HTTPS RR',
      'encoding':
        [
            '1 . ech=' + bad_kp1['b64ecl'],
            '2 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
            '3 . ech=' + bad_kp1['b64ecl'],
        ],
    },
    {
      'id': 'bk1', 'expected': 'error', 'curl_expected': 35,
      'description': 'ECHConfigList with bad alg type (0xcccc) for ech kem',
      'encoding': '1 . ech=' + bad_kp1['b64ecl'],
    },
    {
     'id': 'bk2', 'expected': 'error', 'curl_expected': 35,
     'description': 'zero-length ECHConfig within ECHConfigList',
     'encoding': '1 . ech=' + bad_kp2['b64ecl'],
    },
    {
      'id': 'bv', 'expected': 'error', 'curl_expected': 35,
      'description': 'ECHConfigList with bad ECH version (0xcccc)',
      'encoding': '1 . ech=AEbMzABCmQAgACBrf4D75W04lOLJ4RVtJYz7lFamxDjiETWJA4KLCXeFUAAEAAEAAQATcHVibGljLnRlc3QuZGVmby5pZQAA',
    },
    {
      'id': 'badalpn', 'expected': 'client-dependent', 'curl_expected': 0,
      'description': 'nominal, HTTPS RR, bad alpn',
      'encoding':
        '1 . alpn="' + bad_alpn + '" ech=' + good_kp['b64ecl'],
    },
    {
      'id': 'noaddr', 'expected': 'error', 'curl_expected': 6,
      'description': 'HTTPS RR, with hints but no A/AAAA',
      'encoding':
        '1 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp['b64ecl'] + ' ipv6hint=' + good_ipv6,
      'noaddr': 1,
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
    listen [::]:ALTPORT default_server ssl;
    listen ALTPORT default_server ssl;
    ssl_certificate /etc/acme.sh/test.defo.ie/test.defo.ie_ecc/fullchain.cer;
    ssl_certificate_key /etc/acme.sh/test.defo.ie/test.defo.ie_ecc/test.defo.ie.key;
    include /etc/letsencrypt/live/hoba.ie/options-ssl-nginx.conf;
}
'''

apache_config='''
<VirtualHost *:15444>
    ServerAdmin defo@defo.ie
    DocumentRoot /var/www/html
    ServerName ap.test.defo.ie
    ErrorLog ${APACHE_LOG_DIR}/error.log
    CustomLog ${APACHE_LOG_DIR}/access.log combined
    SSLEngine on
    SSLProtocol TLSv1.3
    SSLECHKeyDir /etc/echkeydir/ap
    <FilesMatch "\\.php$">
        SetHandler "proxy:fcgi://127.0.0.9:9000"
    </FilesMatch>
    Options +ExecCGI
    <FilesMatch "\\.(?:cgi|shtml|phtml|php)$">
        SSLOptions +StdEnvVars
    </FilesMatch>
    SSLCertificateFile  /etc/acme.sh/test.defo.ie/test.defo.ie_ecc/fullchain.cer
    SSLCertificateKeyFile /etc/acme.sh/test.defo.ie/test.defo.ie_ecc/test.defo.ie.key
</VirtualHost>

<VirtualHost *:15444>
    ServerAdmin defo@defo.ie
    DocumentRoot /var/www/html
    ServerName ap-pub.test.defo.ie
    ErrorLog ${APACHE_LOG_DIR}/error.log
    CustomLog ${APACHE_LOG_DIR}/access.log combined
    SSLEngine on
    SSLProtocol TLSv1.3
    SSLECHKeyDir /etc/echkeydir/ap
    <FilesMatch "\\.php$">
        SetHandler "proxy:fcgi://127.0.0.9:9000"
    </FilesMatch>
    Options +ExecCGI
    <FilesMatch "\\.(?:cgi|shtml|phtml|php)$">
        SSLOptions +StdEnvVars
    </FilesMatch>
    SSLCertificateFile  /etc/acme.sh/test.defo.ie/test.defo.ie_ecc/fullchain.cer
    SSLCertificateKeyFile /etc/acme.sh/test.defo.ie/test.defo.ie_ecc/test.defo.ie.key
</VirtualHost>
'''

lighttpd_config='''
# you probably also need to comment out the server.port line in /etc/lighttpd/lighttpd.conf
server.port         = 15445
server.modules += ( "mod_openssl" )
ssl.engine          = "enable"
ssl.pemfile         = "/etc/acme.sh/test.defo.ie//test.defo.ie_ecc/test.defo.ie.both.pem"
ssl.ech-opts = (
  "keydir" => "/etc/echkeydir/ly",

  "refresh" => 3600, # reload hourly
  # "refresh" => 60,    # reload every minute (testing)
  #"refresh" => 0,            # never reload
  # (minimum check interval is actually 64 seconds (2^6))

  # trial decryption allows clients to hide better by not sending real digests
  # that is turned on by default (as we're likely a small server so no harm and
  # better privacy), but you can disable it...
  #"trial-decrypt" => "disable",
)

$HTTP["host"] == "ly.test.defo.ie" {
    server.name                 = "ly.test.defo.ie"
}
$HTTP["host"] == "ly-pub.test.defo.ie" {
    ssl.non-ech-host            = "ly-pub.test.defo.ie"
}
'''

s_server_bash='''
#!/bin/bash

# set -x

cd /var/www/html/
openssl s_server -WWW -ign_eof -tls1_3 -port PORT \\
    -CApath /etc/ssl/certs \\
    -cert_chain /etc/acme.sh/test.defo.ie/test.defo.ie_ecc/fullchain.cer \\
    -key /etc/acme.sh/test.defo.ie/test.defo.ie_ecc/test.defo.ie.key \\
    -cert /etc/acme.sh/test.defo.ie/test.defo.ie_ecc/test.defo.ie.cer \\
    -key2 /etc/acme.sh/test.defo.ie/test.defo.ie_ecc/test.defo.ie.key \\
    -cert2 /etc/acme.sh/test.defo.ie/test.defo.ie_ecc/test.defo.ie.cer \\
    -ech_dir /etc/echkeydir/NAME \\
    -servername NAME.test.defo.ie -alpn http/1.1 HRRTRIGGER
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
    - curl-tests.sh, a script to run curl tests against our nginx-served
      targets
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
a (virtual) server configured on our nginx install:
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
      'id': 'min', 'expected': 'success', 'curl_expected': 0,
      'description': 'minimal HTTPS RR',
      'encoding':
        '1 . ech=' + good_kp['b64ecl'],
    },

A case with multiple HTTPS RRs is:

    {
      'id': 'v4', 'expected': 'error, but maybe arguable', 'curl_expected': 6,
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

When we run curl against the resulting test URL, we expect a fail and for the
command line too to return the value 6.

One should then run the test generator.

If new ECH keys are required for new names, then those will be generated. If
some ECH key pair exists for a test name, that won't be overwritten.

# Installing tests

The following steps may need to be taken after re-running the test generator:

- Make the curl tests executable via: `$ chmod u+x curl-tests`
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
    # instructions...
    print("# Cheat-sheet\n", file=outf)
    print("On zone factory:", file=outf)
    print("   To make curl-tests.sh executable:", file=outf)
    print("        $ chmod u+x " + outdir + "/curl-tests.sh", file=outf)
    print("   To reset test.defo.ie DNS from sratch:", file=outf)
    print("        $ sudo nsupdate -l <" + outdir + "/resetdns.commands", file=outf)
    print("   To add DNS RRs for tests:", file=outf)
    print("        $ sudo nsupdate -l <" + outdir + "/addRRs.commands", file=outf)
    print("On the " + base_domain + " VM:", file=outf)
    print("   To replace old ECH PEM files:", file=outf)
    print("        $ sudo rm -rf /etc/echkeydir", file=outf)
    print("        $ sudo cp -r " + outdir + "/echkeydir /etc", file=outf)
    print("   To replace haproxy TCP config:", file=outf)
    print("        $ sudo cp " + outdir + "/haproxy.cfg /etc/haproxy", file=outf)
    print("        $ sudo service haproxy restart", file=outf)
    print("   To replace the nginx site config:", file=outf)
    print("        $ sudo cp " + outdir + "/ng.test.defo.ie.conf /etc/nginx/sites-enabled/", file=outf)
    print("   To update the iframe based test web page:", file=outf)
    print("        $ scp " + outdir + "/iframe_tests.html test.defo.ie:", file=outf)
    print("        ...then on the test.defo.ie VM...", file=outf)
    print("        $ sudo mv ~/iframe_tests.html /var/www/html", file=outf)
    print("   To update the apache or lighttpd configs:", file=outf)
    print("        $ sudo cp " + outdir + "/ap.test.defo.ie /etc/apache2/sites-enabled", file=outf)
    print("        $ sudo cp " + outdir + "/ly.test.defo.ie /etc/lighttpd/conf-enabled", file=outf)
    print("   To run the openssl s_server scripts:", file=outf)
    print("        $ sudo mkdir -p /var/log/s_server", file=outf)
    print("        $ chmod u+x ./" + outdir + "/s_server_15447.sh", file=outf)
    print("        $ chmod u+x ./" + outdir + "/s_server_15448.sh", file=outf)
    print("        $ sudo sh -c './" + outdir + "/s_server_15447.sh >/var/log/s_server/15447.log 2>&1' &", file=outf)
    print("        $ sudo sh -c './" + outdir + "/s_server_15448.sh >/var/log/s_server/15448.log 2>&1' &", file=outf)
    print("", file=outf)
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
    # print commands to delete then, if needed, add the various records
    didsomething = 0
    print("update delete " + name + " A", file=outf)
    if a is not None:
        print("update add " + name + " " + str(ttl) + " A", a , file=outf)
        didsomething = 1
    print("update delete " + name + " AAAA", file=outf)
    if aaaa is not None:
        print("update add " + name + " " + str(ttl) + " AAAA " + aaaa, file=outf)
        didsomething = 1
    print("update delete " + name + " TXT", file=outf)
    if desc is not None:
        print("update add " + name + " " + str(ttl) + " TXT", desc , file=outf)
        didsomething = 1
    print("update delete " + name + " HTTPS", file=outf)
    if (https_rr is not None):
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
    the_ipv4=good_ipv4
    the_ipv6=good_ipv6
    if 'noaddr' in hp and hp['noaddr']==1:
        the_ipv4=None
        the_ipv6=None
    up_instrs(target, ttl, the_ipv4, the_ipv6, description, https_rr)
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
    print("       use-server " + server_tech[0]['id'] + " if { req.ssl_sni -i test.defo.ie  }", file=outf)
    print("       use-server " + server_tech[0]['id'] + " if { req.ssl_sni -i public.test.defo.ie  }", file=outf)
    print("       use-server " + server_tech[0]['id'] + " if { req.ssl_sni -i otherpublic.test.defo.ie  }", file=outf)
    # de-mux rules for other servers
    for s in server_tech:
        print("       use-server " + s['id'] + " if { req.ssl_sni -i " + s['id'] + "-pub." + base_domain + " }", file=outf)
        print("       use-server " + s['id'] + " if { req.ssl_sni -i " + s['id'] + "." + base_domain + " }", file=outf)
        print("       server " + s['id'] + " 127.0.0.1:" + str(s['altport']) + " check", file=outf)
    for targ in targets_to_make:
        print("       use-server ng if { req.ssl_sni -i " + targ['id'] + "-ng." + base_domain + " }", file=outf)
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

def make_openssl_scripts():
    tmp=s_server_bash.replace('PORT', '15447')
    tmp=tmp.replace('NAME','ss')
    tmp=tmp.replace('HRRTRIGGER','')
    outf=open(outdir+'/s_server_15447.sh','w')
    print(tmp, file=outf)
    hrrstr=s_server_bash.replace('PORT', '15448')
    hrrstr=hrrstr.replace('NAME','sshrr')
    # if we only enable p-384 for the server that'll almost
    # certainly trigger an HRR
    hrrstr=hrrstr.replace('HRRTRIGGER',' -groups P-384 ')
    outf=open(outdir+'/s_server_15448.sh','w')
    print(hrrstr, file=outf)

curl_bash_template='''#!/bin/bash

# Script to run curl tests against targets

# set -x

# structure is host:port mapped to pathname
declare -A targets=(
TARGETS
)

# where we expect a local ECH-enabled curl build
: ${BUILTCURL:="$HOME/code/curl/src/curl"}
# set to yes to run valgrind
: ${VG:="no"}

tout="5s"
curlcmd="curl -s "
vgcmd=""

if [ -f $BUILTCURL ]
then
    curlcmd="$BUILTCURL -s "
fi

if [[ "$VG" == "yes" ]]
then
    #vgcmd="valgrind --leak-check=full "
    vgcmd="valgrind --leak-check=full --error-limit=no --track-origins=yes "
    # allow more time if using valgrind
    tout="10s"
fi

curlargs=" --ech true --doh-url https://one.one.one.one/dns-query "

for targ in "${!targets[@]}"
do
    tmpf=$(mktemp)
    expected=${targets[$targ]}
    timeout $tout $vgcmd $curlcmd $curlargs $targ -o $tmpf
    res=$?
    if [[ "$res" != "$expected" ]]
    then
        echo "Problem with $targ - expected $expected but got $res"
    else
        echo "$targ as expected"
    fi
    # not yet using returned content, might in future
    rm -f $tmpf
done
'''

'''
Output a bash script that calls curl with for our
target URLs, and reports on success/fails
We'll only go after the nginx served URLs for now
as those are our main test targets.
'''
def make_curl_script():
    tlist = ""
    for targ in targets_to_make:
        url="https://" + targ['id'] + "-ng." + base_domain \
            + "/echstat.php?format=json"
        expected=targ['curl_expected']
        tlist += "    [" + url + "]=\"" + str(expected) + "\"\n"
    sout = curl_bash_template.replace('TARGETS',tlist)
    print(sout, file=outf)

if __name__ == "__main__":
    if args.outdir != None:
        outdir=args.outdir
    if not os.path.exists(outdir):
        os.makedirs(outdir)

    # check if there's a local file with additional tests
    # if that exists, it should define an array called
    # more_targets_to_make that has the same structure as
    # targets_to_make
    more_targets_to_make = []
    if os.path.exists("more_targets_to_make.py"):
        from more_targets_to_make import more_targets_to_make
        targets_to_make = targets_to_make + more_targets_to_make

    # where are we running from? (needed to find makeech.sh)
    runpath = os.path.dirname(__file__)

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
            subprocess.run(["bash", "-c", runpath + "/makeech.sh -public_name " + t['id'] + "-pub." + base_domain + \
                        " -pemout " + pemname + " >/dev/null 2>&1"])
        if not os.path.exists(pemname):
            print("Can't read " + pemname + " - exiting")
            sys.exit(1)
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
        if t['tech']['id'] == 'ss' or t['tech']['id'] == 'sshhr':
            # special case for OpenSSL s_server listeners
            pathname = "stats"
        url="https://" + t['target'] + "/" + pathname
        print('<p><a href=\"' + url + '\">' + url + '</a></p>', file=outf)
        print('<iframe src=\"' + url + '\" width=\"80%\" height=\"60\" title=\"testframe' + str(ind) + '\"></iframe>', file=outf)
        url="https://" + t['target'] + ":" + str(t['tech']['altport']) + "/" + pathname
        if t['tech']['id'] == 'ng':
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

    # other sites-enabled like files - these don't currently need any
    # test-related changes, but that could change...
    outf=open(outdir+'/ap.test.defo.ie.conf','w')
    print(apache_config, file=outf)
    outf=open(outdir+'/ly.test.defo.ie.conf','w')
    print(lighttpd_config, file=outf)
    # create the two openssl s_server scripts needed
    make_openssl_scripts()

    # make a curl script

    outf=open(outdir+'/curl-tests.sh','w')
    make_curl_script()

    # print documentation
    outf=open(outdir+'/README.md','w')
    makereadme()
    print("See " + outdir + "/README.md")

