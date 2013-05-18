#!/bin/sh

here="$(dirname "$0")"
logdir="$here"  # "$here/../log" is a good option too...
mkdir -p "$logdir"
if "$here"/grab.py shutdown --verbose
then
  rm -f "$logdir/log.3"
  mv "$logdir/log.2" "$logdir/log.3"
  mv "$logdir/log.1" "$logdir/log.2"
  mv "$logdir/log" "$logdir/log.1"
  nohup node "$here"/grab.js "$@" >"$logdir/log" 2>&1 &
  echo $! > "$logdir"/pid
  retries=x
  while [ "$retries" != xxxxx ]
  do
    retries=x$retries
    sleep 1
    "$here"/grab.py config && exit 0
  done
  echo Failed to start grab daemon >&2
  exit 1
else
  echo Failed to stop grab daemon >&2
  exit 1
fi
