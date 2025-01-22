# Working with Lark

## Work process

This is the recommended process for working with Lark:

1. Collect or create input samples, that demonstrate key features or behaviors in the language you're trying to parse.

2. Write a grammar. Try to aim for a structure that is intuitive, and in a way that imitates how you would explain your language to a fellow human.

3. Try your grammar in Lark against each input sample. Make sure the resulting parse-trees make sense.

4. Use Lark's grammar features to [shape the tree](tree_construction.md): Get rid of superfluous rules by inlining them, and use aliases when specific cases need clarification.

   You can perform steps 1-4 repeatedly, gradually growing your grammar to include more sentences.

5. Create a transformer to evaluate the parse-tree into a structure you'll be comfortable to work with. This may include evaluating literals, merging branches, or even converting the entire tree into your own set of AST classes.

Of course, some specific use-cases may deviate from this process. Feel free to suggest these cases, and I'll add them to this page.

## Getting started

Browse the [Examples](https://github.com/lark-parser/lark/tree/master/examples) to find a template that suits your purposes.

Read the tutorials to get a better understanding of how everything works. (links in the [main page](/index))

Use the [Cheatsheet (PDF)](https://lark-parser.readthedocs.io/en/latest/_static/lark_cheatsheet.pdf) for quick reference.

Use the reference pages for more in-depth explanations. (links in the [main page](/index))

## Debug

Grammars may contain non-obvious bugs, usually caused by rules or terminals interfering with each other in subtle ways.

When trying to debug a misbehaving grammar, the following methodology is recommended:

1. Create a copy of the grammar, so you can change the parser/grammar without any worries
2. Find the minimal input that creates the error
3. Slowly remove rules from the grammar, while making sure the error still occurs.

Usually, by the time you get to a minimal grammar, the problem becomes clear.

But if it doesn't, feel free to ask us on gitter, or even open an issue. Post a reproducing code, with the minimal grammar and input, and we'll do our best to help.

### Regex collisions

A likely source of bugs occurs when two regexes in a grammar can match the same input. If both terminals have the same priority, most lexers would arbitrarily choose the first one that matches, which isn't always the desired one. (a notable exception is the `dynamic_complete` lexer, which always tries all variations. But its users pay for that with performance.)

These collisions can be hard to notice, and their effects can be difficult to debug, as they are subtle and sometimes hard to reproduce.

To help with these situations, Lark can utilize a new external library called `interegular`. If it is installed, Lark uses it to check for collisions, and warn about any conflicts that it can find:

```
import logging
from lark import Lark, logger

logger.setLevel(logging.WARN)

collision_grammar = '''
start: A | B
A: /a+/
B: /[ab]+/
'''
p = Lark(collision_grammar, parser='lalr')

# Output:
# Collision between Terminals B and A. The lexer will choose between them arbitrarily
# Example Collision: a
```

You can install interegular for Lark using `pip install 'lark[interegular]'`.

Note 1: Interegular currently only runs when the lexer is `basic` or `contextual`.

Note 2: Some advanced regex features, such as lookahead and lookbehind, may prevent interegular from detecting existing collisions.

### Shift/Reduce collisions

By default Lark automatically resolves Shift/Reduce conflicts as Shift. It produces notifications as debug messages.

when users pass `debug=True`, those notifications are written as warnings.

Either way, to get the messages printed you have to configure the `logger` beforehand. For example:

```python
import logging
from lark import Lark, logger

logger.setLevel(logging.DEBUG)

collision_grammar = '''
start: as as
as: a*
a: "a"
'''
p = Lark(collision_grammar, parser='lalr', debug=True)
# Shift/Reduce conflict for terminal A: (resolving as shift)
#  * <as : >
# Shift/Reduce conflict for terminal A: (resolving as shift)
#  * <as : __as_star_0>
```

### Strict-Mode

Lark, by default, accepts grammars with unresolved Shift/Reduce collisions (which it always resolves to shift), and regex collisions.

Strict-mode allows users to validate that their grammars don't contain these collisions.

When Lark is initialized with `strict=True`, it raises an exception on any Shift/Reduce or regex collision.

If `interegular` isn't installed, an exception is thrown.

When using strict-mode, users will be expected to resolve their collisions manually:

- To resolve Shift/Reduce collisions, adjust the priority weights of the rules involved, until there are no more collisions.

- To resolve regex collisions, change the involved regexes so that they can no longer both match the same input (Lark provides an example).

Strict-mode only applies to LALR for now.

```python
from lark import Lark

collision_grammar = '''
start: as as
as: a*
a: "a"
'''
p = Lark(collision_grammar, parser='lalr', strict=True)

# Traceback (most recent call last):
#   ...
# lark.exceptions.GrammarError: Shift/Reduce conflict for terminal A. [strict-mode]
```

## Tools

### Stand-alone parser

Lark can generate a stand-alone LALR(1) parser from a grammar.

The resulting module provides the same interface as Lark, but with a fixed grammar, and reduced functionality.

Run using:

```bash
python -m lark.tools.standalone
```

For a play-by-play, read the [tutorial](http://blog.erezsh.com/create-a-stand-alone-lalr1-parser-in-python/)

### Import Nearley.js grammars

It is possible to import Nearley grammars into Lark. The Javascript code is translated using Js2Py.

See the [tools page](tools.md) for more information.
