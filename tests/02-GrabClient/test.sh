#!/bin/bash

# This only works within the framework, so invoke it if it isn't already present.
[ "$framework_loaded" != true ] && cd "$(dirname "$0")" && exec ../../runtest.sh 

host=127.0.0.1
port=1337
url=http://$host:$port/

begin_test GrabCLient
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
  # Ensure we're not using our own json module
  rm -f json.py*
  grep '^[^#]' "$test_path/args.txt"\
    | while read id op resource until rc comment
      do
        sleep 1
        echo "$comment" >> "$test_path"/actual.responses
        ./grab.py --url=$url --owner=$id --until=$until --verbose $op $resource \
           >> "$test_path"/actual.responses 2>&1
        echo "rc = $PIPESTATUS; expected $rc" >> "$test_path"/actual.responses
        echo "== After $op $resource by $id:" >> "$test_path"/actual.responses
        ./grab.py --url=$url --owner=$id --verbose dump \
           >> "$test_path"/actual.responses 2>&1
        echo "==" >> "$test_path"/actual.responses
      done
  kill $pid 2>/dev/null && fail_test GrabCLient "service should shut down by itself" "kill succeeded"
  # Now inject our own json, just to test it too
  node grab.js\
         --debug\
         --timeout=1000000\
         --gc_interval=1000000\
         --host=$host\
         --port=$port\
     >>"$test_path"/actual.stdout \
    2>>"$test_path"/actual.stderr &
  pid=$!
  cp grab_json.py json.py
  export PYTHON_PATH=.
  echo "== Now with our own json.py ==" >> "$test_path"/actual.responses
  grep '^[^#]' "$test_path/args.txt"\
    | while read id op resource until rc comment
      do
        sleep 1
        echo "$comment" >> "$test_path"/actual.responses
        ./grab.py --url=$url --owner=$id --until=$until --verbose $op $resource \
           >> "$test_path"/actual.responses 2>&1
        echo "rc = $PIPESTATUS; expected $rc" >> "$test_path"/actual.responses
        echo "== After $op $resource by $id:" >> "$test_path"/actual.responses
        ./grab.py --url=$url --owner=$id --verbose dump \
           >> "$test_path"/actual.responses 2>&1
        echo "==" >> "$test_path"/actual.responses
      done
  # Remove injection
  rm -rf json.py*

  # Normalize
  sed -e 's/^\(            "[^"]*"\): [1-9][0-9]*/\1: timestamp/'\
      -e "s/until=[0-9]*/until=timestamp/g"\
      -e '/^WARNING:/d'\
      -e "s/$host:$port/host:port/g"\
      -e 's/\(uptime"\): [1-9][0-9]*/\1: uptime/'\
      -e 's/\(until"\): [1-9][0-9]*/\1: until/'\
      -e 's/\(timestamp"\): [1-9][0-9]*/\1: timestamp/'\
      -e 's/\(port"\): "[1-9][0-9]*"/\1: "port"/'\
    "$test_path"/actual.responses > "$test_path"/actual.responses.filtered
  normalized_diff "$test_path"/golden.responses\
                  "$test_path"/actual.responses.filtered\
   || fail_test GrabCLient "responses differs from golden output" "see diff"

  sed -e "s/$port/port/g"\
      -e "s/until=[0-9]*/until=timestamp/g"\
    "$test_path"/actual.stdout > "$test_path"/actual.stdout.filtered
  normalized_diff "$test_path"/golden.stdout\
                  "$test_path"/actual.stdout.filtered\
   || fail_test GrabCLient "stdout differs from golden output" "see diff"

  normalized_diff "$test_path"/golden.stderr\
                  "$test_path"/actual.stderr\
   || fail_test GrabCLient "stderr differs from golden output" "see diff"

  kill $pid 2>/dev/null && fail_test GrabCLient "service should shut down by itself" "kill succeeded"
end_test GrabCLient
