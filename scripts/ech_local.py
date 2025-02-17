# Test ECH against a loclhost server with a command line provided base64
# endoced ECHConfig

import sys, json
import logging
import ssl
import socket
import urllib.parse
import base64

import httptools
from argparse import ArgumentParser

def parse_http_response(response_bytes):
    parser = HTTPResponseParser()
    parser.feed_data(response_bytes)
    return {
        'status_code': parser.parser.get_status_code(),
        'reason': parser.reason,
        'headers': parser.headers,
        'body': bytes(parser.body),
    }

def get_http(hostname, port, path, echconfigs) -> bytes:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    # context.load_verify_locations(cafile='/etc/ssl/cert.pem')
    # load standard CAs
    context.load_verify_locations(cafile='/etc/ssl/certs/ca-certificates.crt')
    # also take a local (fake) CA
    if args.ca:
        context.load_verify_locations(cafile=args.ca)
    context.options |= ssl.OP_ECH_GREASE
    for echconfig in echconfigs:
        try:
            context.set_ech_config(echconfig)
            context.check_hostname = False
        except ssl.SSLError as e:
            pass
    with socket.create_connection(("localhost", args.port)) as sock:
        with context.wrap_socket(sock, server_hostname=hostname, do_handshake_on_connect=False) as ssock:
            ssock.do_handshake()
            if ssock.get_ech_status().name == ssl.ECHStatus.ECH_STATUS_GREASE_ECH:
                echconfigs = [ssock._sslobj.get_ech_retry_config()]
                return get_http(hostname, port, path, echconfigs)
            request = f'GET {path} HTTP/1.1\r\nHost: {hostname}\r\nConnection: close\r\n\r\n'
            ssock.sendall(request.encode('utf-8'))
            response = b''
            while True:
                data = ssock.recv(4096)
                if not data:
                    break
                response += data
            return response, ssock.get_ech_status()

def get(url):
    parsed = urllib.parse.urlparse(url)
    domain = parsed.hostname
    port = parsed.port or 443
    if port != 443:
        print("We don't do localhost tests with a port in the URL")
        sys.exit(5)
    echconfig = base64.b64decode(args.ech)
    echconfigs = [ echconfig ]
    request_path = (parsed.path or '/') + ('?' + parsed.query if parsed.query else '')
    raw, ech_status = get_http(domain, port, request_path, echconfigs)
    return parse_http_response(raw), ech_status

if __name__ == '__main__':
    parser = ArgumentParser(description="test ECH for a URL via python client")
    parser.add_argument("-c", "--ca", help="local (fake) CA to use")
    parser.add_argument("-e", "--ech", help="command line ECHConfig")
    parser.add_argument("-p", "--port", type=int, help="localhost port")
    parser.add_argument("-V", "--superverbose", action="store_true",  help="extra additional output")
    parser.add_argument("-v", "--verbose", action="store_true",  help="additional output")
    parser.add_argument('--url', help="URLs to test")

    args = parser.parse_args()
    if args.superverbose:
        args.verbose = True
    if args.port is None:
        print("You need to provide the localhost port to use")
        sys.exit(3)
    if args.ech is None:
        print("You need to provide the ECHconfg to use")
        sys.exit(4)

    print("Trying", args.url, "on localhost:", args.port, "\n\twith ECH:", args.ech)

    try:
        response, ech_status = get(args.url)
    except Exception as e:
        print(e)
        sys.exit(1)
    if args.superverbose:
        try:
            # this'll work for our echstat.php tests, which is most
            result = json.loads(response['body'])
            print(result)
        except:
            print(response)
    if ech_status.name == 'ECH_STATUS_SUCCESS':
        sys.exit(0)
    sys.exit(2)
