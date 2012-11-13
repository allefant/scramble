class SWriter:
    def __init__(self):
        pass

    def statement(self, row):
        p = self.p
        line = ""
        for tok in row:
            if line: line += " "
            if tok == None:
                line += "POSTFIX"
            elif tok.kind == p.OPERATOR:
                line += "«"
                line += self.statement(tok.value)
                line += "»"
            elif tok.kind == p.STRING:
                line += tok.value
            elif tok.kind == p.SYMBOL:
                line += tok.value
            elif tok.kind == p.TOKEN:
                line += tok.value
            else:
                line += "<unknown_%d>" % tok.kind
        return line

    def write_line(self, s, kind, colon):
        p = self.p
        line = ""
        line += self.statement(s.value)
        self.code += kind
        self.code += self.indent * "    " + line + ("\n" if colon else "\n")

    def write_block(self, b):
        if not b:
            return
        p = self.p
        for i in range(len(b.value)):
            next = None
            if i < len(b.value) - 1:
                next = b.value[i + 1]
            s = b.value[i]
            if s.kind == p.LINE:
                self.write_line(s, "LINE ", next and next.kind == p.BLOCK)
            elif s.kind == p.STATEMENT:
                self.write_line(s, "STAT ", True)
                if s.name.value == "for":
                    if s.sub_kind in ["range", "in", "while"]:
                        self.code += self.indent * "    " + "     " +\
                            self.statement(s.part) + "\n"
                self.indent += 1
                self.write_block(s.block)
                self.indent -= 1
            elif s.kind == p.BLOCK:
                self.indent += 1
                self.write_block(s)
                self.indent -= 1
            elif s.kind == p.FUNCTION:
                self.write_line(s, "FUNC ", True)
                if s.block:
                    self.indent += 1
                    self.write_block(s.block)
                    self.indent -= 1
            elif s.kind == p.MACRO:
                self.write_line(s, "MACR ", True)
                if s.block:
                    self.indent += 1
                    self.write_block(s.block)
                    self.indent -= 1
            elif s.kind == p.TYPE:
                self.write_line(s, "TYPE ", True)
                self.indent += 1
                self.write_block(s.block)
                self.indent -= 1
            elif s.kind == p.IMPORT: self.write_line(s, "IMPO ", True)
            elif s.kind == p.LABEL: self.write_line(s, "LABE ", True)
            elif s.kind == p.GOTO: self.write_line(s, "GOTO ", True)
            elif s.kind == p.PREPROCESSOR: self.write_line(s, "PREP ", True)
            elif s.kind == p.INCLUDE:
                self.code += "include\n"
                self.write_block(s.value.root)
            else:
                self.code += "unknown_%d\n" % s.kind

    def generate(self, p):
        self.p = p
        self.indent = 0
        self.code = ""
        self.write_block(p.root)
        return self.code
