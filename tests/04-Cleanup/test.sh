#!/bin/bash

# This only works within the framework, so invoke it if it isn't already present.
[ "$framework_loaded" != true ] && cd "$(dirname "$0")" && exec ../../runtest.sh 

host=127.0.0.1
port=1337
url=http://$host:$port/

begin_test Cleanup
  node grab.js\
         --debug\
         --timeout=1000000\
         --gc_interval=1000000\
         --host=$host\
         --port=$port\
     > "$test_path"/actual.stdout \
    2> "$test_path"/actual.stderr &
  pid=$!
 
  cp /dev/null "$test_path"/actual.responses
  cp /dev/null "$test_path"/actual_cleanup.log
  cp /dev/null "$test_path"/actual_keepalive.log

  # First do a complete run
  testpath="$test_path" sh sample.sh >> "$test_path"/actual.responses 2>&1
  
  # Now do a partial run and kill it
  testpath="$test_path" sh sample.sh >> "$test_path"/actual.responses 2>&1 &
  build_pid=$!
  sleep 40
  kill $build_pid
  sleep 40
  
  for f in .responses .stdout .stderr _keepalive.log _cleanup.log
  do
    # Normalize
    sed -e 's/^\(            "[^"]*"\): [1-9][0-9]*/\1: timestamp/'\
        -e "s/until=[0-9]*/until=timestamp/g"\
        -e '/^WARNING:/d'\
        -e '/illed:/d'\
        -e 's/\(uptime"\): [1-9][0-9]*/\1: uptime/'\
        -e 's/\(until"\): [1-9][0-9]*/\1: until/'\
        -e 's/\(timestamp"\): [1-9][0-9]*/\1: timestamp/'\
        -e 's/\(port"\): "[1-9][0-9]*"/\1: "port"/'\
        -e "s/$host:$port/host:port/g"\
      "$test_path"/actual$f > "$test_path"/actual$f.filtered
    normalized_diff "$test_path"/golden$f\
                    "$test_path"/actual$f.filtered\
     || fail_test Cleanup "actual$f differs from golden$f" "see diff"
  done
  kill $pid >/dev/null 2>&1 || fail_test Cleanup "service should be left running" "kill failed"
end_test Cleanup
