class Parameter:
    name = ""
    declaration = []

def parse_parameter_list(p, tokens):
    """
    Given a string of tokens parse it into a tree of parameters.

    For example:

    int a, b, float *c
    """

    #print(" ".join([x.value for x in tokens]))
    
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
        elif tok.kind == p.TOKEN and tok.value == "const":
            pass # we ignore const
        else:
            param += [tok]

    if param:
        params += [param]

    params2 = []
    prev = None
    for ptokens in params:
        par = Parameter()
        par.bitfield = None
        
        if len(ptokens) == 1:
            par.declaration = prev.declaration
            par.name = ptokens[0].value
            params2.append(par)
            continue
        if len(ptokens) == 2 and ptokens[0].kind == p.SYMBOL and ptokens[0].value == "*":
            par.declaration = prev.declaration + [ptokens[0]]
            par.name = ptokens[1].value
            params2.append(par)
            continue

        if len(ptokens) == 3:
            for i in range(3):
                if ptokens[i].kind != p.SYMBOL or ptokens[i].value != ".":
                    break
            else:
                par.declaration = ptokens
                par.name = ""
                params2.append(par)
                continue

        last = ptokens[-1]
        if len(ptokens) >= 3 and last.kind == p.TOKEN and\
            last.value[0] in "0123456789" and ptokens[-2].value == "with":
            par.declaration = ptokens[:-3]
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
            par.declaration = ptokens[:i + 1] + ptokens[i + 2:]
            par.name = ptokens[i + 1].value
        elif last.value == "]":
            # e.g. int x[12]
            for i in range(len(ptokens)):
                if ptokens[i].value == "[":
                    break
            par.declaration = ptokens[:i - 1] + ptokens[i:]
            par.name = ptokens[i - 1].value
        else:
            par.name = last.value
            par.declaration = ptokens[:-1]

        params2.append(par)
        prev = par

    #print(": " + ", ".join([" ".join([y.value for y in x.declaration]) + " " + x.name for x in params2]))
    return params2
