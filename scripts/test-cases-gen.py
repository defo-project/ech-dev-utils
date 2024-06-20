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

# all DNS names mapping to tests will be one label below this name
base_domain='test.defo.ie'

# TTL to use for all test RRs
ttl=10

# IP addresses
good_ipv4='185.88.140.5'
# the v6 below is for defo.ie TODO: enable v6 on test.defo.ie
good_ipv6='2a00:c6c0:0:116:5::10'

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
    { 'id': 'hp', 'description': 'haproxy server with lighttpd back-end', 'altport' : 15446  },
    { 'id': 'ss', 'description': 'OpenSSL s_server', 'altport' : 15447 },
    { 'id': 'hpsp', 'description': 'split-mode haproxy server', 'altport' : 15448 },
    { 'id': 'ngsp', 'description': 'split-mode nginx server', 'altport' : 15449 },
    { 'id': 'pf', 'description': 'postfix', 'altport' : 25 },
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
urls_to_test=[]

# the set of good PEM files, all servers can load all of these
pemfiles_to_use = [ good_pemfile, other_pemfile ]

# produce a set of nsupdate commands for one target
def donsupdate(tech, target, hp):
        description='"' + tech['description'] + '/' +hp['description'] + '"'
        print("update delete " + target + " A")
        print("update add " + target + " " + str(ttl) + " A", good_ipv4 )
        print("update delete " + target + " TXT")
        print("update add " + target + " " + str(ttl) + " TXT", description )
        print("update delete " + target + " HTTPS")
        # if encoding is an array then we want multiple HTTPS RR values
        if isinstance(hp['encoding'],str):
            encoding='"' + hp['encoding'] + '"'
            print("update add " + target + " " + str(ttl) + " HTTPS", encoding )
        else:
            for enc in hp['encoding']:
                encoding='"' + enc + '"'
                print("update add " + target + " " + str(ttl) + " HTTPS", encoding )
        print("send")
        url="https://" + target + "/" + pathname
        urls_to_test.append(url)

# prototype for a bit of bind nsupdate scripting
def donsupdates(tech):
    for targ in targets_to_make:
        # use shorter name for base-case
        if targets_to_make.index(targ) == 0:
            target=tech['id'] + "." + base_domain
        else:
            target=targ['id'] + "-" + tech['id'] + "." + base_domain
        donsupdate(tech, target, targ)

if __name__ == "__main__":
    print("DNS commands:")
    donsupdates(server_tech[0])
    print("URLs to test:")
    for u in urls_to_test:
        print(u)
    print("PEM files:")
    for p in pemfiles_to_use:
        print(p)

