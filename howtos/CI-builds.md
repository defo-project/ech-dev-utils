
# DEfO Project CI build/test setup

This is a work-in-progress, don't bother reading it yet:-)

The goal of these continuuous integration builds and related tests
is to indentify any cases where upstream have diverged from our
ECH-enabled forks so that a code-merge would fail or a basic test
would fail.

The upstream and forks concerned are:

- OpenSSL - [https://github.com/defo-project/openssl]
- Apache2 httpd - [https://github.com/defo-project/httpd]
- curl - [https://github.com/defo-project/curl]
- nginx - [https://github.com/defo-project/nginx]
- lighttpd1.4 - [https://github.com/defo-project/lighttpd1.4]
- haproxy - [https://github.com/defo-project/haproxy]

In each case, the relevant CI build file is in
``.github/workflows/packages.yml``. We've also added the ECH code to the
relevant ``master`` (or ``main``) branch of each of the above.

Mostly the ECH-enabled code in the various repos here was originally developed
under the equivalent fork in the ``sftcd`` account. Some fixes (and esp new CI
scripting) was added to these forks under the ``jspricke`` account. We expect
that processing of CI issues will likely involve other DEfO-project github member
accounts too. 

## packages.yml

There is a lot in common across the various ``packages.yml`` files, they each:

- exit on any error
- re-use debian unstable build tools (from @jspricke)
- attempt a ``git merge`` with the upstream for the relevant project
- build the relevant ECH-enabled repo resulting from the merge
- store built packages in a "pseudo" branch called ``packages``
- attempt a basic test using the scripts from this repo and those packages

## OpenSSL

## Apache2 httpd

## nginx

## lighttpd1.4

## haproxy

