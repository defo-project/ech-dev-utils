# TODO

- See also **TODOs** section in *README.md*.

- Invoke utility script *makeech.sh* directly using available
  API options to capture/hide unwanted output, rather than 
  using **bash** as an intermediate wrapper.

- Determine whether deletion of a DNS node using NSUPDATE
  has any effect on child nodes, and consider whether code
  needs revision on account of findings.

- Support additional domain name hierarchies.

- Consider using external configuration file instead of 
  coding configuration in companion Python module.

# DONE

- Use `#!/usr/bin/python3` on first line of executable Python scripts,
  as this is more usually where the interpreter is found. It is the
  standard location on Debian-like systems, and also on macOS.

- Correct invocation of `openssl ech` in *makeech.sh*, and
  correspondigly in *test_cases_gen.py* by using current CLI API, so
  as to avoid failure with a message like:
  
  `Can't read dt/echkeydir/ng/ng-pub.pem.ech - exiting`

---
