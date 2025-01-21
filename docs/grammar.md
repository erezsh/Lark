# Grammar Reference

## Definitions

A **grammar** is a list of rules and terminals, that together define a language.

Terminals define the alphabet of the language, while rules define its structure.

In Lark, a terminal may be a string, a regular expression, or a concatenation of these and other terminals.

Each rule is a list of terminals and rules, whose location and nesting define the structure of the resulting parse-tree.

A **parsing algorithm** is an algorithm that takes a grammar definition and a sequence of symbols (members of the alphabet), and matches the entirety of the sequence by searching for a structure that is allowed by the grammar.

### General Syntax and notes

Grammars in Lark are based on [EBNF](https://en.wikipedia.org/wiki/Extended_Backus–Naur_form) syntax, with several enhancements.

EBNF is basically a short-hand for common BNF patterns.

Optionals are expanded:

```ruby
  a b? c    ->    (a c | a b c)
```

Repetition is extracted into a recursion:

```ruby
  a: b*    ->    a: _b_tag
                 _b_tag: (_b_tag b)?
```

And so on.

Lark grammars are composed of a list of definitions and directives, each on its own line. A definition is either a named rule, or a named terminal, with the following syntax, respectively:

```html
  rule: <EBNF-EXPRESSION>
      | etc.

  TERM: <EBNF-EXPRESSION>   // Rules aren't allowed
```


**Comments** start with
either `//` (C++ style) or `#` (Python style, since version 1.1.6)
and last to the end of the line.

Lark begins the parse with the rule 'start', unless specified otherwise in the options.

Names of rules are always in lowercase, while names of terminals are always in uppercase. This distinction has practical effects, for the shape of the generated parse-tree, and the automatic construction of the lexer (aka tokenizer, or scanner).


## Terminals

Terminals are used to match text into symbols. They can be defined as a combination of literals and other terminals.

**Syntax:**

```html
<NAME> [. <priority>] : <literals-and-or-terminals>
```

Terminal names must be uppercase.

Literals can be one of:

* `"string"`
* `/regular expression+/`
* `"case-insensitive string"i`
* `/re with flags/imulx`
* Literal range: `"a".."z"`, `"1".."9"`, etc.

Terminals also support grammar operators, such as `|`, `+`, `*` and `?`.

Terminals are a linear construct, and therefore may not contain themselves (recursion isn't allowed).

### Templates

Templates are expanded when preprocessing the grammar.

Definition syntax:

```javascript
  my_template{param1, param2, ...}: <EBNF EXPRESSION>
```

Use syntax:

```javascript
some_rule: my_template{arg1, arg2, ...}
```

Example:
```javascript
_separated{x, sep}: x (sep x)*  // Define a sequence of 'x sep x sep x ...'

num_list: "[" _separated{NUMBER, ","} "]"   // Will match "[1, 2, 3]" etc.
```

### Priority

Terminals can be assigned a priority to influence lexing. Terminal priorities
are signed integers with a default value of 0. To give a terminal a priority other than 0, append `.p` to the end of the terminal name, whre `p` is the priority.

When using a lexer, the highest priority terminals are always matched first.

For example, the grammar:
```
start: AB | A_OR_B_PLUS
AB: "ab"
A_OR_B_PLUS: /[ab]+/
```
will parse `"ab"` as the token `AB` as written.

Giving `A_OR_B_PLUS` a higher priority will result in the same string being parsed as that token:
```
start: AB | A_OR_B_PLUS
AB: "ab"
A_OR_B_PLUS.1: /[ab]+/
```

When using Earley's dynamic lexing, terminal priorities are used to prefer
certain lexings and resolve ambiguity.

### Regexp Flags

You can use flags on regexps and strings. For example:

```perl
SELECT: "select"i     //# Will ignore case, and match SELECT or Select, etc.
MULTILINE_TEXT: /.+/s
SIGNED_INTEGER: /
    [+-]?  # the sign
    (0|[1-9][0-9]*)  # the digits
 /x
```

Supported flags are one of: `imslux`. See Python's regex documentation for more details on each one.

Regexps/strings of different flags can only be concatenated in Python 3.6+

#### Notes for when using a lexer:

When using a lexer (basic or contextual), it is the grammar-author's responsibility to make sure the literals don't collide, or that if they do, they are matched in the desired order. Literals are matched according to the following precedence:

1. Highest priority first (priority is specified as: TERM.number: ...)
2. Length of match (for regexps, the longest theoretical match is used)
3. Length of literal / pattern definition
4. Name

**Examples:**
```perl
IF: "if"
INTEGER : /[0-9]+/
INTEGER2 : ("0".."9")+          //# Same as INTEGER
DECIMAL.2: INTEGER? "." INTEGER  //# Will be matched before INTEGER
WHITESPACE: (" " | /\t/ )+
SQL_SELECT: "select"i
```

### Regular expressions & Ambiguity

Each terminal is eventually compiled to a regular expression. All the operators and references inside it are mapped to their respective expressions.

For example, in the following grammar, `A1` and `A2`, are equivalent:
```perl
A1: "a" | "b"
A2: /a|b/
```

This means that inside terminals, Lark cannot detect or resolve ambiguity, even when using Earley.

For example, for this grammar:
```perl
start           : (A | B)+
A               : "a" | "ab"
B               : "b"
```
We get only one possible derivation, instead of two:

```bash
>>> p = Lark(g, ambiguity="explicit")
>>> p.parse("ab")
Tree('start', [Token('A', 'ab')])
```

This is happening because Python's regex engine always returns the best matching option. There is no way to access the alternatives.

If you find yourself in this situation, the recommended solution is to either use the "dynamic_complete" lexer, or use rules instead.

Example using rules:

```python
>>> p = Lark("""start: (a | b)+
...             !a: "a" | "ab"
...             !b: "b"
...             """, ambiguity="explicit")
>>> print(p.parse("ab").pretty())
_ambig
  start
    a   ab
  start
    a   a
    b   b
```

Example using dynamic-complete:

```python
>>> g = """
...     start: (A | B)+
...     A    : "a" | "ab"
...     B    : "b"
... """
>>> p = Lark(g, ambiguity="explicit", lexer="dynamic_complete")
>>> rich.print(p.parse("ab"))
_ambig
├── start
│   └── ab
└── start
    ├── a
    └── b
```

(note: the dynamic-complete lexer can significantly affect the performance of the parser)

## Rules

**Syntax:**
```html
<name> : <items-to-match>  [-> <alias> ]
       | ...
```

Names of rules and aliases are always in lowercase.

Rule definitions can be extended to the next line by using the OR operator (signified by a pipe: `|` ).

An alias is a name for the specific rule alternative. It affects tree construction.


Each item is one of:

* `rule`
* `TERMINAL`
* `"string literal"` or `/regexp literal/`
* `(item item ..)` - Group items
* `[item item ..]` - Maybe. Same as `(item item ..)?`, but when `maybe_placeholders=True`, generates `None` if there is no match.
* `item?` - Zero or one instances of item ("maybe")
* `item*` - Zero or more instances of item
* `item+` - One or more instances of item
* `item ~ n` - Exactly *n* instances of item
* `item ~ n..m` - Between *n* to *m* instances of item (not recommended for wide ranges, due to performance issues)

Note that all operators, including `~ n`, apply directly to the item on their left.
For instance `a ~ 2 b ~ 3` is parsed as `(a ~ 2) (b ~ 3)`.

**Examples:**
```perl
hello_world: "hello" "world"
mul: (mul "*")? number     //# Left-recursion is allowed and encouraged!
expr: expr operator expr
    | value               //# Multi-line, belongs to expr

four_words: word ~ 4
```

### Priority

Like terminals, rules can be assigned a priority. Rule priorities are signed
integers with a default value of 0.

When using LALR, the highest priority rules are used to resolve collision errors.

When using Earley, rule priorities are used to resolve ambiguity.

<a name="dirs"></a>
## Directives

### %ignore

All occurrences of the terminal will be ignored, and won't be part of the parse.

Using the `%ignore` directive results in a cleaner grammar.

It's especially important for the LALR(1) algorithm, because adding whitespace (or comments, or other extraneous elements) explicitly in the grammar, harms its predictive abilities, which are based on a lookahead of 1.

**Syntax:**
```html
%ignore <TERMINAL>
```
**Examples:**
```perl
%ignore " "

COMMENT: "#" /[^\n]/*
%ignore COMMENT
```
### %import

Allows one to import terminals and rules from lark grammars.

When importing rules, all their dependencies will be imported into a namespace, to avoid collisions. To override any of their dependencies (e.g. like you would override methods when inheriting a class), use the ``%override`` directive.

**Syntax:**
```html
%import <module>.<TERMINAL>
%import <module>.<rule>
%import <module>.<TERMINAL> -> <NEWTERMINAL>
%import <module>.<rule> -> <newrule>
%import <module> (<TERM1>, <TERM2>, <rule1>, <rule2>)
```

If the module path is absolute, Lark will attempt to load it from the built-in directory (which currently contains `common.lark`, `lark.lark`, `python.lark`, and `unicode.lark`).

If the module path is relative, such as `.path.to.file`, Lark will attempt to load it from the current working directory. Grammars must have the `.lark` extension.

The rule or terminal can be imported under another name (an alias) with the `->` syntax.

**Example:**
```perl
%import common.NUMBER

%import .terminals_file (A, B, C)

%import .rules_file.rule_a -> rule_b
```

Note that `%ignore` directives cannot be imported. Imported rules will abide by the `%ignore` directives declared in the main grammar.

### %declare

Declare a terminal without defining it. Useful for plugins.

### %override

Override a rule or terminals, affecting all references to it, even in imported grammars.

Useful for implementing an inheritance pattern when importing grammars.

**Example:**
```perl
%import my_grammar (start, number, NUMBER)

// Add hex support to my_grammar
%override number: NUMBER | /0x\w+/
```

### %extend

Extend the definition of a rule or terminal, e.g. add a new option on what it can match, like when separated with `|`.

Useful for splitting up a definition of a complex rule with many different options over multiple files.

Can also be used to implement a plugin system where a core grammar is extended by others.


**Example:**
```perl
%import my_grammar (start, NUMBER)

// Add hex support to my_grammar
%extend NUMBER: /0x\w+/
```

For both `%extend` and `%override`, there is not requirement for a rule/terminal to come from another file, but that is probably the most common use-case.
