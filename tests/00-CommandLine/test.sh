#!/bin/bash

# This only works within the framework, so invoke it if it isn't already present.
[ "$framework_loaded" != true ] && cd "$(dirname "$0")" && exec ../../runtest.sh 

host=127.0.0.1
port=1337

begin_test CommandLine
  node grab.js --help\
    2> "$test_path"/actual.stderr \
     | sed 's/timestamp=.*/timestamp=timestamp/'\
     > "$test_path"/actual.stdout
 
  [ ${PIPESTATUS[0]} -eq 0 ] || fail_test CommandLine "non-zero return code" "expected 0"

  node grab.js --unknown-option --debug --another-unknown-option\
    2>> "$test_path"/actual.stderr \
     | sed 's/timestamp=.*/timestamp=timestamp/'\
     >> "$test_path"/actual.stdout

  [ ${PIPESTATUS[0]} -eq 2 ] || fail_test CommandLine "zero return code" "expected 2"

  normalized_diff "$test_path"/golden.stdout\
                  "$test_path"/actual.stdout\
   || fail_test CommandLine "stdout differs from golden output" "see diff"

  normalized_diff "$test_path"/golden.stderr\
                  "$test_path"/actual.stderr\
   || fail_test CommandLine "stderr differs from golden output" "see diff"
end_test CommandLine
