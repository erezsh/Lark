""""This module implements an SPPF implementation

This is used as the primary output mechanism for the Earley parser
in order to store complex ambiguities.

Full reference and more details is here:
http://www.bramvandersanden.com/post/2014/06/shared-packed-parse-forest/
"""

from random import randint
from math import isinf
from collections import deque
from operator import attrgetter
from importlib import import_module
from functools import partial


from ..parse_tree_builder import AmbiguousIntermediateExpander
from .. visitors import Discard
from ..lexer import Token
from ..utils import logger
from ..tree import Tree

class ForestNode(object):
    pass

class SymbolNode(ForestNode):
    """
    A Symbol Node represents a symbol (or Intermediate LR0).

    Symbol nodes are keyed by the symbol (s). For intermediate nodes
    s will be an LR0, stored as a tuple of (rule, ptr). For completed symbol
    nodes, s will be a string representing the non-terminal origin (i.e.
    the left hand side of the rule).

    The children of a Symbol or Intermediate Node will always be Packed Nodes;
    with each Packed Node child representing a single derivation of a production.

    Hence a Symbol Node with a single child is unambiguous.
    """
    __slots__ = ('s', 'start', 'end', '_children', 'paths', 'paths_loaded', 'priority', 'is_intermediate', '_hash')
    def __init__(self, s, start, end):
        self.s = s
        self.start = start
        self.end = end
        self._children = set()
        self.paths = set()
        self.paths_loaded = False

        ### We use inf here as it can be safely negated without resorting to conditionals,
        #   unlike None or float('NaN'), and sorts appropriately.
        self.priority = float('-inf')
        self.is_intermediate = isinstance(s, tuple)
        self._hash = hash((self.s, self.start, self.end))

    def add_family(self, lr0, rule, start, left, right):
        self._children.add(PackedNode(self, lr0, rule, start, left, right))

    def add_path(self, transitive, node):
        self.paths.add((transitive, node))

    def load_paths(self):
        for transitive, node in self.paths:
            if transitive.next_titem is not None:
                vn = SymbolNode(transitive.next_titem.s, transitive.next_titem.start, self.end)
                vn.add_path(transitive.next_titem, node)
                self.add_family(transitive.reduction.rule.origin, transitive.reduction.rule, transitive.reduction.start, transitive.reduction.node, vn)
            else:
                self.add_family(transitive.reduction.rule.origin, transitive.reduction.rule, transitive.reduction.start, transitive.reduction.node, node)
        self.paths_loaded = True

    @property
    def is_ambiguous(self):
        return len(self.children) > 1

    @property
    def children(self):
        if not self.paths_loaded: self.load_paths()
        return sorted(self._children, key=attrgetter('sort_key'))

    def __iter__(self):
        return iter(self._children)

    def __eq__(self, other):
        if not isinstance(other, SymbolNode):
            return False
        return self is other or (type(self.s) == type(other.s) and self.s == other.s and self.start == other.start and self.end is other.end)

    def __hash__(self):
        return self._hash

    def __repr__(self):
        if self.is_intermediate:
            rule = self.s[0]
            ptr = self.s[1]
            before = ( expansion.name for expansion in rule.expansion[:ptr] )
            after = ( expansion.name for expansion in rule.expansion[ptr:] )
            symbol = "{} ::= {}* {}".format(rule.origin.name, ' '.join(before), ' '.join(after))
        else:
            symbol = self.s.name
        return "({}, {}, {}, {})".format(symbol, self.start, self.end, self.priority)

class PackedNode(ForestNode):
    """
    A Packed Node represents a single derivation in a symbol node.
    """
    __slots__ = ('parent', 's', 'rule', 'start', 'left', 'right', 'priority', '_hash')
    def __init__(self, parent, s, rule, start, left, right):
        self.parent = parent
        self.s = s
        self.start = start
        self.rule = rule
        self.left = left
        self.right = right
        self.priority = float('-inf')
        self._hash = hash((self.left, self.right))

    @property
    def is_empty(self):
        return self.left is None and self.right is None

    @property
    def sort_key(self):
        """
        Used to sort PackedNode children of SymbolNodes.
        A SymbolNode has multiple PackedNodes if it matched
        ambiguously. Hence, we use the sort order to identify
        the order in which ambiguous children should be considered.
        """
        return self.is_empty, -self.priority, self.rule.order

    @property
    def children(self):
        return filter(lambda x: x is not None, [self.left, self.right])

    def __iter__(self):
        return iter([self.left, self.right])

    def __eq__(self, other):
        if not isinstance(other, PackedNode):
            return False
        return self is other or (self.left == other.left and self.right == other.right)

    def __hash__(self):
        return self._hash

    def __repr__(self):
        if isinstance(self.s, tuple):
            rule = self.s[0]
            ptr = self.s[1]
            before = ( expansion.name for expansion in rule.expansion[:ptr] )
            after = ( expansion.name for expansion in rule.expansion[ptr:] )
            symbol = "{} ::= {}* {}".format(rule.origin.name, ' '.join(before), ' '.join(after))
        else:
            symbol = self.s.name
        return "({}, {}, {}, {})".format(symbol, self.start, self.priority, self.rule.order)

class ForestVisitor(object):
    """
    An abstract base class for building forest visitors.

    Use this as a base when you need to walk the forest.
    """

    def visit_token_node(self, node): pass
    def visit_symbol_node_in(self, node): pass
    def visit_symbol_node_out(self, node): pass
    def visit_packed_node_in(self, node): pass
    def visit_packed_node_out(self, node): pass
    def on_cycle(self, node, get_path): pass

    def visit(self, root):
        def make_get_path(node):
            """Create a function that will return a path from `node` to 
            the current position. Used for the `on_cycle` callback."""
            def get_path():
                index = len(path) - 1
                while id(path[index]) != id(node):
                    index -= 1
                return path[index:]
            return get_path

        # Visiting is a list of IDs of all symbol/intermediate nodes currently in
        # the stack. It serves two purposes: to detect when we 'recurse' in and out
        # of a symbol/intermediate so that we can process both up and down. Also,
        # since the SPPF can have cycles it allows us to detect if we're trying
        # to recurse into a node that's already on the stack (infinite recursion).
        visiting = set()

        # a list of nodes that are currently being visited
        # used for the `on_cycle` callback
        path = list()

        # We do not use recursion here to walk the Forest due to the limited
        # stack size in python. Therefore input_stack is essentially our stack.
        input_stack = deque([root])

        # It is much faster to cache these as locals since they are called
        # many times in large parses.
        vpno = getattr(self, 'visit_packed_node_out')
        vpni = getattr(self, 'visit_packed_node_in')
        vsno = getattr(self, 'visit_symbol_node_out')
        vsni = getattr(self, 'visit_symbol_node_in')
        vino = getattr(self, 'visit_intermediate_node_out', vsno)
        vini = getattr(self, 'visit_intermediate_node_in', vsni)
        vtn = getattr(self, 'visit_token_node')
        oc = getattr(self, 'on_cycle')

        while input_stack:
            current = next(reversed(input_stack))
            try:
                next_node = next(current)
            except StopIteration:
                input_stack.pop()
                continue
            except TypeError:
                ### If the current object is not an iterator, pass through to Token/SymbolNode
                pass
            else:
                if next_node is None:
                    continue

                if id(next_node) in visiting:
                    oc(next_node, make_get_path(next_node))
                    continue
                        
                input_stack.append(next_node)
                continue

            if not isinstance(current, ForestNode):
                vtn(current)
                input_stack.pop()
                continue

            current_id = id(current)
            if current_id in visiting:
                if isinstance(current, PackedNode):    
                    vpno(current)
                elif current.is_intermediate:
                    vino(current)
                else:
                    vsno(current)
                input_stack.pop()
                path.pop()
                visiting.remove(current_id)
                continue
            else:
                visiting.add(current_id)
                path.append(current)
                if isinstance(current, PackedNode): 
                    next_node = vpni(current)
                elif current.is_intermediate:
                    next_node = vini(current)
                else:
                    next_node = vsni(current)
                if next_node is None:
                    continue

                if not isinstance(next_node, ForestNode) and \
                        not isinstance(next_node, Token):
                    next_node = iter(next_node)
                elif id(next_node) in visiting:
                    oc(next_node, make_get_path(next_node))
                    continue

                input_stack.append(next_node)
                continue

class ForestTransformer(ForestVisitor):
    """The base class for a bottom-up forest transformation.
    Transformations are applied via inheritance and overriding of the
    following methods:

    transform_symbol_node
    transform_intermediate_node
    transform_packed_node
    transform_token_node

    `transform_token_node` receives a Token as an argument.
    All other methods receive the node that is being transformed and
    a list of the results of the transformations of that nodes children.

    If `Discard` is raised in a transformation, no data from that node
    will be passed to its parent's transformation.
    """

    def __init__(self):
        # results of transformations
        self.data = dict()
        # used to track parent nodes
        self.node_stack = deque()

    def transform(self, root):
        self.node_stack.append('result')
        self.data['result'] = []
        self.visit(root)
        assert len(self.data['result']) <= 1
        if self.data['result']:
            return self.data['result'][0]

    def transform_symbol_node(self, node, data):
        return node

    def transform_intermediate_node(self, node, data):
        return node

    def transform_packed_node(self, node, data):
        return node

    def transform_token_node(self, node):
        return node

    def visit_symbol_node_in(self, node):
        self.node_stack.append(id(node))
        self.data[id(node)] = []
        return node.children

    def visit_packed_node_in(self, node):
        self.node_stack.append(id(node))
        self.data[id(node)] = []
        return node.children

    def visit_token_node(self, node):
        try:
            self.data[self.node_stack[-1]].append(self.transform_token_node(node))
        except Discard:
            pass

    def visit_symbol_node_out(self, node):
        self.node_stack.pop()
        try:
            transformed = self.transform_symbol_node(node, self.data[id(node)])
            self.data[self.node_stack[-1]].append(transformed)
        except Discard:
            pass
        finally:
            del self.data[id(node)]

    def visit_intermediate_node_out(self, node):
        self.node_stack.pop()
        try:
            transformed = self.transform_intermediate_node(node, self.data[id(node)])
            self.data[self.node_stack[-1]].append(transformed)
        except Discard:
            pass
        finally:
            del self.data[id(node)]

    def visit_packed_node_out(self, node):
        self.node_stack.pop()
        try:
            transformed = self.transform_packed_node(node, self.data[id(node)])
            self.data[self.node_stack[-1]].append(transformed)
        except Discard:
            pass
        finally:
            del self.data[id(node)]


class ForestSumVisitor(ForestVisitor):
    """
    A visitor for prioritizing ambiguous parts of the Forest.

    This visitor is used when support for explicit priorities on
    rules is requested (whether normal, or invert). It walks the
    forest (or subsets thereof) and cascades properties upwards
    from the leaves.

    It would be ideal to do this during parsing, however this would
    require processing each Earley item multiple times. That's
    a big performance drawback; so running a forest walk is the
    lesser of two evils: there can be significantly more Earley
    items created during parsing than there are SPPF nodes in the
    final tree.
    """
    def visit_packed_node_in(self, node):
        return iter([node.left, node.right])

    def visit_symbol_node_in(self, node):
        return iter(node.children)

    def visit_packed_node_out(self, node):
        priority = node.rule.options.priority if not node.parent.is_intermediate and node.rule.options.priority else 0
        priority += getattr(node.right, 'priority', 0)
        priority += getattr(node.left, 'priority', 0)
        node.priority = priority

    def visit_symbol_node_out(self, node):
        node.priority = max(child.priority for child in node.children)

class ForestToParseTree(ForestTransformer):
    """Used by the earley parser when ambiguity equals 'resolve' or
    'explicit'. Transforms an SPPF into an (ambiguous) parse tree.

    tree_class: The Tree class to use for construction
    callbacks: A dictionary of rules to functions that output a tree
    prioritizer: A ForestVisitor that manipulates the priorities of
        ForestNodes
    resolve_ambiguity: If True, ambiguities will be resolved based on
        priorities. Otherwise, `_ambig` nodes will be in the resulting
        tree.
    """

    def __init__(self, tree_class=Tree, callbacks=dict(), prioritizer=ForestSumVisitor(), resolve_ambiguity=True):
        super(ForestToParseTree, self).__init__()
        self.tree_class = tree_class
        self.callbacks = callbacks
        self.prioritizer = prioritizer
        self.resolve_ambiguity = resolve_ambiguity
        self._on_cycle_retreat = False

    def on_cycle(self, node, get_path):
        logger.warning("Cycle encountered in the SPPF at node: %s. "
                "As infinite ambiguities cannot be represented in a tree, "
                "this family of derivations will be discarded.", node)
        if self.resolve_ambiguity:
            # TODO: choose a different path if cycle is encountered
            logger.warning("At this time, using ambiguity resolution for SPPFs "
                    "with cycles may result in None being returned.")
        self._on_cycle_retreat = True

    def _check_cycle(self, node):
        if self._on_cycle_retreat:
            raise Discard

    def _collapse_ambig(self, children):
        new_children = []
        for child in children:
            if hasattr(child, 'data') and child.data == '_ambig':
                new_children += child.children
            else:
                new_children.append(child)
        return new_children

    def _call_rule_func(self, node, data):
        # called when transforming children of symbol nodes
        # data is a list of trees that are children of the symbol
        return self.callbacks[node.rule](data)

    def _call_ambig_func(self, node, data):
        # called when transforming a symbol node
        # data is a list of trees where each tree's data is 
        # equal to the name of the symbol
        if len(data) > 1:
            return self.tree_class('_ambig', data)
        elif data:
            return data[0]
        return self.tree_class(node.s.name, [])

    def transform_symbol_node(self, node, data):
        self._check_cycle(node)
        data = self._collapse_ambig(data)
        return self._call_ambig_func(node, data)

    def transform_intermediate_node(self, node, data):
        self._check_cycle(node)
        if len(data) > 1:
            children = [self.tree_class('_inter', c) for c in data]
            return self.tree_class('_iambig', children)
        return data[0]

    def transform_packed_node(self, node, data):
        self._check_cycle(node)
        children = list()
        assert len(data) <= 2
        if node.left:
            if node.left.is_intermediate and isinstance(data[0], list):
                children += data[0]
            else:
                children.append(data[0])
            if len(data) > 1:
                children.append(data[1])
        elif data:
            children.append(data[0])
        if node.parent.is_intermediate:
            return children
        return self._call_rule_func(node, children)

    def visit_symbol_node_in(self, node):
        self._on_cycle_retreat = False
        super(ForestToParseTree, self).visit_symbol_node_in(node)
        if self.prioritizer and node.is_ambiguous and isinf(node.priority):
            self.prioritizer.visit(node)
        if self.resolve_ambiguity:
            return node.children[0]
        return node.children

    def visit_packed_node_in(self, node):
        self._on_cycle_retreat = False
        return super(ForestToParseTree, self).visit_packed_node_in(node)

    def visit_token_node_in(self, node):
        self._on_cycle_retreat = False
        return super(ForestToParseTree, self).visit_token_node_in(node)


def handles_ambiguity(func):
    """Decorator for methods of subclasses of TreeForestTransformer.
    Denotes that the method should receive a list of trees (derivations)."""
    func.handles_ambiguity = True
    return func

class TreeForestTransformer(ForestToParseTree):
    """A ForestTransformer with a tree-like Transformer interface.
    By default, it will construct a tree.

    Methods provided via inheritance are called based on the rule/symbol
    names of nodes in the forest.

    Methods that act on rules will receive a list of the results of the 
    transformations of the rules children. By default, trees and tokens.

    Methods that act on tokens will receive a Token.

    Alternatively, methods that act on rules may be annotated with
    `handles_ambiguity`. In this case, the function will receive a list
    of all the transformations of all the derivations of the rule. 
    By default, a list of trees where each tree.data is equal to the 
    rule name.

    Transformation to any object is made possible by override of 
    `__default__`, `__default_token__`, and `__default_ambig__`.
    """

    def __init__(self, tree_class=Tree, prioritizer=ForestSumVisitor(), resolve_ambiguity=True):
        super(TreeForestTransformer, self).__init__(tree_class, dict(), prioritizer, resolve_ambiguity)

    def __default__(self, name, data):
        """Default operation on tree (for override).
        
        Returns a tree with name with data as children.
        """
        return self.tree_class(name, data)

    def __default_ambig__(self, name, data):
        """Default operation on ambiguous rule (for override).
        
        Wraps data in an '_ambig_ node if it contains more than
        one element.'
        """
        try:
            if len(data) > 1:
                return self.tree_class('_ambig', data)
            elif data:
                return data[0]
            return self.tree_class(name, [])
        except TypeError:
            return data

    def __default_token__(self, node):
        """Default operation on Token (for).
        
        Returns node
        """
        return node

    def transform_token_node(self, node):
        return getattr(self, node.type, self.__default_token__)(node)

    def _call_rule_func(self, node, data):
        name = node.rule.alias or node.rule.options.template_source or node.rule.origin.name
        user_func = getattr(self, name, self.__default__) 
        if user_func == self.__default__ or hasattr(user_func, 'handles_ambiguity'):
            user_func = partial(self.__default__, name)
        if not self.resolve_ambiguity:
            wrapper = partial(AmbiguousIntermediateExpander, self.tree_class)
            user_func = wrapper(user_func)
        return user_func(data)

    def _call_ambig_func(self, node, data):
        name = node.s.name
        user_func = getattr(self, name, self.__default_ambig__)
        if user_func == self.__default_ambig__ or not hasattr(user_func, 'handles_ambiguity'):
            user_func = partial(self.__default_ambig__, name)
        return user_func(data)

class ForestToPyDotVisitor(ForestVisitor):
    """
    A Forest visitor which writes the SPPF to a PNG.

    The SPPF can get really large, really quickly because
    of the amount of meta-data it stores, so this is probably
    only useful for trivial trees and learning how the SPPF
    is structured.
    """
    def __init__(self, rankdir="TB"):
        self.pydot = import_module('pydot')
        self.graph = self.pydot.Dot(graph_type='digraph', rankdir=rankdir)

    def visit(self, root, filename):
        super(ForestToPyDotVisitor, self).visit(root)
        self.graph.write_png(filename)

    def visit_token_node(self, node):
        graph_node_id = str(id(node))
        graph_node_label = "\"{}\"".format(node.value.replace('"', '\\"'))
        graph_node_color = 0x808080
        graph_node_style = "\"filled,rounded\""
        graph_node_shape = "diamond"
        graph_node = self.pydot.Node(graph_node_id, style=graph_node_style, fillcolor="#{:06x}".format(graph_node_color), shape=graph_node_shape, label=graph_node_label)
        self.graph.add_node(graph_node)

    def visit_packed_node_in(self, node):
        graph_node_id = str(id(node))
        graph_node_label = repr(node)
        graph_node_color = 0x808080
        graph_node_style = "filled"
        graph_node_shape = "diamond"
        graph_node = self.pydot.Node(graph_node_id, style=graph_node_style, fillcolor="#{:06x}".format(graph_node_color), shape=graph_node_shape, label=graph_node_label)
        self.graph.add_node(graph_node)
        return iter([node.left, node.right])

    def visit_packed_node_out(self, node):
        graph_node_id = str(id(node))
        graph_node = self.graph.get_node(graph_node_id)[0]
        for child in [node.left, node.right]:
            if child is not None:
                child_graph_node_id = str(id(child))
                child_graph_node = self.graph.get_node(child_graph_node_id)[0]
                self.graph.add_edge(self.pydot.Edge(graph_node, child_graph_node))
            else:
                #### Try and be above the Python object ID range; probably impl. specific, but maybe this is okay.
                child_graph_node_id = str(randint(100000000000000000000000000000,123456789012345678901234567890))
                child_graph_node_style = "invis"
                child_graph_node = self.pydot.Node(child_graph_node_id, style=child_graph_node_style, label="None")
                child_edge_style = "invis"
                self.graph.add_node(child_graph_node)
                self.graph.add_edge(self.pydot.Edge(graph_node, child_graph_node, style=child_edge_style))

    def visit_symbol_node_in(self, node):
        graph_node_id = str(id(node))
        graph_node_label = repr(node)
        graph_node_color = 0x808080
        graph_node_style = "\"filled\""
        if node.is_intermediate:
            graph_node_shape = "ellipse"
        else:
            graph_node_shape = "rectangle"
        graph_node = self.pydot.Node(graph_node_id, style=graph_node_style, fillcolor="#{:06x}".format(graph_node_color), shape=graph_node_shape, label=graph_node_label)
        self.graph.add_node(graph_node)
        return iter(node.children)

    def visit_symbol_node_out(self, node):
        graph_node_id = str(id(node))
        graph_node = self.graph.get_node(graph_node_id)[0]
        for child in node.children:
            child_graph_node_id = str(id(child))
            child_graph_node = self.graph.get_node(child_graph_node_id)[0]
            self.graph.add_edge(self.pydot.Edge(graph_node, child_graph_node))
