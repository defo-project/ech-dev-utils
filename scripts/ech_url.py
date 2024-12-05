import sys, json
import logging
import ssl
import socket
import urllib.parse

import dns.resolver
import httptools
from argparse import ArgumentParser

class HTTPResponseParser:
    def __init__(self):
        self.headers = {}
        self.body = bytearray()
        self.status_code = None
        self.reason = None
        self.http_version = None
        self.parser = httptools.HttpResponseParser(self)

    def on_message_begin(self):
        pass

    def on_status(self, status):
        self.reason = status.decode('utf-8', errors='replace')

    def on_header(self, name, value):
        self.headers[name.decode('utf-8')] = value.decode('utf-8')

    def on_headers_complete(self):
        pass

    def on_body(self, body):
        self.body.extend(body)

    def on_message_complete(self):
        pass

    def feed_data(self, data):
        self.parser.feed_data(data)

def parse_http_response(response_bytes):
    parser = HTTPResponseParser()
    parser.feed_data(response_bytes)
    return {
        'status_code': parser.parser.get_status_code(),
        'reason': parser.reason,
        'headers': parser.headers,
        'body': bytes(parser.body),
    }

def get_echconfigs(domain, port):
    try:
        if port == 443:
            answers = dns.resolver.resolve(domain, 'HTTPS')
        else:
            answers = dns.resolver.resolve("_"+str(port)+"._https."+domain, 'HTTPS')
    except dns.resolver.NoAnswer:
        logging.warning(f"No HTTPS record found for {domain}:{port}")
        return None
    except Exception as e:
        logging.error(f"DNS query failed: {e}")
        return None

    configs = []

    for rdata in answers:
        if hasattr(rdata, 'params'):
            params = rdata.params
            echconfig = params.get(5)
            if echconfig:
                configs.append(echconfig.ech)

    if len(configs) == 0:
        logging.warning(f"No echconfig found in HTTPS record for {domain}")

    return configs

def get_http(hostname, port, path, echconfigs) -> bytes:
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    # context.load_verify_locations(cafile='/etc/ssl/cert.pem')
    context.load_verify_locations(cafile='/etc/ssl/certs/ca-certificates.crt')
    context.options |= ssl.OP_ECH_GREASE
    for echconfig in echconfigs:
        try:
            context.set_ech_config(echconfig)
            context.check_hostname = False
        except ssl.SSLError as e:
            pass
    with socket.create_connection((hostname, port)) as sock:
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
    echconfigs = get_echconfigs(domain, port)
    request_path = (parsed.path or '/') + ('?' + parsed.query if parsed.query else '')
    raw, ech_status = get_http(domain, port, request_path, echconfigs)
    return parse_http_response(raw), ech_status

if __name__ == '__main__':
    parser = ArgumentParser(description="test ECH for a URL via python client")
    parser.add_argument('--url', help="URLs to test")
    parser.add_argument("-v", "--verbose", action="store_true",  help="additional output")
    parser.add_argument("-V", "--superverbose", action="store_true",  help="extra additional output")
    args = parser.parse_args()
    response, ech_status = get(args.url)
    result = json.loads(response['body'])
    print(result)
    if ech_status.name == 'ECH_STATUS_SUCCESS':
        sys.exit(0)
    sys.exit(2)
