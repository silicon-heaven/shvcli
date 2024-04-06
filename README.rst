=====================================
Silicon Heaven CLI access application
=====================================
.. image:: https://gitlab.com/silicon-heaven/shvcli/-/raw/master/logo.svg
   :align: right
   :height: 128px

This provides an easy to use CLI interfase to access the SHV network.

* `📃 Sources <https://gitlab.com/silicon-heaven/shvcli>`__
* `⁉️ Issue tracker <https://gitlab.com/silicon-heaven/shvcli/-/issues>`__
* `📕 Silicon Heaven protocol documentation <https://silicon-heaven.github.io/shv-doc/>`__


Installation
------------

The installation can be done with package manager ``pip``.

.. code-block:: console

   $ pip install shvcli


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
   .app
   > dir
   dir ls lschng
   > .app:
   .app> dir
   dir ls lschng shvVersionMajor shvVersionMinor name version ping
   .app> name
   "pyshvbroker"
   .app> broker:ls
   currentClient client clientInfo
   .app> ls broker
   currentClient client clientInfo
   .app> broker/currentClient:info
   {"clientId":0,"mountPoint":null,"subscriptions":[],"userName":"admin"}
   .app> /:
   >


Configuration file
------------------

Tool reads configuration from files ``/etc/shvcli.ini`` and ``~/.shvcli.ini``.
They are in INI file format and the following sections are supported:

**hosts**: That provides mapping from some name to RPC URL.

**hosts-shell**: That is same as **hosts** with exception that URL is passed
through your local Shell to expand any variables or command substitutions.

**config**: That allows you to set some initial configuration that can be also
switched in runtime. The following options are available:

* **vimode**: If Vi input mode should be used for command line input. The
  default is ``false``.
* **autoget**: Automatically call getter methods and print received values when
  listing nodes and methods (``ls`` and ``dir`` methods special handling).
* **autoprobe**: Completion process benefits from probing of the SHV nodes with
  ``ls`` and ``dir``, and to provide easier usage this can happen automatically
  in background. This is what this option controls. It is ``true`` by default
  but it might not be desirable in some cases, because this can generate a lot
  of hidden traffic.
* **raw**: Controls if ``ls`` and ``dir`` methods are handled in a special way
  as described later in this document. This special handling can be possibly
  decremental if you are trying to debug something specific with these functions
  and this provides a way to call them with any CPON to see what they provide.
  Note that caching and discovery of the nodes will stop working once you are in
  the raw mode and thus you will no longer get the advantage of that. The
  default is ``false``.
* **debug**: Controls if internal debug messages are displayed. These messages
  can give you idea of what shvcli is actually doing behind the wail but it can
  be also overwhelming. The default is ``false``. It is beneficial to disable
  the **autobrobe** once you enable debug because otherwise output on CLI will
  be mangled on completion.
* **cache**: Controls if cache is preserved between invocations. Cache is
  separated based on the connection URL and stored in files in
  ``$XDG_CACHE_HOME/shvcli``. The default is ``true``.


Example configuration file:

.. code-block:: ini

   [hosts]
   localhost = tcp://test@localhost?password=test

   [hosts-shell]
   company = tcp://smith@company.example.org?password=$(pass company/shv)

   [config]
   vimode = true


Internal methods
----------------

CLI provides few additional methods that can be called on top of the ones
provided by SHV network. They are all prefixed with ``!`` to clearly distinguish
them. They provide a way to control CLI as well as to get insight into the
environment you are running in.

**subscribe|sub**: Add new subscribe. Shortcut to the call of
``.app/broker/currentClient:subscribe`` that accepts arguments in more convenient
way (you need to use Map if you call that method directly). The argument has
same format such as method calls in this tool, that means ``PATH:METHOD`` where
``METHOD`` can be left out to match all methods. Pattern subscribes are not
supporter, yet.

**unsubscribe|usub**: Unsubscribe existing subscription. It is reverse operation
to the **subscribe** and same remarks apply here as well. It is a shortcut to
the call of ``.app/broker/currentClient:unsubscribe``

**subscriptions|subs**: List current subscriptions. This is shortcut to call
``.app/broker/currentClient:subscriptions``.

**cd**: Change current path prefix to given one even when there is no such node.

**tree|t**: This prints tree of known nodes from current path prefix. This is
not all nodes present in the SHV network. This is only what was discovered so
far (and cached thus it can be also old). You can use it to visualize the tree
of nodes you are working with as well as to get insight into the state of the
cache.

**scan[X]**: Perform recursive probing of the tree up to the depth given as `X`
(the default is 3). On big servers this can be pretty resource demanding and
thus use it sparely.

**set|s**: allows modification of configuration option in runtime.  The names
are the same as in ``config`` section. The boolean options (the only ones
available right now) are set if no argument is provided, or cleared if name is
prefixed with ``no`` (and thus to disable ``raw`` you use ``noraw``). You can
also provide argument ``true`` or ``false``. Without any configuration option it
simply prints the current configuration.


Special methods ``ls`` and ``dir``
----------------------------------

These methods are handled in a special way to allow easy discovery of the SHV
nodes. Their output is processed and displayed in easy to read format but not in
the fullest content.

Their parameter is also handled in a special way. It is considered to be
additional path suffix unless it is a valid CPON. This is allowed to match the
common shells.
