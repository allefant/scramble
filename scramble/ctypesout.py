from . import helper

class CTypesWriter:
    def __init__(self):
        self.typedefs = []

    def ctype(self, t):
        """
        Given a C type (without variable name) return the ctypes type.
        For function pointers/arrays they look like for example
            "int(*)(int,int)"
            "int[10][10]"
        """

        # For now if we see a function pointer just use c_void_p.
        if t.endswith(")"):
            return "c_void_p"

        is_pointer = False
        if t.endswith("]"):
            i = t.find("[")
            if i >= 0:

                count = t[i + 1:-1].strip()
                if not count:
                    is_pointer = True
                    t = t[:i].rstrip()
                else:
                    array_type = self.ctype(t[:i].strip())
                    return array_type + " * " + count
        
        if t.endswith("*"):
            if is_pointer: return "c_void_p"
            is_pointer = True
            t = t[:-1].rstrip(" ")
            if t.endswith("*"):
                return "c_void_p" # pointer to pointer

        if t.startswith("struct"):
            t = t[len("struct"):].strip()

        if t == ". . .":
            return "c_void_p"

        rt = None
        if t == "int": rt = "c_int"
        elif t == "int32_t": rt = "c_int"
        elif t == "unsigned int": rt = "c_uint"
        elif t == "unsigned char": rt = "c_ubyte"
        elif t == "uint32_t": rt = "c_uint32"
        elif t == "uint16_t": rt = "c_uint16"
        elif t == "float": rt = "c_float"
        elif t == "double": rt = "c_double"
        elif t == "bool": rt = "c_bool"
        elif t == "void": rt = "c_void"
        elif t == "size_t": rt = "c_size_t"
        elif t == "FILE": rt = "c_void"
        elif t == "char": rt = "c_char"

        if rt:
            if is_pointer:
                if rt in ["c_char", "c_void"]:
                    return rt + "_p"
                return "POINTER(" + rt + ")"
            else: return rt

        if is_pointer:
            if t == "char": return "c_char_p"
            return "LP_" + t
        return t

    def function(self, tokens):
        state = "ret"
        p = self.p
        "int def land_get_clip(float *cx1, float *cy1, float *cx2, float *cy2):"
        ret = []
        name = "?"
        params = []
        for i, tok in enumerate(tokens):
            if state == "ret":
                if tok.kind == p.TOKEN and tok.value == "def":
                    state = "name"
                elif tok.kind == p.TOKEN and tok.value == "const":
                    pass
                else:
                    ret += [tok]
            elif state == "name":
                name = tok.value
                state = "params"
                balance = 0
            else:
                if tok.kind == p.SYMBOL and tok.value == "(":
                    pass
                else:
                    params = helper.parse_parameter_list(p, tokens[i:])
                    break

        params2 = []
        for param in params:
            v = " ".join([x.value for x in param.declaration])
            params2.append(self.ctype(v))

        params = params2

        s = name + " = load_function("
        s += '"' + name + '"'
        s += ", "
        if ret: s += self.ctype(" ".join([x.value for x in ret]))
        else: s += "c_int"
        s += ", ["

        first = True
        for param in params:
            if first:
                first = False
            else:
                s += ", "
            s += param
        s += "])"
        return s

    def struct(self, tokens, block):
        p = self.p

        class TypeDef: pass
        class Field: pass
        t = TypeDef()

        # Example: ["class", "Foo", ":"]
        t.name = tokens[1].value
        t.base = "Structure" if tokens[0].value == "class" else "Union"
        t.fields = []
        for line in block.value:
            if line.value[0].kind == p.STRING: # docstring
                continue

            fields = helper.parse_parameter_list(p, line.value)

            for field in fields:
                f = Field()
                f.name = field.name
                decl = " ".join([x.value for x in field.declaration])
                f.type = self.ctype(decl)
                f.bitfield = field.bitfield
                t.fields.append(f)
        
        self.typedefs.append(t)

    def enum(self, tokens, block):
        p = self.p
        class Enum: pass
        class Value: pass
        e = Enum()
        if len(tokens) > 1:
            e.name = tokens[1].value
        else:
            e.name = ""
        e.values = []
        i = 0
        for line in block.value:
            v = Value()
            v.name = line.value[0].value
            if len(line.value) == 3 and line.value[1].value == "=":
                v.value = line.value[2].value
                if v.value.startswith("'"):
                    v.value = ord(v.value[1])
                else:
                    v.value = int(v.value)
                i = v.value
            else:
                v.value = str(i)
                i += 1
            e.values.append(v)
        
        self.enums.append(e)

    def typedef(self, tokens):
        class Typedef: pass
        class Value: pass
        t = Typedef()
        t.name = ""
        t.values = []
        v = Value()
        v.name = tokens[-1].value
        v.value = self.ctype(" ".join([x.value for x in tokens[1:-1]]))
        t.values.append(v)
        self.enums.append(t)

    def write_line(self, s, block):
        p = self.p
        prev = None
        line = ""
        tokens = s.value[:]

        if not tokens: return
        if tokens[0].kind == p.STRING: # docstring
            return

        if tokens[0].value == "static":
            return

        if tokens[0].value == "***":
            return

        if tokens[0].value == "import":
            return

        if tokens[0].value == "extern":
            return

        if tokens[0].value == "global":
            # We don't support global variables for now.
            return

        if tokens[0].value == "macro":
            # FIXME:
            # For just defining numbers we can use enums.
            # For macro functions dunno, probably they should just be
            # recreated in Python - so no need to have them in the
            # auto-generated ctypes file.
            return

        elif tokens[0].value in ["class", "union"]:
            self.struct(tokens, block)
        elif tokens[0].value == "enum":
            self.enum(tokens, block)
        elif tokens[0].value == "typedef":
            self.typedef(tokens)
        else:
            is_function = False
            for tok in tokens:
                if tok.kind == p.TOKEN and tok.value == "def":
                    is_function = True

            if is_function:
                line = self.function(tokens)
            else:
                line = ">>> " + tokens[0].value

        if line:
            self.code += line + "\n"

    def write_block(self, b):
        p = self.p
        for i in range(len(b.value)):
            block = None
            if i < len(b.value) - 1:
                block = b.value[i + 1]
                if block.kind != p.BLOCK: block = None
            s = b.value[i]
            if s.kind == p.LINE:
                self.write_line(s, block)
            elif s.kind == p.INCLUDE:
                self.p = s.value
                self.write_block(self.p.root)
                self.p = p

    def generate(self, p):
        self.p = p
        self.enums = []
        self.code = ""
        self.write_block(p.root)

        code = """# don't modify, generated with scramble.py
from ctypes import *

"""

        for e in self.enums:
            if e.name:
                code += e.name + " = c_int\n"
            for v in e.values:
                code += v.name + " = " + str(v.value) + "\n"
        
        code += "\n"
        
        for t in self.typedefs:
            code += "class " + t.name + "(" + t.base + "): pass\n"
            code += "LP_" + t.name + " = POINTER(" + t.name + ")\n"

        code += "\n"

        for t in self.typedefs:
            code += t.name + "._fields_ = [\n"
            for f in t.fields:
                if f.bitfield:
                    code += "    (" + '"' + f.name + '", '+ f.type + ", " + f.bitfield + "),\n"
                else:
                    code += "    (" + '"' + f.name + '", '+ f.type + "),\n"
            code += "]\n"

        code += self.code
        return code
