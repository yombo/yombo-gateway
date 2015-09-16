.. index:: install_gateway_fork

.. _install_gateway_fork:

============================================================
Install with forked GIT - Allows you to contribute to Yombo
============================================================

This outlines the steps to download, configure, and use the gateway software.
This assumes that you already have


:doc:`python and the required python modules <../chapters/install-python>`
installed.

Everyone is welcome and encouraged to contribute code, no matter how big
or small.  To make it easy, Yombo uses bitbucket and 
`Yombo Projects <https://projects.yombo.net>`_
to track issues and feature requests.

Summary of steps
================

Although the lenght of this document is a bit lengthy, it's geared towards
getting anyone started. The follow steps are simple and can be completed in
a matter of minutes.

* Install Git - A content revision tracking system. 
* Hello git - Tell Git who you are.
* Get a free `BitBucket account <https://bitbucket.org/plans>`_ - BitBucket
  hosts the open source repository.
* Fork - Create your personal copy of the repository to make changes against.
* Clone - Download a copy.

Then, when if/when you want to contribute code to the community perform the
following:

* Submit a ticket - Visit `Yombo Projects <https://projects.yombo.net>`_ and
  submit a feature request or create an issue.
* Make Changes - Make any changes to the software or this documentation.
* Commit - Commit your changes into your local copy of the respository.
* Push - Push the changes back to BitBucket.
* Pull Request - Tell the Yombo team that you have changes you wish to get
  integrated into the mainline code.

Install Git
==============

Depending on your operating system:

Linux
-----

Fedora:

.. code-block:: bash

  $ yum install git-core

Debian based, like Ubuntu:

.. code-block:: bash

  $ apt-get install git-core

Mac
---

Download the graphical Git installer: `<http://code.google.com/p/git-osx-installer>`_

Or, if you have `MacPorts <http://www.macports.org>`_) installed:

.. code-block:: bash

  $ sudo port install git-core +svn +doc +bash_completion +gitweb

Windows
-------

Installing Git on Windows is also easy. The msysGit project has an easy
installation procedure. Just download the installer and the Google Code page, and run it:

`<http://code.google.com/p/msysgit>`_

This installes command-line version, which includes an SSH client to
communicate with remote repositories, and the standard GUI.

Hello Git
=============

Git allows for author attribution, that is, you get credit for the work
and contributions you do. The purpose of Git is to track changes to
any content (documentation, source code, scripts, etc) and allow
collaboration on projects easily.  In order to do this, you need to
tell Git who you are.  This can be a real name, or an alias.
However, whatever information you set below will be maintained within
the Git repository and forwarded into the master repository. This
helps to comply with the requirement that all code contributions be
documented by each contributor.

.. note::

  Since Git is tracking your contributions, there is no need to make comments
  in code of what and where you changed items.  However, the ticket number
  needs to be referenced within the git commit.

Lets do it!
-----------

Git is actually a series of tools, one of them is called "config".  We will
use this to set your name and email address for attribution so you
get credit. Git config allows you to get and set all aspects of how Git operates
and looks. Git config stores these variables in three different places:

.. note::

  Information that you set here and push to bitbucket may be maintained
  indefinitely. If you are uncomfortable with giving your real name
  and email address, please setup  another email account that you can
  check periodically. 


* ``/etc/gitconfig`` - System wide settings for every user and all
  their repositories. If you pass the option ``--system`` to ``git config``,
  this file gets updated.
* ``~/.gitconfig`` - Specific to only your user. Specify ``--global`` on the command
  link to use this file.
* A config file in the local repository. It's stored in ``.git/config`` of whichever
  repository you want. Any settings here are only specific to this repository.

*Priority* of the file is: local repository, user, system wide.

For Windows, Git looks for the .gitconfig file in your $HOME directory 
(C:\Documents and Settings\$USER for most people). Git will also /etc/gitconfig; however
it's relative to the MSys root - where you installed Git as set in the installer.

Tell gi who you are
-------------------
First things first, tell Git who you are so Git can tell us who you are. Once you make
a commit with these settings, and pass them around, they unchangeable!

.. code-block:: bash

  $ git config --global user.name "John Doe"
  $ git config --global user.email johndoe@example.com

Select an Editor
----------------

By default, Git uses your system defined editor. If you wish to change this:

.. code-block:: bash

  $ git config --global core.editor emacs

Review your settings
--------------------

To review, simple do ``git config --list``:

.. code-block:: bash

  $ git config --list
  user.name=John Doe
  user.email=johndoe@example.com
  color.status=auto
  color.branch=auto
  color.interactive=auto
  color.diff=auto
  ...

You might see some values more than one time since Git reads the same key from different files.
When this happens, Git will use the last value for each key listed. 

If you want to inspect a specific setting:

.. code-block:: bash

  $ git config user.name
  John Doe

BitBucket Account
=================

Before you can contribute code, you will need a BitBucket account.  If you
already have one, you can can skip this section and move to :ref:`gitfork`

If you don't have an account, sign up for a
`free bitbucket account <https://bitbucket.org/plans>`_.

.. _gitfork:

Fork It
========

This step creates a copy of the Yombo-Gateway repository for your personal use.
You can make as many changes as you want without affecting anyone else.  If
needed, you can always delete your copy (fork), you can re-fork again.

Visit `Yombo Gateway Repository <http://code.yombo.net/yombo-gateway>`_.

Click the "Fork" button then follow the on screen prompts.  That's it!

Clone It
========

.. note::

  This tutorial uses branches to track changes. If you are unfamiliar with branching,
  see this article: `<http://git-scm.com/book/en/Git-Branching-Basic-Branching-and-Merging>`_.

.. note::

  This tutorial uses an example bitbucket account titled "yombouser". Replace
  any references to this with your username.

Now that you have copy of the repository at BitBucket, which your copy currently only
exists there, it's time to download (clone) it to your computer.

Change to a directory where you want it stored. Keep in mind, this process
will create a new subdirectory and store the repository and the source there.

.. code-block:: bash

  $ git clone https://bitbucket.org/yombo/yombo-gateway.git
  #
  # OR
  #
  # SSH if you have submitted your SSH key (preferred)
  $ git clone git@bitbucket.org/yombo/yombo-gateway.git

If you wish to name the directory something other than Yombo-Gateway, just
add the desired name to the end.

.. code-block:: bash

  $ git clone https://github.com/yombouser/yombo-gateway.git gateway
  # creates a directory called "gateway", and puts the files there.
  # the rest of this document assumes you didn't change the name.

Configure Remotes
-----------------

You have cloned your fork of the Yombo-Gateway repository. To get changes
to the mainline code, you need to add a pointer; we will call this ``upstream``.

.. code-block:: bash

  $ cd yombo-gateway
  # Changes to the root of the new git repository

  $ git remote add upstream https://bitbucket.org/yombo/yombo-gateway.git
  # Assigns the mainline code repo to a remote called "upstream"

Merging upstream changes will be explained below.

Change It
=========

If you found a bug, make sure it hasn't already been reported. You
can search `<https://projects.yombo.net/projects/gateway/issues>`_
to see if someone is already working on it, or the issue has been
completed.

Also, make sure you have the latest version of the code and using the
develop branch.  The develop branch is fairly stable and much more
updated than the master branch which only contains offically released
versions.

.. code-block:: bash

  $ git fetch upstream
  # Pulls in changes to mainline repo, without modifying your code

  $ git checkout develop
  # change to the develop branch before merging from upstream

  $ git merge upstream/develop
  # This merges your existing develop branch to the upstream version.
  # You should never be making changes to the develop branch directly!

.. note::

   Only one feature or one bug fix per branch. To submit your code
   back to the community, you must have a ticket number to associate
   your changes too. This helps the community track work in progress
   and what the changes you made are for.

Create a ticket number here: `<https://projects.yombo.net/projects/gateway/issues/new>`
and fill out the form as best you can.

Set the status of the ticket to one of:

* New - You just wanted to report the bug, but don't plan on coding, or at least not
  coding right now. Perhaps someone else can work on it.
* Investigating - You are still researching the bug, but not actively coding a solution.
* Coding - You are activley working on this ticket.

Unless the ticket is marked "New", assign the ticket to yourself. If it's new, someone else will address
the ticket and assign it to themselves.  Save the ticket and **make a note of the ticket number**. You
will use this ticket number in your commit string to note what this change is about.

Make a new branch with to include the ticket number:

.. code-block:: bash

  $ git checkout devlop
  # Use the lastest version, make sure you recently fetched and merged updates.
  $ git branch item-456
  # Create a new branch for bug/feature #456

Now, *start coding*. Make any changes to the code or documentation. Then, in the root directory
of the repository perform these steps.

.. note::

  This is a shotgun approach and quickly adds all files to a commit.
  You can control which files, or parts of files, are committed. See <find a page>
  for more details.

.. code-block:: bash

  $ git add .
  # Add all changed/new files to the stagging area to be committed.

  $ git commit

You may repeat this step several times as you work on the new feature or work on squishing
a bug.  This is fine and excepted.  However, please rebase your branch before pushing them
back to your github repository.  See 
`Squashing Commits with Rebase <http://gitready.com/advanced/2009/02/10/squashing-commits-with-rebase.html>`_.
Just a note on the "second editor window/popup". Just delete all the previous commit
messages and follow the commit comment standard.

Comment Standards
-----------------

All lines of the commit message must be 80 characters or less!

The first line of the commit comment is a short description of the change followed
by a blank line along with the ticket number, including the #. The # sign
tells the project tracker to link your commit to an issue or feature
request number. 

``#456 No longer drops network connection after a bad command.``

Following the short description, and separated by a blank line, is the full description
which includes: Details, history, reasons, etc.

Push It
=======

If you want to backup your changes to github, or contribute them to
the community, you can push them to github. So far, we have only been working
on the local repository on your computer.

.. code-block:: bash

  $ git checkout item-456
  # Push you bug/feature to github.  Or, whatever branch you want.

  $ git push origin item-456
  # Push commits to your repository on github.

Generate Pull Request
=====================

Naviage to your repository at GitHub (eg: `<http://github.com/yombouser/Yombo-Gateway>`_ ).
Navigate to the your new branch (eg: item-456) you want to submit, and press the "Pull Request" button.

Submit pull requests to one of:

* ``yombo:dev-contrib-bugs`` for bugs fixed.
* ``yombo:dev-contrib-features`` for new features.
* ``yombo:dev-contrib-doc`` for documentation updates.

Once submitted, your commit request will be reviewed.  If accepted, they will be made
available in the "develop" branch.  From here, we will create release branches
and eventaully merge your changes into the master branch.

Merging from upstream
=====================

Whenever you want to pull in changes from the mainline repo, you commit
your changes, and then fetch from the upstream.

  $ git fetch upstream
  # Pulls in changes to mainline repo, without modifying your code

  # Before performing this step, make sure your changed are commited or stashed.
  $ git merge upstream/master
  # Assumes you are working on your master branch. This will
  # merge your changes with the mainline code.

Other things to do
==================

More on branches..
