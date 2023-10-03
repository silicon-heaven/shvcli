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


Documentation
-------------

The documentation is available in `docs` directory. You can build it using:

    sphinx-build -b html docs docs-html
