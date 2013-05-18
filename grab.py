#!/usr/bin/env python

import urllib2
import time
import sys
import os

GRAB_URL = 'http://127.0.0.1:1337/'
SLEEP = 30.0       # seconds
MAX_ATTEMPTS = 120 # 1 hour

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

`shutdown'
   Initiate soft shutdown. All new requests will be denied, all
   the existing requests will be allowed to time out or to be 
   released. Returns zero if service actually shuts down, non-
   zero if service is still holding on to locks.

Options are:

--help
   Displays this text

--owner
   Owner of the request

--max-attempts
   How often to attempt a request.

--sleep=<time>
   How long to sleep between polls

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

# Quick and dirty json rendering to avoid dependency on possibly missing python
# modules.

def parse(string):
    true = True
    false = False
    null = None
    return eval(string.strip())

def render(x, indent=0):
    if type(x) == type(""):
        return '"'+x.replace("\\", "\\\\")\
                    .replace("\"", "\\\"")\
                    .replace("\b", "\\b")\
                    .replace("\f", "\\f")\
                    .replace("\v", "\\v")\
                    .replace("\r", "\\r")\
                    .replace("\t", "\\t")\
                    .replace("\n", "\\n")+'"'

    if type(x) == type({}):
        keys = x.keys()
        if indent:
            keys.sort()
            content = (",\n"+' '*indent).join(['"'+str(key)+'": '+render(x[key], indent+2) for key in keys])
            if content:
                return "{\n"+' '*indent+content+' }'
            else:
                return "{}"
        else:
            return '{'+",".join(['"'+str(key)+'":'+render(x[key]) for key in keys])+'}'

    if type(x) == type([]) or type(x) == type(()):
        if indent:
            content = (",\n"+' '*indent).join([render(val, indent+2) for val in x])
            if content:
                return "[\n"+' '*indent+content+' ]'
            else:
                return "[]"
        else:
            return '['+','.join([render(val) for val in x])+']'

    if type(x) == type(2):
        return str(x)
    if x == None:
        return 'null'
    if x == True:
        return 'true'
    if x == False:
        return 'false'
    
    return render("%r" % x)

class Grab:
    def __init__(self, owner, url=GRAB_URL, sleep=SLEEP, max_attempts=MAX_ATTEMPTS, verbose=False):
        self.url = url
        self.owner = owner
        self.sleep = sleep
        self.max_attempts=MAX_ATTEMPTS
        self.verbose = verbose
        try:
             self.ppid = os.getppid()
        except:
             self.ppid = None

    def get(self, op, resource):
        url = self.url + resource + '?id=%s&op=%s' % (self.owner, op)
        try:
            req = urllib2.urlopen(url)
        except:
            if self.verbose:
                print >>sys.stderr, "Failed to urlopen", url
            return None
        if req:
            try:
                response = parse(req.read())
            except:
                if self.verbose:
                    print >>sys.stderr, "Unable to parse response:", response
                response = None
            req.close()
            return response 
        else:
            return None

    def poll(self, op, resource, keepalive):
        attempts = self.max_attempts
        while keepalive or attempts > 0:
            attempts -= 1
            # If invoking process dies, commit suicide
            if self.ppid is not None and os.getppid() != self.ppid:
                sys.exit()
            response = self.get(op, resource)
            if keepalive:
                if self.verbose:
                    print >>sys.stderr, "sleeping after getting response to keepalive:"
                    print >>sys.stderr, render(response, indent=2)
            else:
                if response is None:
                    return None
                if response.get('status') == 'ok':
                    return response
                if self.verbose:
                    print >>sys.stderr, "sleeping after getting non-ok:"
                    print >>sys.stderr, render(response, indent=2)
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
            if arg.startswith("--url="):
                grab_url = arg[len("--url="):]
                continue
            if arg.startswith("--max-attempts="):
                max_attempts = arg[len("--max-attempts="):]
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
            if arg in ('peek', 'grab', 'keepalive', 'release', 'shutdown', 'dump', 'config'):
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

    if op in ('peek', 'grab', 'release') and resource is None:
        usage("Must specify resource for %s." % op)
    elif resource is None:
        resource = ''

    if op == 'keepalive':
        op = 'grab'
        keepalive = True
    else:
        keepalive = False

    result = Grab(owner=owner,
                  url=grab_url,
                  sleep=sleep,
                  max_attempts=max_attempts,
                  verbose=verbose).poll(op, resource, keepalive)

    if verbose or op in ('config', 'dump'):
        if result is None:
            print >>sys.stderr, "None"
        else:
            print >>sys.stderr, render(result, indent=2)

    if op == 'peek' and result is not None:
        print result.get('data', {}).get('id')

    if op == 'shutdown':
        if result is None or result['status'] == 'ok':
            sys.exit(0)
        sys.exit(1)
    if result is None or result['status'] != 'ok':
        sys.exit(1)
    sys.exit(0)

