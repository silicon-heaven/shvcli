=====================================
Silicon Heaven CLI access application
=====================================

This provides an easy to use CLI interfase to access the SHV network.


Usage
-----

You need to start application ``shvcli``. The first argument is URL specifying
where client should connect to.

After successful connection you will see prompt (``>``) and you can start typing.
Methods can be called with ``PATH:METHOD`` syntax or with just ``METHOD``. You can
use ``PATH:`` for change current path prefix. This prefix is displayed before
prompt and is prefixed to any paths you specify on command line. To return to
the root you need to use absolute path (``/``).

An example of usage:

.. code-block:: console

  > ls
  [".app","test"]
  > .app:
  .app> dir
  [{"access":"bws","flags":0,"name":"dir","signature":3},{"access":"bws","flags":0,"name":"ls","signature":3},{"access":"bws","flags":2,"name":"shvVersionMajor","signature":2},{"access":"bws","flags":2,"name":"shvVersionMinor","signature":2},{"access":"bws","flags":2,"name":"appName","signature":2},{"access":"bws","flags":2,"name":"appVersion","signature":2},{"access":"bws","flags":0,"name":"ping","signature":0}]
  .app> appName
  "pyshvbroker"
  .app> ls
  ["broker"]
  .app> broker:dir
  [{"access":"bws","flags":0,"name":"dir","signature":3},{"access":"bws","flags":0,"name":"ls","signature":3},{"access":"srv","flags":0,"name":"clientInfo","signature":3},{"access":"srv","flags":2,"name":"clients","signature":2},{"access":"srv","flags":0,"name":"disconnectClient","signature":1},{"access":"rd","flags":2,"name":"mountPoints","signature":2}]
  .app> broker:ls
  ["currentClient","client","clientInfo"]
  .app> /:
  >


Configuration file
------------------

Tool reads configuration from files ``/etc/shvcli.ini`` and ``~/.shvcli.ini``.
They are in INI file format and the following sections are supported:

**hosts**: That provides mapping from some name to RPC URL.

**hosts-shell**: That is same as **hosts** with exception that URL is passed
through your local Shell to expand any variables or command substitutions.


Example configuration file:

.. code-block:: ini

   [hosts]
   localhost = tcp://test@localhost?password=test

   [hosts-shell]
   company = tcp://smith@company.example.org?password=$(pass company/shv)


Internal methods
----------------

CLI provides few additional methods that can be called on top of the ones
provided by SHV network. They are all prefixed with ``!`` to clearly distinguish
them. They provide a way to control CLI as well as to get insight into the
environment you are running in.

**tree|t**: This prints tree of known nodes from current path prefix. This is
not all nodes present in the SHV network. This is only what was discovered so
far (and cached thus it can be also old). You can use it to visualize the tree
of nodes you are working with as well as to get insight into the state of the
cache.

**raw**: ``ls`` and ``dir`` methods are handled in a special way as described in
the next chapter. This special handling can be possibly decremental if you are
trying to debug something specific with these functions and this this provides a
way to disable this. Note that caching and discovery of the nodes will stop
working once you are in the raw mode and thus you will no longer get the
advantage of that.

**autoprobe**: The default behavior is to use ``ls`` and ``dir`` methods to
discover nodes and methods on autocompletion. That is very convenient but it
also generates traffic that is not directly visible to you. If you prefer not to
do that for any reason then you can use this to disable this behavior.

**debug|d**: This controls logging facilities of SHVCLI itself. With this you
can get info about all messages sent and received as well as other debug info.
It is beneficial to disable the **autoprobe** once you disable debug because
otherwise the output on the CLI will be mangled on completion.


Special methods ``ls`` and ``dir``
----------------------------------

These methods are handled in a special way to allow easy discovery of the SHV
nodes. Their output is processed and displayed in easy to read format but not in
the fullest content.

Their parameter is also handled in a special way. It is considered to be
additional path suffix unless it is a valid CPON. This is allowed to match the
common shells.


Documentation
-------------

The documentation is available in `docs` directory. You can build it using:

    sphinx-build -b html docs docs-html
