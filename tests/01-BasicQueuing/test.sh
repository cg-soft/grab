#!/bin/bash

# This only works within the framework, so invoke it if it isn't already present.
[ "$framework_loaded" != true ] && cd "$(dirname "$0")" && exec ../../runtest.sh 

host=127.0.0.1
port=1337

normalize_responses()
{
  sed -e 's/^\(            "[^"]*"\): [1-9][0-9]*/\1: timestamp/'\
      -e 's/\("uptime"\): [1-9][0-9]*/\1: uptime/'\
      -e 's/\("timestamp"\): [1-9][0-9]*/\1: timestamp/'\
      -e 's/\("port"\): "[1-9][0-9]*"/\1: "port"/'
}

begin_test BasicQueuing
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
  grep '^[^#]' "$test_path/urls.txt"\
    | while read id op resource comment
      do
        sleep 1
        echo "$comment" >> "$test_path"/actual.responses
        curl "http://$host":"$port/$resource""?op=$op""&id=$id" 2>/dev/null\
            | ./json.py test\
            | normalize_responses\
           >> "$test_path"/actual.responses
        echo "== After $op $resource by $id:" >> "$test_path"/actual.responses
        curl "http://$host":"$port/$resource""?op=dump""&id=$id" 2>/dev/null\
            | ./json.py test 2>/dev/null\
            | normalize_responses\
           >> "$test_path"/actual.responses
        echo "==" >> "$test_path"/actual.responses
      done
  normalized_diff "$test_path"/golden.responses\
                  "$test_path"/actual.responses\
   || fail_test BasicQueuing "responses differs from golden output" "see diff"
  sed -e "s/$port/port/g"\
      -e "s/until=[0-9]*/until=timestamp/g"\
    "$test_path"/actual.stdout > "$test_path"/actual.stdout.filtered
  normalized_diff "$test_path"/golden.stdout\
                  "$test_path"/actual.stdout.filtered\
   || fail_test BasicQueuing "stdout differs from golden output" "see diff"
  normalized_diff "$test_path"/golden.stderr\
                  "$test_path"/actual.stderr\
   || fail_test BasicQueuing "stderr differs from golden output" "see diff"
  kill $pid 2>/dev/null && fail_test BasicQueuing "service should shut down by itself" "kill succeeded"
end_test BasicQueuing
