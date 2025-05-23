
# DEfO Project CI build/test setup

The goal of these continuous integration (CI) builds and tests is to identify
any cases where upstream code has diverged from our ECH-enabled forks, such
that a ``git merge`` would fail, or a basic test of the result of such a
merge fails.

The forks concerned are:

- [OpenSSL](https://github.com/defo-project/openssl)
- [curl](https://github.com/defo-project/curl)
- [Apache2 httpd](https://github.com/defo-project/apache-httpd)
- [nginx](https://github.com/defo-project/nginx)
- [lighttpd1.4](https://github.com/defo-project/lighttpd1.4)
- [haproxy](https://github.com/defo-project/haproxy)

In each case, the relevant CI build file is in
``.github/workflows/packages.yaml``. We've also added the ECH code to the
relevant ``master`` (or ``trunk``) branch of each of the above.

## packages.yaml

There is a lot in common across the various ``packages.yaml`` files, they each:

- define a ``builder`` workflow to be run on ``push`` or daily at 0530 UTC
- exit on any error
- re-use debian testing build tools (from @jspricke)
- attempt a ``git merge`` with the upstream for the relevant project
- build the relevant ECH-enabled repo resulting from the merge
- store built packages in a "pseudo" branch called ``packages``
- attempt a basic test using the scripts from this repo and those packages

The test scripts and configurations defined in this repo are used
in those tests. When running those as part of this CI setup, we set
an environment variable ``PACKAGING=1`` so the scripts and configs
can differ from the command line and CI environments, which is
sometimes useful.

## Heritage

Mostly, the ECH-enabled code in the various repos here was originally developed
under the equivalent fork in the ``sftcd`` github account.

The new CI scripting was initially added to these forks under the ``jspricke``
github account.

## Reacting to ``builder`` fails

When we see a failure with a ``builder`` workflow the general plan is to
do as follows:

- clone the repo to a new directory
- rebase that branch with upstream fixing any issues identified
- build and test
- force-push

While not the only way to do it, the recipe I'd follow for
the above when dealing with an issue in the ``apache-http``
repo would be:

- First, clone the repo and rebase with upstream:

```bash
$ cd $HOME/code
$ git clone git@github.com:defo-project/apache-httpd.git apache-httpd-rebase
$ cd apache-httpd-rebase
$ git remote add upstream https://github.com/apache/httpd.git
$ git fetch upstream
$ git rebase -i upstream/trunk trunk
... fix things that need fixing ...
```

- Next, follow our build/test howto for that repo, in this case
that'd be [here](apache2.md).
When running the test, you'll need to set the ``ATOP`` environment
variable to reflect the use of the ``apache-httpd-rebase``
directory, so:

```bash
$ cd $HOME/lt
$ ATOP=$HOME/code/apache-httpd-rebase/ $HOME/code/ech-dev-utils/scripts/testapache.sh
/home/user/lt
Executing: /home/user/code/apache-httpd-rebase//httpd -d /home/user/lt -f /home/user/code/ech-dev-utils/configs/apachemin.conf
Testing grease 9443
Testing public 9443
Testing real 9443
Testing hrr 9443
All good.
```

- Once all is well, you can force-push the repo and then
clean up:

```bash
$ cd $HOME/code/apache-httpd-rebase
$ git push -f
$ cd ..
$ rm -rf apache-httpd-rebase
```

Various names in the above will change for other repos of course.

