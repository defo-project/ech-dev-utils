
from test_cases_settings import *

more_targets_to_make=[
    {
      'id': 'many-10', 'expected': 'success',
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
        ],
    }
]
