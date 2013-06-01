#!/usr/bin/env python

# Created by Christian Goetze - http://blog.fortified-bikesheds.com/ - and released under
# the terms of the CC0 1.0 Universal legal code:
# 
# http://creativecommons.org/publicdomain/zero/1.0/legalcode

# Quick and dirty json rendering.
#
# WARNING: this uses eval(), so is not secure and should not be used with untrusted input
#
# This module is supplied just in case your python does not have the "json" module, and 
# it provides the loads() and dumps() functions with similar signatures.

def loads(string):
    true = True
    false = False
    null = None
    return eval(string.strip())

def dumps(x, indent=0, sort_keys=False, separators=(',',':'), current_indent=0, is_this_grab_json=0):
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
        if sort_keys:
            keys.sort()
        if indent:
            content = (separators[0]+"\n  "+' '*current_indent).join(['"'+str(key)+'"'+separators[1]+dumps(x[key], indent, sort_keys, separators, current_indent+indent) for key in keys])
            if content:
                return "{\n  "+' '*current_indent+content+"\n"+' '*current_indent+'}'
            else:
                return "{}"
        else:
            return '{'+separators[0].join(['"'+str(key)+'"'+separators[1]+dumps(x[key], 0, sort_keys, separators) for key in keys])+'}'

    if type(x) == type([]) or type(x) == type(()):
        if indent:
            content = (separators[0]+"\n  "+' '*current_indent).join([dumps(val, indent, sort_keys, separators, current_indent+indent) for val in x])
            if content:
                return "[\n  "+' '*current_indent+content+"\n"+' '*current_indent+']'
            else:
                return "[]"
        else:
            return '['+separators[0].join([dumps(val, 0, sort_keys, separators) for val in x])+']'

    if type(x) == type(2):
        return str(x)
    if x == None:
        return 'null'
    if x == True:
        return 'true'
    if x == False:
        return 'false'
    
    return dumps("%r" % x, indent, sort_keys, separators, current_indent)

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
    print json.dumps({"some": "json", "structure": ["with", "stuff", "..."]})

A very simple json renderer.
""" % sys.argv[0]
        sys.exit(0)

    json = loads(sys.stdin.read())
    print dumps(json, indent=indent, sort_keys=True, separators=(',',': '))
