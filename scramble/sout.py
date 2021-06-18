class SWriter:
    def __init__(self):
        pass

    def statement(self):
        p = self.p
        while self.stack:
            tok = self.stack.pop(0)
            if self.line: self.line += " "
            if tok == None:
                self.line += "POSTFIX"
            elif isinstance(tok, str):
                self.line += tok
            elif tok.kind == p.OPERATOR:
                self.stack = ["«"] + list(tok.value) + ["»"] + self.stack
            elif tok.kind == p.STRING:
                self.line += tok.value
            elif tok.kind == p.SYMBOL:
                self.line += tok.value
            elif tok.kind == p.TOKEN:
                self.line += tok.value
            else:
                self.line += "<unknown_%d>" % tok.kind

    def write_line(self, s, kind, colon):
        p = self.p
        self.line = ""
        self.stack = []
        for tok in s.value:
            self.stack.append(tok)
        self.statement()
        self.code += kind
        self.code += self.indent * "    " + self.line + ("\n" if colon else "\n")

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
                self.write_line(s, "STAT " + s.name.value + " ", True)
                if s.name.value == "for":
                    if s.sub_kind in ["range", "in", "while"]:
                        self.stack.append(s.part)
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
