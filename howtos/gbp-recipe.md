# A recipe for handling builder CI failures with patches

From time to time we see CI failures due to a mismatch between
the upstream repo (after merging with our ECH code) and the
set of debian patches used in our CI builds. The following 
recipe can be used to update the debian patches to the most
recent ones, which resolves a bunch of these issues.

The most recent such case happened with haproxy, so the
commands below were usable to resolve that. The same
recipe should work for other upstreams.

```bash
# goto wherever you keep the defo-project haproxy code
$ cd $HOME/code/defo-project-org/haproxy
# update that
$ git pull
# make sure you're on the master or main branch
$ git checkout master
# fetch latest upstram commits
$ git fetch upstream
# rebase with the upstream master (assumes that remote was added)
# if you have to fix merge issues, do that here, we assume it works
# for now
$ git rebase upstream/master 
# now use `gbp` to fetch latest debian patches, you might 
# need to increase the 50
# when done, this lands us in another branch, called patch-queue/master
$ gbp pq import --time-machine=50
# rebase patch-queue/master with master
$ git rebase master 
# we may need to fix something to get the rebase to work, in 
# the current case we had to...
$ git status
$ vi admin/systemd/haproxy.service.in 
$ git add admin/systemd/haproxy.service.in 
$ git rebase --continue 
# when the rebase has worked, we want to get those changes back
# into the master branch
$ gbp pq export
# the above pops us back to the master branch, but no harm checking...
$ git status
# the status here should show us the changed files in debian/patches
# so add those back
$ git add .
# commit those
$ git commit -am 'debian patches updated'
# you should build and test that things work
# finally push back to github
$ git push -f
```


