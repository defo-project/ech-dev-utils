
from test_cases_settings import *

'''
Each element of the array specifies a test case. The first one maps to the
DNS name `many-ng.test.defo.ie` - the "-ng" indicates we run the server part of
this test on an nginx instance. Accessing the URL below should give info on
whether ECH happened (if the test is such that things ought work):

            https://many-ng.test.defo.ie/echstat.php?format=json

The fields that can be used for each test case are:

    - id - short string (don't include any "-") used in first DNS label
    - expected - whether we think this should work (for human consumption, so
      text is ok here)
    - curl_expected - value we expect command line invocation of curl to return
    - description - a string that'll be published in the DNS as a TXT RR (and
      elsewhere) to help remember what the test does
    - encoding: presentation syntax for an HTTPS RR, or, an array of such, if
      we should have more than one
    - (optional) noaddr: if this has the value 1 (as a number, not string) then
      we won't publish an A/AAAA to go with the name

The presentation syntax encoding can make use of variables that are set in the
test_cases_settings file, e.g. good_ipv4 is the IPv4 address of our test VM.
After printing, the result should be presentation syntax that'll be accepted by
bind's `nsupdate -l` command.
'''
more_targets_to_make=[
    {
      'id': 'many', 'expected': 'success', 'curl_expected': 0,
      'description': '20 values in HTTPS RR',
      'encoding':
        [
            '1 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
            '2 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
            '3 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
            '4 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
            '5 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
            '6 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
            '7 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
            '8 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
            '9 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
            '10 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
            '11 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
            '12 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
            '13 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
            '14 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
            '15 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
            '16 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
            '17 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
            '18 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
            '19 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
            '20 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
        ],
    },
    {
      'id': 'mixedmode', 'expected': 'error, but likely ignored', 'curl_expected': 35,
      'description': 'AliasMode (0) and ServiceMode (!=0) are not allowed together',
      'encoding':
        [
            '1 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
            '0 test.defo.ie'
        ]
    },
    {
      'id': 'p256', 'expected': 'success, but client-dependent', 'curl_expected': 0,
      'description': 'uses p256, hkdf-385 and chacha',
      'encoding': '1 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp256['b64ecl'] + ' ipv6hint=' + good_ipv6,
    },
    {
      'id': 'curves1', 'expected': 'success, but client-dependent', 'curl_expected': 0,
      'description': 'two RRVALs one using x25519 and one with p256, same priority',
      'encoding':
        [
            '1 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
            '1 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp256['b64ecl'] + ' ipv6hint=' + good_ipv6,
        ]
    },
    {
      'id': 'curves2', 'expected': 'success, but client-dependent', 'curl_expected': 0,
      'description': 'two RRVALs one using x25519 (priority=1) and one with p256 (priority=2)',
      'encoding':
        [
            '1 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
            '2 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp256['b64ecl'] + ' ipv6hint=' + good_ipv6,
        ]
    },
    {
      'id': 'curves3', 'expected': 'success, but client-dependent', 'curl_expected': 0,
      'description': 'two RRVALs one using x25519 (priority=2) and one with p256 (priority=1)',
      'encoding':
        [
            '1 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp256['b64ecl'] + ' ipv6hint=' + good_ipv6,
            '2 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
        ]
    },
    {
      'id': 'h2alpn', 'expected': 'success', 'curl_expected': 0,
      'description': 'alpn is only h2',
      'encoding': '1 . alpn="h2" ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
    },
    {
      'id': 'h1alpn', 'expected': 'success', 'curl_expected': 0,
      'description': 'alpn is only http/1.1',
      'encoding': '1 . alpn="http/1.1" ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
    },
    {
      'id': 'mixedalpn', 'expected': 'success', 'curl_expected': 0,
      'description': 'alpn is http/1.1,foo,bar,bar,bom,h2',
      'encoding': '1 . alpn="http/1.1,foo,bar,baz,bom,h2" ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
    },
    {
      'id': 'longalpn', 'expected': 'success', 'curl_expected': 0,
      'description': 'alpn is very long ending with http/1.1,h2',
      'encoding':
            '1 . alpn="' + \
            'bogus0,bogus1,bogus2,bogus3,bogus4,bogus5,bogus6,bogus7,bogus8,bogus9,' + \
            'bogus10,bogus11,bogus12,bogus13,bogus14,bogus15,bogus16,bogus17,bogus18,bogus19,' + \
            'bogus20,bogus21,bogus22,bogus23,bogus24,bogus25,bogus26,bogus27,bogus28,bogus29,' + \
            'bogus30,bogus31,bogus32,bogus33,bogus34,bogus35,bogus36,bogus37,bogus38,bogus39,' + \
            'bogus40,bogus41,bogus42,bogus43,bogus44,bogus45,bogus46,bogus47,bogus48,bogus49,' + \
            'bogus50,bogus51,bogus52,bogus53,bogus54,bogus55,bogus56,bogus57,bogus58,bogus59,' + \
            'bogus60,bogus61,bogus62,bogus63,bogus64,bogus65,bogus66,bogus67,bogus68,bogus69,' + \
            'bogus70,bogus71,bogus72,bogus73,bogus74,bogus75,bogus76,bogus77,bogus78,bogus79,' + \
            'bogus80,bogus81,bogus82,bogus83,bogus84,bogus85,bogus86,bogus87,bogus88,bogus89,' + \
            'bogus90,bogus91,bogus92,bogus93,bogus94,bogus95,bogus96,bogus97,bogus98,bogus99,' + \
            'http/1.1,h2" ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
    },
    {
      'id': '2thenp', 'expected': 'success', 'curl_expected': 0,
      'description': 'ECHConfiglist with 2 entries a 25519 one then a p256 one (both good keys)',
      'encoding': '1 . ech=AK3+DQBCqQAgACBlm7cfDx/gKuUAwRTe+Y9MExbIyuLpLcgTORIdi69uewAEAAEAAQATcHVibGljLnRlc3QuZGVmby5pZQAA/g0AY54AEABBBBYJC5HR0vrc9fD15nWKWAWXShsYwZvljRvQLCjWjgo+G5g27heCsrxxGRo+vlpbNVQXtTl4nq6YxomDhK4jlpwABAACAAMAE3B1YmxpYy50ZXN0LmRlZm8uaWUAAA=='
    },
    {
      'id': 'pthen2', 'expected': 'success', 'curl_expected': 0,
      'description': 'ECHConfiglist with 2 entries a p256 one then a 25519 one (both good keys)',
      'encoding': '1 . ech=AK3+DQBjngAQAEEEFgkLkdHS+tz18PXmdYpYBZdKGxjBm+WNG9AsKNaOCj4bmDbuF4KyvHEZGj6+Wls1VBe1OXierpjGiYOEriOWnAAEAAIAAwATcHVibGljLnRlc3QuZGVmby5pZQAA/g0AQqkAIAAgZZu3Hw8f4CrlAMEU3vmPTBMWyMri6S3IEzkSHYuvbnsABAABAAEAE3B1YmxpYy50ZXN0LmRlZm8uaWUAAA=='
    },
    {
      'id': 'withext', 'expected': 'success', 'curl_expected': 0,
      'description': 'minimal HTTPS RR but with 2 ECHConfig extensions',
      'encoding':
        '1 . ech=' + good_withext['b64ecl'],
    },
]
