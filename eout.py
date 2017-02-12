class EWriter:
    def write_type_info(self):
        a = self.p.analyzer
        for t in a.types:
            self.code += str(t) + "\n"
            if a.types[t].block:
                for v in a.types[t].block.variables:
                    self.code += "    " + str(v.name) + " : " + v.get_type() + "\n"

    def write_variables(self):
        for v in self.p.root.variables:
            if v.declaration.is_global:
                self.code += str(v.name) + " : " + v.get_type() + "\n"

    def generate(self, p):
        self.p = p
        self.code = ""
        self.write_type_info()
        self.write_variables()
        return self.code
