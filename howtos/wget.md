
# Integrating ECH into wget

Now that we've made progress with
[curl](https://github.com/sftcd/curl/blob/ECH-experimental/docs/ECH.md), it's
natural to look at wget.  wget2 seems to be the code target going forward and
has developed some since we first looked (in 2019) and does now have an OpenSSL
option.

wget2 source is at https://gitlab.com/gnuwget/wget2 and I have a fork at
https://gitlab.com/sftcd/wget2

Let's see what DNS support is like... There's a ``libwget/dns_cache.c`` that
looks like it'd be useful if we added HTTPS RRs to the ``cache_entry`` type,
but so far it seems to only be populated via ``getaddrinfo()`` which is a bit
of a gotcha for our purposes. Checking... So far it's not looking like there's
an easy path forward to retrieve HTTPS RRs so the situation with wget is
probably similar to that with curl when DoH is not in use (albeit with perhaps
better caching and TLS session re-use).

So, for now, we don't have good news for ECH integration with wget.  If anyone
has good ideas for getting ECH working in wget2, we'd be happy to explore
those.
