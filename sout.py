class SWriter:
    def __init__(self):
        pass

    def write_line(self, s, colon):
        p = self.p
        prev = None
        line = ""
        for tok in s.value:
            word = tok.value
            if prev:
                if prev.kind == p.SYMBOL:
                    if tok.kind == p.SYMBOL:
                        if tok.value == "(" and prev.value != "(":
                            line += " "
                        else:
                            pass
                    else:
                        if prev.value in ["("]:
                            pass
                        else:
                            line += " "
                else:
                    if tok.kind == p.SYMBOL:
                        if tok.value in ["(", ")"]:
                            pass
                        else:
                            line += " "
                    else:
                        line += " "
            line += word
            prev = tok
        self.code += self.indent * "    " + line + (":\n" if colon else "\n")

    def write_block(self, b):
        p = self.p
        for i in range(len(b.value)):
            next = None
            if i < len(b.value) - 1:
                next = b.value[i + 1]
            s = b.value[i]
            if s.kind == p.LINE:
                self.write_line(s, next and next.kind == p.BLOCK)
            elif s.kind == p.BLOCK:
                self.indent += 1
                self.write_block(s)
                self.indent -= 1

    def generate(self, p):
        self.p = p
        self.indent = 0
        self.code = ""
        self.write_block(p.root)
        return self.code
