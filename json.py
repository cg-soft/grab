#!/usr/bin/env python

# Created by Christian Goetze - http://blog.fortified-bikesheds.com/ - and released under
# the terms of the CC0 1.0 Universal legal code:
# 
# http://creativecommons.org/publicdomain/zero/1.0/legalcode

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

if __name__ == '__main__':
    import sys
    if len(sys.argv) == 2 and sys.argv[1] == 'test':
        run_test = True 
        indent = 2
    elif len(sys.argv) == 1:
        run_test = False
        indent = 0
    else:
        print """Usage:

  from the command line:

    %s < json_to_validate

  from a script:

    import json
    print json.render({"some": "json", "structure": ["with", "stuff", "..."]})

A very simple json renderer.
""" % sys.argv[0]
        sys.exit(0)

    json = parse(sys.stdin.read())
    print render(json, indent)
