#!/bin/python3

# A script to emit test-case names and test artefacts corresponding to
# those, very much still a work-in-progress...

# Eventual plan is to be able to spit out server configs, bind
# nsupdate scripts (if we stick with bind) and client scripts
# for selenium and command line tools (curl/s_client)
# We also need some way to report on tests, that's TBD for now

import os, sys, argparse, gc
import json

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
pathname="ech-check.php"

# ALPNs
good_alpn="http/1.1,h2"

# not sure what to put here but a quote is probably bad enough for now
bad_alpn="+"

# good key pairs
# generated with openssl ech -public_name public.test.defo.ie
good_pemfile='-----BEGIN PRIVATE KEY-----\n' + \
        'MC4CAQAwBQYDK2VuBCIEIACiPF1jkmMxwNuEBX9Epyci4hGBo/BuQjpmMOGz3B58\n'+ \
        '-----END PRIVATE KEY-----\n' + \
        '-----BEGIN ECHCONFIG-----\n' + \
        'AEb+DQBCmQAgACBrf4D75W04lOLJ4RVtJYz7lFamxDjiETWJA4KLCXeFUAAEAAEAAQATcHVibGljLnRlc3QuZGVmby5pZQAA\n' + \
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
    'b64ecl': 'AEb+DQBCmQAgACBrf4D75W04lOLJ4RVtJYz7lFamxDjiETWJA4KLCXeFUAAEAAEAAQATcHVibGljLnRlc3QuZGVmby5pZQAA',
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
server_tech=[
    { 'id': 'ng', 'description': 'nginx server', 'altport' : 15443 },
    { 'id': 'ap', 'description': 'apache server', 'altport' : 15444 },
    { 'id': 'ly', 'description': 'lighttpd server', 'altport' : 15445 },
    { 'id': 'ss', 'description': 'OpenSSL s_server', 'altport' : 15447 },
    { 'id': 'sshrr', 'description': 'OpenSSL s_server forcing HRR', 'altport' : 15448 },
    { 'id': 'hp', 'description': 'haproxy server with lighttpd back-end', 'altport' : 15446  },
    #{ 'id': 'hpsp', 'description': 'split-mode haproxy server', 'altport' : 15448 },
    #{ 'id': 'ngsp', 'description': 'split-mode nginx server', 'altport' : 15449 },
    #{ 'id': 'pf', 'description': 'postfix', 'altport' : 25 },
]
# could add NSS, boringssl and wolfssl server test tools maybe
# a filename for a temlpate we can fill via envsubst may be good

# encoding values are presentation syntax or arrays of those
# the first of these will get a shorter target name
targets_to_make=[
    {
      'id': 'min',
      'description': 'minimal HTTPS RR',
      'encoding':
        '1 . ech=' + good_kp['b64ecl'],
    },
    {
      'id': 'v1',
      'description': 'nominal, HTTPS RR',
      'encoding':
        '1 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp['b64ecl'] + ' ipv6hint=' + good_ipv6,
    },
    {
      'id': 'v2',
      'description': 'nominal, HTTPS RR',
      'encoding':
        '1 . alpn="' + good_alpn + '" ipv4hint=' + good_ipv4 + ' ech=' + good_kp['b64ecl'] + ' ipv6hint=' + good_ipv6,
    },
    {
      'id': 'v3',
      'description': 'two RRvals for nominal, minimal, HTTPS RR',
      'encoding':
        [
            '1 . ech=' + good_kp['b64ecl'],
            '2 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
        ],
    },
    {
      'id': 'bk1',
      'description': 'ECHConfigList with bad alg type (0xcccc) for ech kem',
      'encoding': '1 . ech=' + bad_kp1['b64ecl'],
    },
    {
     'id': 'bk2',
     'description': 'zero-length ECHConfig within ECHConfigList',
     'encoding': '1 . ech=' + bad_kp2['b64ecl'],
    },
    {
      'id': 'bv',
      'description': 'ECHConfigList with bad ECH version (0xcccc)',
      'encoding': '1 . ech=AEbMzABCmQAgACBrf4D75W04lOLJ4RVtJYz7lFamxDjiETWJA4KLCXeFUAAEAAEAAQATcHVibGljLnRlc3QuZGVmby5pZQAA',
    },
    {
      'id': 'badalpn',
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

# the set of good PEM files, all servers can load all of these
# note that some servers need the ".ech" file extension for loading
pemfiles_to_use = [ { 'id': 'good.pem.ech', 'content': good_pemfile },
                    { 'id': 'other.pem.ech', 'content': other_pemfile }]

# haproxy.cfg preamble
haproxy_cfg_preamble='global\n' + \
'       log /dev/log    local0\n' + \
'       log /dev/log    local1 notice\n' + \
'       chroot /var/lib/haproxy\n' + \
'       stats socket /run/haproxy/admin.sock mode 660 level admin\n' + \
'       stats timeout 30s\n' + \
'       user haproxy\n' + \
'       group haproxy\n' + \
'       daemon\n' + \
'       # Default SSL material locations\n' + \
'       ca-base /etc/ssl/certs\n' + \
'       crt-base /etc/ssl/private\n' + \
'       # See: https://ssl-config.mozilla.org/#server=haproxy&server-version=2.0.3&config=intermediate\n' + \
'       ssl-default-bind-ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384\n' + \
'       ssl-default-bind-ciphersuites TLS_AES_128_GCM_SHA256:TLS_AES_256_GCM_SHA384:TLS_CHACHA20_POLY1305_SHA256\n' + \
'       ssl-default-bind-options ssl-min-ver TLSv1.2 no-tls-tickets\n' + \
'defaults\n' + \
'       log     global\n' + \
'       mode    http\n' + \
'       option  httplog\n' + \
'       option  dontlognull\n' + \
'       timeout connect 5000\n' + \
'       timeout client  50000\n' + \
'       timeout server  50000\n' + \
'       errorfile 400 /etc/haproxy/errors/400.http\n' + \
'       errorfile 403 /etc/haproxy/errors/403.http\n' + \
'       errorfile 408 /etc/haproxy/errors/408.http\n' + \
'       errorfile 500 /etc/haproxy/errors/500.http\n' + \
'       errorfile 502 /etc/haproxy/errors/502.http\n' + \
'       errorfile 503 /etc/haproxy/errors/503.http\n' + \
'       errorfile 504 /etc/haproxy/errors/504.http\n' + \
'frontend defotest\n' + \
'       mode tcp\n' + \
'       option tcplog\n' + \
'       bind :443\n' + \
'       use_backend defotestservers\n' + \
'backend defotestservers\n' + \
'       mode tcp\n' + \
'       tcp-request inspect-delay 5s\n' + \
'       tcp-request content accept if { req_ssl_hello_type 1 }\n'

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

# produce a set of nsupdate commands for one target
def donsupdate(tech, target, hp):
    description='"' + tech['description'] + '/' +hp['description'] + '"'
    print("update delete " + target + " A", file=outf)
    print("update add " + target + " " + str(ttl) + " A", good_ipv4 , file=outf)
    print("update delete " + target + " AAAA", file=outf)
    print("update add " + target + " " + str(ttl) + " AAAA " + good_ipv6, file=outf)
    print("update delete " + target + " TXT", file=outf)
    print("update add " + target + " " + str(ttl) + " TXT", description , file=outf)
    print("update delete " + target + " HTTPS", file=outf)
    # if encoding is an array then we want multiple HTTPS RR values
    if isinstance(hp['encoding'],str):
        print("update add " + target + " " + str(ttl) + " HTTPS", hp['encoding'] , file=outf)
    else:
        for enc in hp['encoding']:
            print("update add " + target + " " + str(ttl) + " HTTPS", enc, file=outf)
    print("send", file=outf)
    targets_to_test.append({'tech': tech, 'target':target})

# prototype for a bit of bind nsupdate scripting
def donsupdates(tech):
    for targ in targets_to_make:
        # use shorter name for base-case
        if targets_to_make.index(targ) == 0:
            target=tech['id'] + "." + base_domain
        else:
            target=targ['id'] + "-" + tech['id'] + "." + base_domain
        donsupdate(tech, target, targ)

# print lines that haproxy needs to forward port 443 traffic to the
# correct client-facing server - note: haproxy in this mode is only
# a TCP de-muxer and is doing no ECH nor TLS processing
def haproxy_fe_config():
    print(haproxy_cfg_preamble, file=outf)
    for t in targets_to_test:
        print("       use-server " + t['target'] + " if { req.ssl_sni -i " + t['target'] + " }", file=outf)
        print("       server " + t['target'] + " 127.0.0.1:" + str(t['tech']['altport']) + " check", file=outf)
    # default on last line? TODO: check also TODO: consider a special default server
    print("       server default 127.0.0.1:" + str(targets_to_test[0]['tech']['altport']), file=outf)

# print out a sites-enabled config file for nginx
def nginx_site():
    print(nginx_conf_preamble, file=outf)

if __name__ == "__main__":
    if args.outdir != None:
        outdir=args.outdir
    if not os.path.exists(outdir):
        os.makedirs(outdir)
    # print("Reset DNS commands:")
    outf=open(outdir+'/resetdns.commands','w')
    resetdnscommands()
    # print("DNS commands:")
    # do all the oddball tests with 1st named tech
    outf=open(outdir+'/addRRs.commands','w')
    donsupdates(server_tech[0])
    # only do nominal cases for other techs
    for tech in server_tech:
        if server_tech.index(tech) == 0:
            continue
        target=tech['id'] + "." + base_domain
        donsupdate(tech, target, targets_to_make[0])

    # print("URLs to test:")
    outf=open(outdir+'/urls_to_test','w')
    for t in targets_to_test:
        print("https://" + t['target'] + "/" + pathname, file=outf)
    # print("ECH PEM files:")
    if not os.path.exists(outdir+"/echkeydir"):
        os.makedirs(outdir+"/echkeydir")
    for p in pemfiles_to_use:
        outf=open(outdir+'/echkeydir/'+p['id'],'w')
        print(p['content'], file=outf)
    # print("haproxy config lines:")
    outf=open(outdir+'/haproxy.cfg','w')
    haproxy_fe_config()
    print("On zone factory:")
    print("   To reset test.defo.ie DNS from sratch:")
    print("        $ sudo nsupdate -l <" + outdir + "/resetdns.commands")
    print("   To add DNS RRs for tests:")
    print("        $ sudo nsupdate -l <" + outdir + "/addRRs.commands")
    print("On the " + base_domain + " VM:")
    print("   To replace old ECH PEM files:")
    print("        $ sudo rm -rf /etc/echkeydir")
    print("        $ sudo cp -r " + outdir + "/echkeydir /etc")
    print("   To replace the nginx config:")
    print("        $ sudo cp " + outdir + "/ng-site.conf /etc/nginx/sites-enabled/")
    print("   If new \"virtualhost\"'s added by the above you may need to re-run cerbot")
    print("        $ sudo certbot --nginx")
    print("   To replace haproxy TCP mux'er config:")
    print("        $ sudo cp " + outdir + "/haproxy.cfg /etc/haproxy")
    print("        $ sudo service haproxy restart")

