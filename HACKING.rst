Developing Gateway
===================

We welcome contributions to the Yombo Gateway and modules. to get started

Sending a bitbucket pull request
---------------------------------

This is the preferred method for contributions, simply create a BitBucket
fork, commit your changes to the fork, and then open up a pull request.

Posting patches https://projects.yombo.net/projects/gateway/issues/new
----------------------------------------------------------------------

An alternative to forking and generating a pull request is to submit a
new issue at https://projects.yombo.net/projects/gateway/issues/new 

Please format it via `git format-patch` and paste it in the description. This
allows the patch to give you the contributor the credit for your patch, and
gives the Yombo community an archive of the patch and a place for discussion.

Contributions Welcome!
----------------------

The goal here is to make contributions clear, make sure there is a trail for
where the code has come from, but most importantly, to give credit where credit
is due!

Documentation
=============

Editing and Previewing the Docs
-------------------------------
You need ``sphinx-build`` to build the docs. In Debian/Ubuntu this is provided
in the ``python-sphinx`` package.

Then::

    cd docs; make html

- The docs then are built in the ``docs/build/html/`` folder. If you make
  changes and want to see the results, ``make html`` again.
- The docs use ``reStructuredText`` for markup. See a live demo at
  http://rst.ninjs.org/
- The help information on each module or state is culled from the python code
  that runs for that piece. Find them in ``yombo/core/`` or ``yombo/lib/``.
- If you are developing using Arch Linux (or any other distribution for which
  Python 3 is the default Python installation), then ``sphinx-build`` may be
  named ``sphinx-build2`` instead. If this is the case, then you will need to
  run the following ``make`` command::

    make SPHINXBUILD=sphinx-build2 html

Installing Gateway for development
----------------------------------

Documentation for configuring your machine and downloading the software
is located here: https://yombo.net/docs/

Create a virtual environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a new `virtualenv`_::

    virtualenv /path/to/your/virtualenv

.. _`virtualenv`: http://pypi.python.org/pypi/virtualenv

On Arch Linux, where Python 3 is the default installation of Python, use the
``virtualenv2`` command instead of ``virtualenv``.

Debian, Ubuntu, and the RedHat systems mentioned above, you should use
``--system-site-packages`` when creating the virtualenv::

    virtualenv --system-site-packages /path/to/your/virtualenv

.. note:: Using your system Python modules in the virtualenv

    If you have the required python modules installed on your system already
    and would like to use them in the virtualenv rather than having pip
    download and compile new ones into this environment, run ``virtualenv``
    with the ``--system-site-packages`` option. If you do this, you can skip
    the pip command below that installs the dependencies (python-gnupg,
    pyephem), assuming that the listed modules are all installed in your system
    PYTHONPATH at the time you create your virtualenv.

Configure your virtual environment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Activate the virtualenv::

    source /path/to/your/virtualenv/bin/activate

Install Gateway (and dependencies) into the virtualenv::

    pip install -r requirements.txt
    pip install psutil
    pip install -e .

