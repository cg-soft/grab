#!/bin/sh

# Created by Christian Goetze - http://blog.fortified-bikesheds.com/ - and released under
# the terms of the CC0 1.0 Universal legal code:
# 
# http://creativecommons.org/publicdomain/zero/1.0/legalcode

here="$(dirname "$0")"
logdir="$here"  # "$here/../log" is a good option too...
mkdir -p "$logdir"
sha1sum="$(sha1sum "$here/grab.js" | awk '{print $1}')"
"$here"/grab.py shutdown --verbose --hash="$sha1sum"
case $? in
  # shutdown returns 7 when hash matches with running process,
  # so no need to restart.
  7) exit 0 ;;
  0) rm -f "$logdir/log.3"
     mv "$logdir/log.2" "$logdir/log.3"
     mv "$logdir/log.1" "$logdir/log.2"
     mv "$logdir/log" "$logdir/log.1"
     nohup node "$here"/grab.js --hash="$sha1sum" "$@" >"$logdir/log" 2>&1 &
     echo $! > "$logdir"/pid
     retries=x
     while [ "$retries" != xxxxx ]
     do
       retries=x$retries
       sleep 1
       "$here"/grab.py config && exit 0
     done
     echo Failed to start grab daemon >&2
     exit 1 ;;
  *) echo Failed to stop grab daemon >&2
     exit 1 ;;
esac
