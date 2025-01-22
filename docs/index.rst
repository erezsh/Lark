.. Lark documentation master file, created by
   sphinx-quickstart on Sun Aug 16 13:09:41 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to Lark's documentation!
================================


Lark is a modern parsing library for Python. Lark can parse any context-free grammar.

Lark provides:

- Advanced grammar language, based on EBNF
- Three parsing algorithms to choose from: Earley, LALR(1) and CYK
- Automatic tree construction, inferred from your grammar
- Fast unicode lexer with regexp support, and automatic line-counting

Refer to the section :doc:`features` for more information.


Install Lark
--------------

.. code:: bash

   $ pip install lark


-------

How the documentation is organized
----------------------------------

A high-level overview of how it’s organized will help you know where to look for certain things:

* Tutorials take you by the hand through a series of steps how to get familiar with Lark. Start here if you’re new to Lark.
* How-to guides are bite-sized, problem-specific solutions to common tasks.
* Addendums covers background information to Lark.
* References contain syntax and semantics reference material for Lark.

.. toctree::
   :maxdepth: 2
   :caption: First steps

   json_tutorial


.. toctree::
   :maxdepth: 2
   :caption: How-to guides

   recipes
   examples/index
   how_to_use
   how_to_develop


.. toctree::
   :maxdepth: 2
   :caption: Addendum

   philosophy
   resources

.. toctree::
   :maxdepth: 2
   :caption: Reference

   features
   parsers
   grammar
   tree_construction
   classes
   visitors
   forest
   tools