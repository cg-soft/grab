grab
====

A Hierarchical Perishable Lock Service
--------------------------------------

Perishable locks are locks with a relatively short time to live (usually about a minute or so), and which are expected to be refreshed via some keep-alive or polling process until they are no longer required.

The intended use is for continuous builds via jenkins or similar services. 

Builds are notoriously fickle, and crash or are terminated by impatient users. Builds also make use of shared resources, and sometimes require exclusive access. Using traditional locking mechanisms requires cleanup to avoid stale locks.

This service works around the problem of stale locks by incorporating the cleanup mechanism and releasing locks that haven't been refreshed within a given timespan.

Features include:

* Hierarchical locking structure via resource paths. The last item in the path gets an exclusive lock, and the items in the path get shared locks.
* Queues for every resource ensure "first come first serve", as opposed to "whoever shows up at the right time gets it".
* REST api using simple GET requests returning JSON responses.
* Pure in memory state, no databases or files required.
* Clean shutdown to preserve continuous service even during upgrades.

Components
----------

<table>
 <tr>
  <td>grab.js</td>
  <td>
Node script containing the actual server code. Run "node grab.js --help" to see the configuration options.
  </td>
 </tr>
 <tr>
  <td>grab.py</td>
  <td>
Python client script. Run "python grab.py --help" to see the options.
  </td>
 </tr>
 <tr>
  <td>restart.sh</td>
  <td>
Wrapper script to cleanly restart the service.
  </td>
 </tr>
 <tr>
  <td>sample.sh</td>
  <td>
Sample grab() and release() shell functions using the locking service with keep-alive process.
  </td>
 </tr>
</table>

Sample Usage
------------

First ensure you have python and node installed, then:

1. start the service by running ./restart.sh
2. optionally, in a separate window, tail -f ./log
3. run the sample script: ./sample.sh
4. try more experiments by using grab.py
5. stop the service: ./grab.py shutdown
6. inspect the log file: 
