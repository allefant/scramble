from . import analyzer
from . import parser

class Parameter:
    name = ""
    declaration = []

    def as_variable(self):
        return analyzer.Variable(self.name, self.declaration)

    def __repr__(self):
        return self.name

"""
Returns the number of * before the variable.
"""
def pointer_indirection(tokens, p):
    i = 0
    par = 0
    for tok in tokens:
        if type(tok) == str:
            p.error(f"Unexpected token {tok}!")
        if tok.kind == p.SYMBOL:
            if tok.value == "(":
                par += 1
            if tok.value == ")":
                par -= 1
            if tok.value == "*":
                if par == 0:
                    i += 1
    return i

"""
Given a parameter, see if it has a pointer named name.
"""
def get_pointer_member(x : Parameter, name : str, p):
    d = x.declaration.value
    if d[0].kind == p.SYMBOL:
        if d[0].value == "*":
            t = p.analyzer.types.get(d[1].value)
            if t is not None:
                for v in t.block.variables:
                    if v.name == name:
                        return v
            else:
                t = p.external_types.get(d[1].value)
                if t:
                    for v in t.variables:
                        if v.name == name:
                            return v
    return None

def parse_parameter_list(p, tokens):
    """
    Given a string of tokens parse it into a tree of parameters.

    For example:

    int a, b, float *c
    """

    #print(" ".join([x.value for x in tokens]))

    # split at , but leaving ()
    params = []
    param = []
    balance = 0
    for tok in tokens:
        if tok.kind == p.SYMBOL and tok.value == "(":
            param += [tok]
            balance += 1
        elif tok.kind == p.SYMBOL and tok.value == ")":
            if balance == 0: break
            balance -= 1
            param += [tok]
        elif tok.kind == p.SYMBOL and tok.value == ",":
            if balance > 0: param += [tok]
            elif param:
                params += [param]
                param = []
        else:
            param += [tok]

    if param:
        params += [param]

    params2 = []
    prev = None

    def prev_declaration():
        if not prev:
            return []
        name = prev.name
        i = 0
        for i in range(len(prev.declaration)):
            if prev.declaration[i].kind == p.SYMBOL:
                if prev.declaration[i].value == "*":
                    return prev.declaration[:i]
            if prev.declaration[i].kind == p.TOKEN:
                if prev.declaration[i].value == name:
                    return prev.declaration[:i]
        return prev.declaration

    for ptokens in params:
        par = Parameter()
        par.bitfield = None
        is_pointer = False

        if ptokens[0].kind == p.SYMBOL and ptokens[0].value == "...":
            par.declaration = [ptokens[0]]
            par.name = ptokens[0].value
            params2.append(par)
            continue

        if ptokens[0].kind == p.SYMBOL and ptokens[0].value == "*":
            is_pointer = True
        
        if len(ptokens) == 1:
            par.declaration = prev_declaration() + [ptokens[0]]
            par.name = ptokens[0].value
            params2.append(par)
            continue

        if is_pointer:
            par.declaration = prev_declaration()
        else:
            par.declaration = []

        last = ptokens[-1]
        if len(ptokens) >= 3 and last.kind == p.TOKEN and\
            last.value[0] in "0123456789" and ptokens[-2].value == "with":
            par.declaration += ptokens[:-2]
            par.name = ptokens[-3].value
            par.bitfield = last.value
        elif last.value == ")":

            # e.g. void (*x)(int z)
            for i in range(len(ptokens)):
                if ptokens[i].value == "(":
                    break
            for i in range(i + 1, len(ptokens)):
                if ptokens[i].value == "*":
                    break
            par.declaration += ptokens
            par.name = ptokens[i + 1].value
        elif last.value == "]":
            # e.g. int x[12]
            for i in range(len(ptokens)):
                if ptokens[i].value == "[":
                    break
            par.declaration += ptokens
            par.name = ptokens[i - 1].value
        else:
            par.name = last.value
            par.declaration += ptokens

        if par.name == "*":
            par.declaration += [p.unnamed_token]
        params2.append(par)
        prev = par

    #print(": " + ", ".join([" ".join([y.value for y in x.declaration]) + " " + x.name for x in params2]))

    return params2    

# tokens[x] is an open parenthesis. Return y so that tokens[y] is the matching
# closing parenthesis or else None.
def find_matching_parenthesis(p, tokens, x):
    balance = 0
    y = x
    while y < len(tokens):
        if tokens[y].kind == p.SYMBOL:
            if tokens[y].value == "(":
                if balance == 0 and y != x: # did not start at a (
                    return None
                balance += 1
            if tokens[y].value == ")":
                balance -= 1
                if balance == 0:
                    return y
        y += 1
    return None

# In something like a.b.c.d return [a, b, c, d]
def find_dots(p : "Parser", token : "Node"):
    r = []
    def go_up(x):
        if x.kind == p.OPERATOR:
            if len(x.value) >= 3 and x.value[0].kind == p.SYMBOL:
                if x.value[0].value == ".":
                    r.insert(0, x.value[2])
                    if not x.value[1]:
                        p.error_token("Need name after dot!", x)
                    go_up(x.value[1])
                    return
        r.insert(0, x)
    go_up(token)
    return r

def tree_to_list(p, t):
    is_sym = analyzer.Analyzer.is_sym
    r = []
    stack = [t]
    while stack:
        node = stack.pop()
        if node.kind == p.OPERATOR:
            if is_sym(node.value[0], ","):
                stack.append(node.value[2])
                stack.append(node.value[1])
            else:
                r.append(node)
        else:
            r.append(node)
    return r

def list_to_tree(p, l):
    pos = 1
    node = l[0]
    while pos < len(l):
        b = l[pos]
        comma = parser.Token(p.SYMBOL, ",", 0, 0)
        node = parser.Node(p.OPERATOR, [comma, node, b])
        pos += 1
    return node

# This gets an expression and tries to deduce the type.
# For example if we have:
# A *a
# fun f -> B*
# class A:
#   C *c
# A *c
# then these would be the return values:
# 1. a -> A*
# 2. c.c -> C*
# 3. f() -> B*
def find_type(self, expression):
    # detect form auto foo.bar
    dot = None
    if expression.kind == self.p.OPERATOR and is_sym(expression.value[0], "."):
        var = expression.value[1].value # foo in example above
        dot = expression.value[2].value # bar in example above
        # FIXME: detect arbitrary chain of . not just the first
    else:
        var = expression.value

    v = self.find_variable(var)
    if v:
        if dot:
            tname = v.get_type()
            if tname.endswith("*"): tname = tname[:-1]
            t = self.p.analyzer.types.get(tname, None)
            if t:
                for v2 in t.block.variables:
                    if v2.name == dot:
                        v = v2
            if not t:
                t = self.p.external_types.get(tname, None)
                if t:
                    for v2 in t.variables:
                        if v2.name == dot:
                            v = v2
        return list(v.declaration.value)[:-1]
    else:
        if isinstance(expression.value[0], str):
            self.p.error_token("Unexpected token ", expression)
        else:
            f = self.find_function(expression.value[0].value)
            if f:
                if not f.ret:
                    self.p.error_token("Cannot determine function return type", expression)
                if len(f.ret) < 2:
                    self.p.error_token("Right now auto only works with pointers", expression)
                return [f.ret[1], f.ret[0]]
