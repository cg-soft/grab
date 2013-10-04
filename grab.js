/* grab.js

Created by Christian Goetze - http://blog.fortified-bikesheds.com/ - and released under
the terms of the CC0 1.0 Universal legal code:

http://creativecommons.org/publicdomain/zero/1.0/legalcode

*/

var http = require('http');
var url = require('url');
var fs = require('fs');
var path = require('path');

var config = { 'help': false,
               'timestamp': new Date().getTime(),
               'hash': '',
               'static_content': './static',
               'version': "VERSION",
               'debug': false,
               'port': 1337,
               'host': '127.0.0.1',
               'gc_interval':   10000,  // 10 seconds
               'timeout':       60000   //  1 minute
             };

var stats = { 'uptime': 0,
              'total': 0,
              'max_queue_length': 0,
              'max_queue_resource': null,
              'max_queue_owner': null,
              'by_owner': {},
              'by_lock': {} };

// For serving the static web UI pieces
var mime_types = { '.js':   'text/javascript',
                   '.css':  'text/css',
                   '.ico':  'image/x-icon',
                   '.html': 'text/html' };

/* Note that we spend the time to do server validation of
 * the owner and resource parameters, because otherwise it
 * is easy to create confusion by using "smart" owner names.
 * We do use a trick to append the resource to the owner name
 * in order to uniquely identify locks. This could be perverted
 * if we allowed "/" in an owner name.
 */
var resource_regexp = new RegExp('^[._a-z0-9A-Z/]+$');
var owner_regexp = new RegExp('^[._a-z0-9A-Z]+$');

var queues = {};
var shutdown_pending = false;
var shutdown = false;

var errors = 0;
process.argv.forEach(function (val, index, array) {
  var arg = val.match(/^--([^=]*)(=(.*))?/);
  if (arg && arg[1] in config) {
    config[arg[1]] = arg[2] ? arg[3] : true;
  } else if (index > 1) {
    errors++;
    console.log("Unrecognized argument: "+val);
  }
});

if (errors || config.help) {
  for (var c in config) console.log('--'+c+'='+config[c]);
  process.exit(errors);
}

function is_empty(obj)
{
  for (var prop in obj) if (obj.hasOwnProperty(prop)) return false;
  return true;
}

function keys(obj)
{
  var keys = [];
  for (var prop in obj) if (obj.hasOwnProperty(prop)) keys.push(prop);
  return keys;
}

function register_stats(resource, owner)
{
  stats.total ++;
  if (owner in stats.by_owner) {
    stats.by_owner[owner]++;
  } else {
    stats.by_owner[owner] = 1;
  }
  if (resource in stats.by_lock) {
    stats.by_lock[resource]++;
  } else {
    stats.by_lock[resource] = 1;
  }
  if (queues[resource].getLength() > stats.max_queue_length) {
    stats.max_queue_length = queues[resource].getLength();
    stats.max_queue_resource = resource;
    stats.max_queue_owner = owner;
  }
}

/*

Queue.js

A function to represent a queue

Created by Stephen Morley - http://code.stephenmorley.org/ - and released under
the terms of the CC0 1.0 Universal legal code:

http://creativecommons.org/publicdomain/zero/1.0/legalcode

*/

/* Creates a new queue. A queue is a first-in-first-out (FIFO) data structure -
 * locks are added to the end of the queue and removed from the front.
 */

/* This is inlined and adapted for use here, as the functions now assume
 * some metadata to be present in the queued locks:
 *  "owners": {}     // hash of owners - each owner has own timestamp,
 *                   // or timestamp zero upon release
 *  "exes": {}       // hash of expired/released owners (for logging)
 *  "shared": bool   // exclusive or shared lock
 */

Queue = function (){

  // initialise the queue and offset
  var queue  = [];
  var offset = 0;

  /* Returns the length of the queue.
   */
  this.getLength = function(){

    // return the length of the queue
    return (queue.length - offset);

  }

  /* Returns true if the queue is empty, and false otherwise.
   */
  this.isEmpty = function(){

    // return whether the queue is empty
    return (queue.length == 0);

  }

  /* Enqueues the specified lock.
   */
  this.enqueue = function(resource, owner, timestamp, shared){

    // First check if lock is already in queue, if yes, update it.
    for (var i = offset; i < queue.length; i++) {
      // We own this lock, so update or remove ourselves from it
      if (owner in queue[i].owners) {
        if (config.debug) console.log("Found "+owner+" at "+resource+"["+i+"]");
        if (timestamp === 0) { 
          delete queue[i].owners[owner];
          queue[i].exes[owner] = 1
          return 0;
        } 
        queue[i].owners[owner] = timestamp;
        if (timestamp > queue[i].max_timestamp) queue[i].max_timestamp = timestamp;
        return (i - offset + 1);
      } 
      // We want a shared lock, and this is a shared lock at
      // the end of the queue, so re-use it.
      if (shared && queue[i].shared && i+1 === queue.length) {
        // arguably, this case shouldn't happen: we request a shared
        // lock with timestamp 0, which means we are actually releasing a
        // resource we never claimed. No harm done, but weird.
        if (timestamp === 0) {
          queue[i].exes[owner] = 1
          return 0;
        }
        if (config.debug) console.log("Merging "+owner+" at end of "+resource);
        register_stats(resource, owner);
        queue[i].owners[owner] = timestamp;
        if (timestamp > queue[i].max_timestamp) queue[i].max_timestamp = timestamp;
        return (i - offset + 1);
      }
    }

    // enqueue the new lock
    if (timestamp > 0) {
      if (config.debug) console.log("Adding "+owner+" to end of "+resource);
      var q = { "owners": {}, "exes": {}, "shared": shared, "max_timestamp": timestamp };
      q.owners[owner] = timestamp;
      queue.push(q);
      register_stats(resource, owner);
    }
    return queue.length - offset;
  }

  /* Tests if front lock in queue is expired
   */
  this.expired = function(now, timeout){

    // If queue is empty, nothing can be expired
    if (queue.length == 0) return false;

    // store the lock at the front of the queue
    var lock = queue[offset];

    // now test if lock really should be dequeued
    for (var owner in lock.owners) {
      if (lock.owners.hasOwnProperty(owner) && now - lock.owners[owner] < timeout) return false;
    }

    // all ids appear to be expired
    return true;
  }

  /* Dequeues an lock and returns it. If the queue is empty then undefined is
   * returned. 
   */
  this.dequeue = function(){

    // if the queue is empty, return undefined
    if (queue.length == 0) return undefined;

    // store the lock at the front of the queue
    var lock = queue[offset];

    // increment the offset and remove the free space if necessary
    if (++ offset * 2 >= queue.length){
      queue  = queue.slice(offset);
      offset = 0;
    }

    // register any surviving owners as exes
    for (var owner in lock.owners) {
      if (lock.owners.hasOwnProperty(owner)) lock.exes[owner] = 1;
    }
    lock.owners = {};

    // return the dequeued lock
    return lock;

  }

  /* Returns the lock at the front of the queue (without dequeuing it). If the
   * queue is empty then undefined is returned.
   */
  this.peek = function(){

    // return the lock at the front of the queue
    return (queue.length > 0 ? queue[offset] : undefined);

  }

  /* Dumps the complete queue
   */
  this.dump = function(){

    return queue.slice(offset);

  }

}

function purge(resource, cutoff) {
  var purged = 0;
  if (resource in queues) {
    var expired = queues[resource].expired(cutoff, config.timeout);
    while (expired) {
      var lock = queues[resource].dequeue();
      if (config.debug) console.log("Removing "+keys(lock.exes).join()+" from "+resource);
      purged++;
      expired = queues[resource].expired(cutoff, config.timeout);
    }
    if (queues[resource].getLength() === 0) delete queues[resource];
  }
  return purged;
}

setInterval(function () {
  var now = new Date().getTime();
  for (var resource in queues) {
    purge(resource, now);
  }
}, config.gc_interval);

function response(op, id, resource, rc, data)
{
  return JSON.stringify({ "op": op,
                          "id": id,
                          "resource": resource,
                          "status": rc,
                          "data": data });
}

function parent_of(str)
{
  var slash = str.lastIndexOf('/');
  if (slash < 0) return '';
  return str.substring(0, slash);
}

var action = {
  'stats': function (op, id, resource, until) {
    stats.uptime = until - config.timestamp;
    return response(op, id, resource, 'ok', stats);
  },
  'grab': function (op, id, resource, until) {
    var pos = 0;
    var locks = {};
    var r = resource;
    var shared = false;
    var max_timestamp = 0;
    while (r !== '') {
      if (r in queues) {
        if (!(id in queues[r].peek().owners) && shutdown_pending) {
          return response(op, id, r, 'shutdown', 0);
        }
      } else {
        if (shutdown_pending) {
          return response(op, id, r, 'shutdown', 0);
        } else {
          queues[r] = new Queue();
        }
      }
      locks[r] = queues[r].enqueue(r, id, until, shared);
      var t = queues[r].peek().max_timestamp;
      if (t > max_timestamp) max_timestamp = t;
      pos += locks[r] - 1;
      r = parent_of(r);
      shared = true;
    }
    return response(op, id, resource, pos === 0 ? 'ok' : 'wait', { "pos": locks, "until": max_timestamp });
  },
  'release': function (op, id, resource, until) {
    var purged = 0;
    var r = resource;
    var shared = false;
    while (r !== '') {
      if (r in queues) {
        queues[r].enqueue(r, id, 0, shared);
        purged += purge(r, until);
      }
      r = parent_of(r);
      shared = true;
    }
    return response(op, id, resource, 'ok', purged);
  },
  'peek': function (op, id, resource, until) {
    var locks = {};
    var r = resource;
    while (r !== '') {
      if (r in queues) {
        var lock = queues[r].peek();
        if (lock) locks[r] = lock;
      }
      r = parent_of(r);
    }
    return response(op, id, resource, 'ok', locks);
  },
  'dump': function (op, id, resource, until) {
    var data = {};
    for (var q in queues) data[q] = queues[q].dump();
    return response(op, id, resource, 'ok', { "config": config, "stats": stats, "queues": data });
  },
  'config': function (op, id, resource, until) {
    return response(op, id, resource, 'ok', config);
  },
  'shutdown': function (op, id, resource, until) {
    shutdown_pending = true;
    for (var q in queues) return response(op, id, resource, 'wait', 0);
    shutdown = true;
    return response(op, id, resource, 'ok', 0);
  }
};

http.createServer(function (req, res) {

  if (req.method !== 'GET') {
    res.writeHead(405, "Unsupported request method");
    res.end();
    return;
  }

  var req_url = url.parse(req.url, true);
  var resource = req_url.pathname;

  // Serve static files if resource begins with the path /ui/...
  if (resource === '/ui' || (resource.length > 3 && resource.substring(0,4) === '/ui/')) {
    var file_path = config.static_content;
    if (resource === '/ui' || resource === '/ui/') file_path += '/index.html';
    else file_path += resource.substring(3);
    if (config.debug) console.log('GET '+file_path);
    fs.exists(file_path, function (exists) {
      if (exists) {
        var stream = fs.createReadStream(file_path)
        stream.on('error', function (error) {
          res.writeHead(500, error+"\n");
          res.end(error);
        });
        var extname = path.extname(file_path);
        if (extname in mime_types) {
          res.setHeader('Content-Type', mime_types[extname]);
        } else {
          res.setHeader('Content-Type', 'text/plain');
        }
        res.writeHead(200);
        stream.pipe(res);
        return;
      } else {
        res.writeHead(404, "Not found: "+file_path);
        res.end("Not found: "+file_path+"\n");
        return;
      }
    });
    return;
  }

  var op = req_url.query['op'];
  var id = req_url.query['id'];
  var until = req_url.query['until'];

  if (typeof op === 'undefined') op = 'peek';
  if (typeof id === 'undefined') id = 'unknown';
  if (typeof until === 'undefined') until = new Date().getTime();
  else until = parseInt(until);
  if (config.debug) console.log("GET: op="+op+"; id="+id+"; until="+until+"; resource="+resource);
  if (id === 'unknown' && ( op === 'grab' || op == 'release')) {
    if (config.debug) console.log('"id" required for "'+op+'"');
    res.writeHead(400, '"id" required for "'+op+'"');
    res.end();
  } else if (!resource_regexp.test(resource)) {
    if (config.debug) console.log('"resource" contains illegal characters: "'+resource+'"');
    res.writeHead(400, '"resource" contains illegal characters: "'+resource+'"');
    res.end();
  } else if (!owner_regexp.test(id)) {
    if (config.debug) console.log('"id" contains illegal characters: "'+id+'"');
    res.writeHead(400, '"id" contains illegal characters: "'+resource+'"');
    res.end();
  } else if (op in action) {
    res.writeHead(200, {'Content-Type': 'application/json'});
    res.end(action[op](op, id+resource, resource, until));
  } else {
    if (config.debug) console.log('Not a recognized operation: '+op);
    res.writeHead(400, 'Not a recognized operation: '+op);
    res.end();
  }

  if (shutdown) {
    console.log("Shutting down");
    process.exit();
  }
}).listen(config.port, config.host);

console.log('Server running at http://'+config.host+':'+config.port);
