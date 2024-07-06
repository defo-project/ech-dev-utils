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

    # instructions...
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

