
class Variable:
    def __init__(self, name, declaration):
        P = parser.Parser
        self.declaration = declaration
        if type(name) is str:
            self.name = name
        elif Analyzer.is_tok(name):
            self.name = name.value
        elif name.kind == P.OPERATOR:
            if Analyzer.is_sym(name.value[0], "*"):
                name = name.value[1]
            else:
                while name.kind == P.OPERATOR:
                    name = name.value[0]
            self.name = name.value
        else:
            self.name = name.value

    def __repr__(self):
        return self.name

    def replace_node(self, node, new_name):
        copies = []
        for token in node.value:
            if token.value == self.name:
                token = new_name
            copies.append(token)
        copy = parser.Node(node.kind, copies)
        return copy

    def replace(self, new_name):
        copy = self.replace_node(self.declaration, new_name)
        return copy

    def get_type(self):
        P = parser.Parser
        n = self.declaration
        if isinstance(n.value[0], str):
            if n.value[0] == ".":
               pass
            else:
                print(n)
            return n.value[0]
            
        if Analyzer.is_sym(n.value[0], "*"):
            star = "*"
            name = n.value[1]

            if len(n.value) > 2:
                op3 = n.value[2]
                if op3.kind == P.OPERATOR:
                    # TODO: We only detect ** pointers but not *** and so on
                    if Analyzer.is_sym(op3.value[0], "*"):
                        star += "*"
            
            if Analyzer.is_tok(name):
                return name.value + star
            elif name.kind == P.OPERATOR:
                if name.value[0].kind == P.TOKEN:
                    # something like: "char const *x" -> "char const*"
                    r = " ".join([v.value for v in name.value])
                    return r + star
        return ""
