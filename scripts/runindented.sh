#!/bin/bash

# Found on stackexchange, not currently using it, but keeping it around
# for a while may be useful

run_indented() {
  local indent=${INDENT:-"    "}
  local indent_cmdline=(awk '{print "'"$indent"'" $0}')

  if [ -t 1 ] && command -v unbuffer >/dev/null 2>&1; then
    { unbuffer "$@" 2> >("${indent_cmdline[@]}" >&2); } | "${indent_cmdline[@]}"
  else
    { "$@" 2> >("${indent_cmdline[@]}" >&2); } | "${indent_cmdline[@]}"
  fi
}

INDENT="  " run_indented echo "hello"
run_indented echo "world"

