from . import cout
import re
import time

class DWriter(cout.CWriter):
    def __init__(self):
        pass

    def pr(self, s):
        self.code += s

    def pl(self, s = ""):
        self.code += s + "\n"

    def fo(self, par):
        x = self.format_line([par.declaration])
        ms = []
        for m in re.finditer(r"\b" + par.name + r"\b", x):
            ms.append(m)
        for m in reversed(ms):
            x = x[:m.start()] + "**" + x[m.start():m.end()] + "**" + x[m.end():]
        return x

    def fo2(self, tokens):
        return self.format_line(tokens)

    def doc(self, s):
        p = self.p
        if s.value[0].kind != p.STRING:
            return False
        v = s.value[0].value
        if v.startswith('"""'):
            v = v[3:]
        if v.endswith('"""'):
            v = v[:-3]
        v = v.strip()
        self.pl(v)
        return True

    def write_block(self, b):
        if not b:
            return
        title = self.name.replace("/", ".")
        self.pl("% " + title)
        #self.pl("% Allefant")
        #self.pl("% " + time.ctime())
        self.pl()

        p = self.p
        for i in range(len(b.value)):
            s = b.value[i]
            if s.kind == p.LINE:
                self.doc(s)
                self.pl()
            if s.kind == p.FUNCTION and not s.is_static:
                link = "http://sourceforge.net/p/lland/land/ci/master/tree/src/"
                link += self.name[5:] + ".py#l" + str(s.value[0].row)
                self.pl("## [" + str(s.name.value) + "](" +
                    link + ")")
                if s.parameters:
                    self.pr("Parameters: ")
                    pars = [self.fo(par) for par in s.parameters]
                    self.pl(", ".join(pars))
                    self.pl()
                else:
                    self.pl("no parameters\n")
                if s.ret:
                    self.pr("Returns: ")
                    self.pl(self.fo2(s.ret))
                    self.pl()
                else:
                    #self.pl("no return\n")
                    pass
                doc = False
                if s.block:
                    first = s.block.value[0]
                    if first.kind == p.LINE:
                        doc = self.doc(first)
                if not doc:
                    #self.pl("no description\n")
                    pass
                self.pl()
            if s.kind == p.TYPE and not s.is_static:
                link = "http://sourceforge.net/p/lland/land/ci/master/tree/src/"
                link += self.name[5:] + ".py#l" + str(s.value[0].row)
                self.pl("## [" + str(s.name.value) + "](" +
                    link + ")")

                doc = False
                if s.block:
                    first = s.block.value[0]
                    if first.kind == p.LINE:
                        doc = self.doc(first)
                if not doc:
                    #self.pl("no description\n")
                    pass
                self.pl()
    def generate(self, p, name):
        self.p = p
        self.name = name
        self.code = ""
        self.write_block(p.root)
        return self.code

