
# Testing ECH split mode with haproxy or nginx

We assume you've already built our OpenSSL fork in ``$HOME/code/openssl`` and
have gotten the [localhost-tests](localhost-tests.md) working, and you should
have created an ``echkeydir`` as described
[here](../README.md#server-configs-preface---key-rotation-and-slightly-different-file-names).

Split-mode tests use lighttpd [HOWTO](lighttpd.md) as the back-end web server
for split-mode processing, and can use either [nginx](nginx.md) or
[haproxy](haproxy.md) as the front-end.

This file has the same structure as the other HOWTOs, but most of the
content is by reference to others.

# Build

- [nginx](nginx.md#build)
- [haproxy](haproxy.md#build)

# Configuration

# Test

# Logs

# PHP variables

# Code changes   

# Reloading ECH keys

# Debugging
