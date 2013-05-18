#!/bin/sh

# Created by Christian Goetze - http://blog.fortified-bikesheds.com/ - and released under
# the terms of the CC0 1.0 Universal legal code:
# 
# http://creativecommons.org/publicdomain/zero/1.0/legalcode

# Usage:
#   ./runtest.sh <path-to-test-dir>

# The idea of this script is to give developers a quick and easy way to
# run individual tests or test suites. Note that individual tests can be
# run directly from within their test.sh, which has a line to check for
# "framework_loaded" and re-exec this script.

here="$(cd "$(dirname "$0")" && pwd)"
pwd="$(pwd | sed "s,^$here/,,")"

cd "$here"
export framework_loaded=true
export succeeded=true
export allow_sections=true
export status_unset=true

# These are TeamCity service messages... not sure whether Jenkins supports
# something similar. It produces structured build logs in TeamCity.

echo_service_message()
{
  echo "##teamcity[$@]"
}

begin_section()
{
  $allow_sections && echo_service_message blockOpened name="'$1'"
}

end_section()
{
  $allow_sections && echo_service_message blockClosed name="'$1'"
}

begin_suite()
{
  $allow_sections && echo_service_message testSuiteStarted name="'$1'"
}

end_suite()
{
  $allow_sections && echo_service_message testSuiteFinished name="'$1'"
  allow_sections=true
}

begin_test()
{
  echo_service_message testStarted name="'$1'" captureStandardOutput="'${2:-true}'"
  allow_sections=false
}

end_test()
{
  echo_service_message testFinished name="'$1'"
  allow_sections=true
}

fail_test()
{
  echo_service_message testFailed name="'$1'" message="'$2'" details="'$3'"
  succeeded=false
}

ignore_test()
{
  echo_service_message testIgnored name="'$1'" message="'$2'"
}

sorted_normalized_diff()
{
  sed -e 's,tests/[0-9][0-9]-[^/]*/[0-9][0-9]-[^/]*/,testdata/,g'\
      -e "s,`pwd`,%here%,g"\
    "$2" | sort > "$2".normalized
  diff -w "$1" "$2".normalized
}

normalized_diff()
{
  sed -e 's,tests/[0-9][0-9]-[^/]*/[0-9][0-9]-[^/]*/,testdata/,g'\
      -e "s,`pwd`,%here%,g"\
    "$2" > "$2".normalized
  diff -w "$1" "$2".normalized
}

run_tests()
{
  cd "$here"
  while [ "$1" ]
  do
    case "$1" in
    */*/test.sh) tests="'$1'";;
    */*/) tests="'$1'test.sh";;
    */) tests="'$1'*/test.sh";;
    */*) tests="'$1'/test.sh";;
    *) tests="'$1'/*/test.sh";;
    esac

    for test in `eval "ls $tests 2>/dev/null"`
    do
      test_path=$(dirname "$test")
      . "$test" || succeeded=false
    done
    shift
  done
}

if [ "$1" ]
then
  run_tests "$@"
elif [ -x "$pwd/test.sh" ]
then
  test_path="$pwd"
  . "$pwd/test.sh" || succeeded=false
else
  run_tests tests
fi

$succeeded\
 && echo "Tests passed."\
 || echo "Some tests failed."
$succeeded
