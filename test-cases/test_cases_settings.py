
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

# URL pathname for (most) tests
pathname="echstat.php?format=json"

# URL pathname for s_server tests
s_pathname="stats"

# ALPNs
good_alpn="http/1.1,h2"

# not sure what to put here but a quote is probably bad enough for now
bad_alpn="+"

# good key pairs
# generated with openssl ech -public_name public.test.defo.ie
good_pemfile='''-----BEGIN PRIVATE KEY-----
MC4CAQAwBQYDK2VuBCIEIOCiDSigzHBNxUlCkWsEXd8JFTqTi6CREnxNM2vMiMlk
-----END PRIVATE KEY-----
-----BEGIN ECHCONFIG-----
AEb+DQBCqQAgACBlm7cfDx/gKuUAwRTe+Y9MExbIyuLpLcgTORIdi69uewAEAAEAAQATcHVibGljLnRlc3QuZGVmby5pZQAA
-----END ECHCONFIG-----
'''

# generated with openssl ech -public_name otherpublic.test.defo.ie
other_pemfile='''-----BEGIN PRIVATE KEY-----
MC4CAQAwBQYDK2VuBCIEIHAxrYK93ytX/vnj912RlvRM3hMrAmG00hsU3jEgxUpy
-----END PRIVATE KEY-----
-----BEGIN ECHCONFIG-----
AEv+DQBHdAAgACCCU49qdxKOUXJPs3wlsM06v/t42sMH5xQOL37MAd3HaAAEAAEAAQAYb3RoZXJwdWJsaWMudGVzdC5kZWZvLmllAAA=
-----END ECHCONFIG-----
'''

# generated with openssl ech -public_name public.test.defo.ie -suite 0x10,2,3
# that means p256, hkdf-384 and chacha
p256_pemfile='''-----BEGIN PRIVATE KEY-----
MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgZEy9rEnJRS7I/STb
rvs/+3gBbyVGHHcWj8PqQqGLEU+hRANCAAQWCQuR0dL63PXw9eZ1ilgFl0obGMGb
5Y0b0Cwo1o4KPhuYNu4XgrK8cRkaPr5aWzVUF7U5eJ6umMaJg4SuI5ac
-----END PRIVATE KEY-----
-----BEGIN ECHCONFIG-----
AGf+DQBjngAQAEEEFgkLkdHS+tz18PXmdYpYBZdKGxjBm+WNG9AsKNaOCj4bmDbuF4KyvHEZGj6+Wls1VBe1OXierpjGiYOEriOWnAAEAAIAAwATcHVibGljLnRlc3QuZGVmby5pZQAA
-----END ECHCONFIG-----
'''

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
good_kp256={
    'id': 'good_kp256',
    'description': 'A good ECH key pair with public.test.defo.ie using p256',
    'public_name': 'public.test.defo.ie',
    'b64ecl': 'AGf+DQBjngAQAEEEFgkLkdHS+tz18PXmdYpYBZdKGxjBm+WNG9AsKNaOCj4bmDbuF4KyvHEZGj6+Wls1VBe1OXierpjGiYOEriOWnAAEAAIAAwATcHVibGljLnRlc3QuZGVmby5pZQAA',
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

