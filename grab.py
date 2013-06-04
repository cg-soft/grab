#!/usr/bin/env python

# Created by Christian Goetze - http://blog.fortified-bikesheds.com/ - and released under
# the terms of the CC0 1.0 Universal legal code:
# 
# http://creativecommons.org/publicdomain/zero/1.0/legalcode

import urllib2
import time
import sys
import os
import re
import subprocess

# Use our insecure eval() based json parser if the json module
# is unavailable.
try:
    from json import dumps, loads
except:
    from grab_json import dumps, loads
try:
    dumps({}, is_this_grab_json=1)
except:
    pass
else:
    print >>sys.stderr, "WARNING: This uses an insecure json module, please try to install python's standard json module."

GRAB_URL = 'http://127.0.0.1:1337/'
SLEEP = 30.0       # seconds
MAX_ATTEMPTS = 120 # 1 hour

# Support specifying durations
until_regexp = re.compile(r'(\d+)([smhdw])')
until_unit = { 's': 1, 'm': 60, 'h': 3600, 'd': 24*3600, 'w': 7*24*3600 }

def usage(error=""):
    print >>sys.stderr, """Usage:

%s <op> [<resource>] [<options>]

Poll lock service to obtain a resource. The resource can be 
any alphanumeric string no longer than 100 characters.

Operations are:

`grab'
   Attempt to obtain a lock on a resource. If the attemp succeeds,
   error code is zero, otherwise it's the number of requests in the
   queue.

`keepalive'
   Runs "grab" forever, until killed or until the parent process dies.

`release'
   Free resource, or cancel request for a resource. Always succeeds.

`config'
   Dump config of the lock service.

`dump'
   Dump current state of the lock service.

`peek'
   Check who is hogging the resource.

`stats'
   Dump statistics

`shutdown'
   Initiate soft shutdown. All new requests will be denied, all
   the existing requests will be allowed to time out or to be 
   released. Returns zero if service actually shuts down, non-
   zero if service is still holding on to locks.

Options are:

--help
   Displays this text

--hash
   Used in conjunction with "shutdown" to check whether a shutdown
   is required. Specify the sha1sum or md5sum of the new grab.js file,
   and this will be compared to the value stored in the config of the
   running grab.js daemon.

--max-attempts
   How often to attempt a request.

--owner
   Owner of the request

--ppid
   Parent process id. On unix systems, this will be determined automatically.
   On windows systems, it should be passed in, since it is easier to find out
   that way.

--sleep=<time>
   How long to sleep between polls

--until=<duration>
   How long to keep the lock. Durations can be expressed by a string of integer+unit
   combinations. Possible units are seconds (s), minutes(m), hours(h), days(d) and
   weeks(w). Units can be combined, for example 2w3d means 2 weeks and 3 days.
   The default duration is "None", which means the lock needs to be refreshed within
   the time period configured in the grab server, usually one minute. This option
   essentially lets you set an expiration date in the future, so you do not need
   to run a keepalive process if you know you want the resource to be locked for
   at least the given duration.

--url
   Url of lock service

--verbose
   Show all requests and responses

""" % sys.argv[0]

    if error:
        print >>sys.stderr, error
        sys.exit(-1)
    else:
        sys.exit(0)

def IsProcessRunning(processId):
    # On Windows, we need to do this....
    ps = subprocess.Popen('tasklist.exe /NH /FI "PID eq %d"' % processId, shell=True, stdout=subprocess.PIPE)
    output = ps.stdout.read()
    ps.stdout.close()
    ps.wait()
    if str(processId) in output:
        return True
    return False

class Grab:
    def __init__(self, owner, url=GRAB_URL, sleep=SLEEP, max_attempts=MAX_ATTEMPTS, verbose=False, ppid=None):
        self.url = url
        self.owner = owner
        self.sleep = sleep
        self.max_attempts=max_attempts
        self.verbose = verbose
        self.max_wait = int(time.time()*1000) + max_attempts*sleep*1000
        if ppid is None:
            try:
                self.ppid = os.getppid()
            except:
                self.ppid = None
        else:
            self.ppid = ppid

    def get(self, op, resource="", until=None):
        url = self.url + resource + '?id=%s&op=%s' % (self.owner, op)
        if until is not None:
            url += '&until=%d' % until
        if self.verbose:
            print >>sys.stderr, "GET", url
        try:
            req = urllib2.urlopen(url)
        except:
            if self.verbose:
                print >>sys.stderr, "Failed to urlopen", url
            return None
        if req:
            try:
                response = loads(req.read())
            except:
                if self.verbose:
                    print >>sys.stderr, "Unable to parse response:", response
                response = None
            req.close()
            return response 
        else:
            return None

    def poll(self, op, resource, until, keepalive):
        attempts = self.max_attempts
        while keepalive or attempts > 0:
            attempts -= 1
            # If invoking process dies, commit suicide
            if self.ppid is not None:
                if os.name == 'nt':
                    # On windows, use the windows process check
                    if not IsProcessRunning(self.ppid):
                        if self.verbose:
                            print >>sys.stderr, "Parent process died, shutting down"
                        sys.exit()
                elif os.getppid() != self.ppid:
                    if self.verbose:
                        print >>sys.stderr, "Parent process died, shutting down"
                    sys.exit()
            response = self.get(op, resource, until)
            if keepalive:
                if self.verbose:
                    print >>sys.stderr, "sleeping after getting response to keepalive:"
                    print >>sys.stderr, dumps(response, indent=2, sort_keys=True, separators=(',',': '))
            else:
                if response is None:
                    return None
                if response.get('status') == 'ok':
                    return response
                if self.max_wait is not None:
                    if response.get('data', {'until': 0}).get('until', 0) > self.max_wait:
                        if self.verbose:
                            print >>sys.stderr, "exiting after being told the delay would exceed my maximum wait time"
                        return None
                        
                if self.verbose:
                    print >>sys.stderr, "sleeping after getting non-ok:"
                    print >>sys.stderr, dumps(response, indent=2, sort_keys=True, separators=(',',': '))
            time.sleep(self.sleep)
        return None

if __name__ == '__main__':

    parse_options = True
    test_run = False
    verbose = False
    owner = 'someone'
    max_attempts = MAX_ATTEMPTS
    sleep = SLEEP
    grab_url = GRAB_URL
    op = None
    resource = None
    sha1sum = None
    ppid = None
    until = None
    for arg in sys.argv[1:]:
        if parse_options:
            if arg in ("-h", "--help"):
                usage()
            if arg in ("--test",):
                test_run = True
                continue
            if arg in ("--verbose",):
                verbose = True
                continue
            if arg.startswith("--hash="):
                sha1sum = arg[len("--hash="):]
                continue
            if arg.startswith("--url="):
                grab_url = arg[len("--url="):]
                continue
            if arg.startswith("--max-attempts="):
                max_attempts = arg[len("--max-attempts="):]
                continue
            if arg.startswith("--ppid="):
                ppid = arg[len("--ppid="):]
                continue
            if arg.startswith("--until="):
                until = arg[len("--until="):]
                continue
            if arg.startswith("--sleep="):
                sleep = arg[len("--sleep="):]
                continue
            if arg.startswith("--owner="):
                owner = arg[len("--owner="):]
                continue
            if arg == "--":
                parse_options = False
                continue
            if arg.startswith("--"):
                usage("Unknown option: %s." % arg)
        if op is None:
            if arg in ('peek', 'grab', 'keepalive', 'release', 'shutdown', 'dump', 'stats', 'config'):
                op = arg
            else:
                usage("Unknown operation: %s." % arg)
        elif resource is None:
            if len(arg) < 101 and arg.replace('/','').isalnum():
                resource = arg
            else:
                usage("Resource name must be alphanumeric and shorter than 100 chars:\n    %s" % arg)
        else:
            usage("Unrecognized argument: %s." % arg)
    if op is None:
        usage("Must specify op")

    if not owner.isalnum():
        usage("Value for --owner must be alphanumeric: %s." % owner)

    if ppid is not None:
        try:
            ppid = int(ppid)
        except:
            usage("--ppid=<n> must be an integer")

    if until is not None:
        offset = 0
        ok = False
        for count, unit in until_regexp.findall(until):
            offset += int(count)*until_unit[unit]
            ok = True
        if not ok:
            usage("--until=<time> must be a duration expressed in <n>{s|m|h|d|w}")
        until = int(time.time()*1000) + offset*1000

    if op in ('peek', 'grab', 'release') and resource is None:
        usage("Must specify resource for %s." % op)
    elif resource is None:
        resource = ''

    if op == 'keepalive':
        op = 'grab'
        keepalive = True
    else:
        keepalive = False

    grab = Grab(owner=owner,
                url=grab_url,
                sleep=sleep,
                ppid=ppid,
                max_attempts=max_attempts,
                verbose=verbose)

    if op == 'shutdown':
        config = grab.get("config")    
        if config is not None and sha1sum is not None:
            old_sha1sum = config.get('data',{}).get('hash')
            if verbose:
                print >>sys.stderr, "Old sha1sum: %s\nNew sha1sum: %s" % (old_sha1sum, sha1sum)
            if old_sha1sum == sha1sum:
                print "No restart required, running service matches specified --hash string"
                sys.exit(0)

    result = grab.poll(op, resource, until, keepalive)

    if verbose or op in ('config', 'stats', 'dump'):
        if result is None:
            print >>sys.stderr, "None"
        else:
            print >>sys.stderr, dumps(result, indent=2, sort_keys=True, separators=(',',': '))

    if op == 'peek' and result is not None:
        print result.get('data', {}).get('id')

    if op == 'shutdown':
        if result is None or result['status'] == 'ok':
            sys.exit(0)
        sys.exit(1)
    if result is None or result['status'] != 'ok':
        if op == 'grab':
            if verbose:
                print >>sys.stderr, "Releasing", resource
            grab.get('release', resource)
        sys.exit(1)
    sys.exit(0)

