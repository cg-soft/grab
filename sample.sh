#!/bin/bash

# Created by Christian Goetze - http://blog.fortified-bikesheds.com/ - and released under
# the terms of the CC0 1.0 Universal legal code:
# 
# http://creativecommons.org/publicdomain/zero/1.0/legalcode

here="$(dirname "$0")"
owner=$(whoami)

grab()
{
  local resource="$1"
  echo "Waiting for $resource"
  if "$here"/grab.py\
     --verbose\
     --owner="$owner"\
     grab "$resource"
  then
    echo Grabbed - Starting keepalive
    "$here"/grab.py\
     --verbose\
     --owner="$owner"\
     keepalive "$resource" >"$here"/keepalive.log 2>&1 &
     export keepalive_pid=$!
  elif "$here"/grab.py\
    --verbose\
    --owner="$owner"\
    dump
  then
    echo "Resource $resource is being hogged"
    return 1
  else
    echo "Failed to grab resource $resource; Grab Daemon down?"
    return 1
  fi
  echo "Done waiting for $resource"
}

release()
{
  local resource="$1"
  echo "Releasing $resource"
  if [ -n "$keepalive_pid" ] && ps "$keepalive_pid"
  then
    # unconditionally kill it dead, it isn't doing anything stateful
    kill -9 "$keepalive_pid"
    echo "Keepalive log"
    cat "$here"/keepalive.log
  elif [ -r "$here"/keepalive.log ]
  then
    echo Keepalive died on its own
    cat "$here"/keepalive.log
  else
    echo No keepalive process used
  fi
  rm -f "$here"/keepalive.log
  if "$here"/grab.py\
     --verbose\
     --owner="$owner"\
     release "$resource"
  then
    echo Released
  elif "$here"/grab.py\
    --verbose\
    --owner="$owner"\
    dump
  then
    echo "Failed to release resource $resource"
    return 1
  else
    echo "Failed to release resource $resource; Grab Daemon down?"
    return 1
  fi
  echo "Done releasing $resource"
}

grab path/to/my/resource || exit 1
# Do something with it
sleep 10
echo doing...
sleep 10
echo doing...
sleep 10
echo doing...
sleep 10
echo done.
release path/to/my/resource || exit 1

