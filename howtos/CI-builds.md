
# DEfO Project CI build/test setup

The goal of these continuuous integration (CI) builds and tests is to identify
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

## Heritge

Mostly, the ECH-enabled code in the various repos here was originally developed
under the equivalent fork in the ``sftcd`` github account.

The new CI scripting was initially added to these forks under the ``jspricke``
github account.

## Reacting to found issues

When we see a failure with a ``git merge`` the general plan is to
do as follows:

- clone your``development`` branch to a new local tree
- rebase that branch with upstream fixing any issues identified
- add the relevant ``defo-project`` repo as a new upstream 
- force-push to the defo-project repo

While not the only way to do it, the recipe I'd follow for
the above when dealing with an issue in the ``apache-http``
repo would be:

```bash
$ git clone git@github.com:sftcd/httpd.git httpd-rebase
$ cd httpd-rebase
$ git remote add upstream https://github.com/apache/httpd.git
$ git fetch upstream
$ git checkout trunk
$ git reset --hard upstream/trunk
$ git push origin trunk --force 
$ git checkout ECH-experimental
$ git rebase -i trunk ECH-experimental
... fix things...
$ git status
... see <to-be-fixed-thing> needs an edit...
... do the edit...
$ git add <to-be-fixed-thing>
$ git rebase --continue
... rinse/repeat 'till done ...
$ git push -f
$ git remote add defoprojectupstream git@github.com:defo-project/apache-httpd.git
$ git push defoprojectupstream ECH-experimental:trunk
$ cd ..
$ rm -rf httpd-rebase
```

Various names in the above will change in other cases of course.

