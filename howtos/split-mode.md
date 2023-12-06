
# Testing ECH split mode with haproxy or nginx

We assume you've already built our OpenSSL fork in ``$HOME/code/openssl`` and
have gotten the [localhost-tests](localhost-tests.md) working, and you should
have created an ``echkeydir`` as described
[here](../README.md#server-configs-preface---key-rotation-and-slightly-different-file-names).

Split-mode tests use lighttpd [HOWTO](lighttpd.md) as the back-end web server
for split-mode processing, and can use either [nginx](nginx.md) or
[haproxy](haproxy.md) as the front-end.

This file mostly has the same structure as the other HOWTOs, but much of the
content is by reference to others.

# Nomenclature

Here's some terminology we use when talking about shared- or split-mode
configurations.  

We'll name and document them like this:

            N. setup-name: Client <--[prot]--> frontend <--[prot]--> Backend

Where "N" is a number, "setup-name" is some catchy title we use just for ease
of reference, "client" is ``curl`` or ``s_client``, "frontend" is haproxy or
nginx so we'll just note the relevant port number used by our test setup,
and as the "backend" is also always lighttpd, we'll do the same for that.
Finally, "prot" is some string describing the protocol options on that hop.

With that our first and most basic setup is:

            1. ECH-front: Client <--[TLS+ECH]--> :7443 <--[Plaintext HTTP]--> :3480

The second one just turns on TLS, via two entirely independent TLS sessions,
with no ECH to the backend:

            2. Two-TLS: Client <--[TLS+ECH]--> :7444 <--[other-TLS]--> :3481

The third has one TLS session from the client to backend, with the frontend
just using the (outer) SNI for e.g. routing, if at all, and so that the
frontend doesn't get to see the plaintext HTTP traffic. This isn't that
interesting for us (other than to understand how to set it up), but is on the
path to one we do want.

            3. One-TLS: Client <--[TLS]--> :7445 <--[same-TLS]--> :3482

The fourth is where we use ECH split-mode, with the same TLS session between client
and backend but where the frontend did decrypt the ECH and just pass on the
inner CH to the backend, but where the frontend doesn't get to see the
plaintext HTTP traffic.  (As in the previous case, we have another backend
listener at :3485 to handle the case of both an outer SNI and a failure to
decrypt an ECH.)

            4. Split-mode: Client <--[TLS+ECH]--> :7446 <--[inner-CH]--> :3484

A fifth option that we don't plan to investigate but that may be worth naming
is where we have two separate TLS sessions both of which independently use ECH.
If that did prove useful, it'd probably be fairly easy to do.

            5. Two-ECH: Client <--[TLS+ECH]--> frontend <--[other-TLS+ECH]--> backend

# Build

There are no special build instructions for split-mode, you
just need to follow the relevant HOWTOs:

- [nginx](nginx.md#build)
- [haproxy](haproxy.md#build)
- [lighttpd](lighttpd.md#build)

# Configuration

The split-mode configuration settings are described for each
of the servers:

- [nginx](nginx.md#configuration)
- [haproxy](haproxy.md#configuration)
- [lighttpd](lighttpd.md#configuration)

Briefly, for front-ends that means:

- for haproxy, using the ``ech-decrypt`` directive in ``mode tcp`` frontends,
  e.g. ``tcp-request ech-decrypt echkeydir`` where ``echkeydir`` is the 
  usual directory used for ECH PEM files
- for nginx, adding a ``ssl_echkeydir $RUNTOP/echkeydir;`` setting to a 
  ``stream`` stanza

# Test

Individual tests are described in the links below but don't cover split-mode.

- [nginx](nginx.md#test)
- [haproxy](haproxy.md#test)
- [lighttpd](lighttpd.md#test)

For split-mode we have a special test script
[testsplitmode.sh](../scripts/testsplitmode.sh) that takes one command line
argument (either ``haproxy`` or ``nginx``) to specify the frontend to use.
That script starts the relevant front-end server and a lighttpd instance as
a backend and then runs a client against the chosen front-end, checking
the usual GREASEing, use of the ``public_name`` a real use of ECH and a
case that triggers HRR.

In addition, since lighttpd doesn't support TLS ``early_data`` a test is
run to check ECH split-mode with ``early_data`` both with and without
triggering HRR. That uses an ``openssl s_server`` instance as the backend.
(Testing ``early_data`` requires a first TLS connection to acquire the
resumption tickets needed, then a second TLS connection to send a 
request with ``early_data``.)

TODO: check logs for split-mode+HRR+early to ensure all we expect is happening.

For split-mode tests in our configurations the frontend listens on port 7446
and the backend listens on port 3484.

```bash
    $ # split-mode test
    $ $HOME/code/ech-dev-utils/scripts/echcli.sh -s localhost  -H foo.example.com -p 7446 -P echconfig.pem -f index.html
    Running /home/user/code/ech-dev-utils/scripts/echcli.sh at 20230315-154634
    Assuming supplied ECH is encoded ECHConfigList or SVCB
    /home/user/code/ech-dev-utils/scripts/echcli.sh Summary: 
    Looks like ECH worked ok
    ECH: success: outer SNI: 'example.com', inner SNI: 'foo.example.com'
    $ # shared-mode test
    $ $HOME/code/ech-dev-utils/scripts/echcli.sh -s localhost  -H foo.example.com -p 7445 -P echconfig.pem -f index.html
    Running /home/user/code/ech-dev-utils/scripts/echcli.sh at 20230315-154900
    Assuming supplied ECH is encoded ECHConfigList or SVCB
    /home/user/code/ech-dev-utils/scripts/echcli.sh Summary: 
    Looks like ECH worked ok
    ECH: success: outer SNI: 'example.com', inner SNI: 'foo.example.com'
```

# Logs

No special logging is done for split-mode.

- [nginx](nginx.md#logs)
- [haproxy](haproxy.md#logs)
- [lighttpd](lighttpd.md#logs)

# PHP variables

These should be available as usual for the backend.

- [nginx](nginx.md#php-variables)
- [haproxy](haproxy.md#php-variables)
- [lighttpd](lighttpd.md#php-variables)

# Code changes   

These are described for the individual servers:

- [nginx](nginx.md#code-changes)
- [haproxy](haproxy.md#code-changes)
- [lighttpd](lighttpd.md#code-changes)

# Reloading ECH keys

These are described for the individual servers (noting
that we don't yet support key reloading for haproxy):

- [nginx](nginx.md#reloading-ech-keys)
- [haproxy](haproxy.md#reloading-ech-keys)
- [lighttpd](lighttpd.md#reloading-ech-keys)

# Debugging

These are described for the individual servers:

- [nginx](nginx.md#debugging)
- [haproxy](haproxy.md#debugging)
- [lighttpd](lighttpd.md#debugging)
