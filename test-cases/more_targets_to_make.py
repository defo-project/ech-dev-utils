
from test_cases_settings import *


'''
Each element of the array specifies a test case. The first one will map to the
DNS name many10-ng.test.defo.ie and accessing the URL below shoulo give info on
whether ECH happened (if the test is such that things ought work):

            https://many10.test.defo.ie/echstat.php?format=json

The fields that can be used for each test case are:

    - id - short string (don't include any "-") used in DNS label
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
      'description': '10 values in HTTPS RR',
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
      'id': 'mixedmode', 'expected': 'error, but likely ignored', 'curl_expected': 6,
      'description': 'AliasMode (0) and ServiceMode (!=0) are not allowed together',
      'encoding':
        [
            '1 . ipv4hint=' + good_ipv4 + ' ech=' + good_kp2['b64ecl'] + ' ipv6hint=' + good_ipv6,
            '0 . test.defo.ie'
        ]
    }

]
