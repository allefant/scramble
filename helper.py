import analyzer

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
                    go_up(x.value[1])
                    return
        r.insert(0, x)
    go_up(token)
    return r
