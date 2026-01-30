# TODO

- See also **TODOs** section in *README.md*.

- Use `#!/usr/bin/python3` on first line of executable Python scripts,
  as this is more usually where the interpreter is found. It is the
  standard location on Debian-like systems, and also on macOS.

- Correct invocation of `openssl ech` in *makeech.sh*, and
  correspondigly in *test_cases_gen.py* by using current CLI API, so
  as to avoid failure with a message like:
  
  `Can't read dt/echkeydir/ng/ng-pub.pem.ech - exiting`

---
