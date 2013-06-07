#!/bin/bash

# This only works within the framework, so invoke it if it isn't already present.
[ "$framework_loaded" != true ] && cd "$(dirname "$0")" && exec ../../runtest.sh 

host=127.0.0.1
port=1337

begin_test StaticContent
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
    | while read resource comment
      do
        sleep 1
        echo "$comment" >> "$test_path"/actual.responses
        curl -D - "http://$host":"$port/$resource"\
            | sed 10q\
           >> "$test_path"/actual.responses
        echo "==" >> "$test_path"/actual.responses
      done

  # Normalize output
  sed -e "s/$port/port/g"\
      -e "s/^Date: .*/Date: date/"\
    "$test_path/actual.responses" > "$test_path/actual.responses.filtered"
  normalized_diff "$test_path"/golden.responses\
                  "$test_path"/actual.responses.filtered\
   || fail_test StaticContent "responses differs from golden output" "see diff"

  sed -e "s/$port/port/g"\
    "$test_path"/actual.stdout > "$test_path"/actual.stdout.filtered

  normalized_diff "$test_path"/golden.stdout\
                  "$test_path"/actual.stdout.filtered\
   || fail_test StaticContent "stdout differs from golden output" "see diff"

  normalized_diff "$test_path"/golden.stderr\
                  "$test_path"/actual.stderr\
   || fail_test StaticContent "stderr differs from golden output" "see diff"

  kill $pid || fail_test StaticContent "service should not crash" "kill failed"
end_test StaticContent
