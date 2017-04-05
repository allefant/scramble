import parser, analyzer, helper

is_sym = analyzer.Analyzer.is_sym
is_op = analyzer.Analyzer.is_op
is_tok = analyzer.Analyzer.is_tok

class CWriter:

    note = "/* This file was generated by scramble.py. */\n"

    operator_hug_left = set((")", ",", ";", "++", "--", ".", "->", "[", "]", "}", "***"))
    operator_hug_right = set(("(", ".", "->", "--", "++", "[", "{", "***"))

    def first_line(self):
        if self.no_lines: return ""
        x = self.note
        x += "#line %d \"%s\"\n" % (1, self.p.filename)
        return x

    def add_header_line(self, code):
        if not self.no_lines and not self.in_macro:
            if self.out_hrow != self.in_row and not code.strip() in ("}", "};"):
                self.header += "#line %d\n" % self.in_row
                self.out_hrow = self.in_row
        self.header += code
        if self.in_macro: self.header += " \\"
        self.header += "\n"
        self.out_hrow += 1

    def add_code_line(self, code):
        if not self.no_lines and not self.in_macro:
            if self.out_crow != self.in_row and (
                code == None or code.strip() != "}"):
                self.code += "#line %d\n" % self.in_row
                self.out_crow = self.in_row
        if code == None: return
        self.code += code
        if self.in_macro: self.code += " \\"
        self.code += "\n"
        self.out_crow += 1

    def add_line(self, code):
        if self.in_header:
            self.add_header_line(code)
        else:
            self.add_code_line(code)

    def add_iline(self, code):
        self.add_line(self.indent * "    " + code)

    def handle_len(self, tok):
        op = self.stack[0] # function call operator
        if type(op) != parser.Node or op.kind != self.p.OPERATOR:
            self.p.error_token("len() needs an argument", tok)
        variable = op.value[1].value
        v = self.find_variable(variable)
        if not v:
            self.p.error_token("Cannot use len() on " + str(variable), tok)
        t = v.get_type()
        if t and t.endswith("*"):
            return t[:-1] + "__len__"
        return tok.value

    def format_op(self, tok):
        p = self.p

        word = tok.value
        if tok.kind == p.TOKEN:
            if word == "None": word = "NULL"
            elif word == "unnamed": word = ""
            elif word == "True": word = "1"
            elif word == "False": word = "0"
            elif word == "min": word = "_scramble_min"; self.need_min = True
            elif word == "max": word = "_scramble_max"; self.need_max = True
            elif word == "with": word = ":" # for bit fields
            elif word == "len": word = self.handle_len(tok)

        elif tok.kind == p.SYMBOL:
            if word == "***": word = "#" # macro string concatenation
            elif word == "not": word = "!"
            elif word == "and": word = "&&"
            elif word == "or": word = "||"
            elif word == "//": word = "/"

        elif tok.kind == p.STRING:
            if word.startswith("'''") or word.startswith('"""'):
                if word[-3:] == word[:3]:
                    new_word = ""
                    new_rows = word[3:-3].replace('"', '\\"').split("\n")
                    for i in range(len(new_rows)):
                        if i > 0: new_word += (1 + self.indent) * "    "
                        new_word += '"' + new_rows[i]
                        if i < len(new_rows) - 1:
                            new_word += '\\n"\n'
                        else:
                            new_word += '"'
                    word = new_word

        elif tok.kind == p.OPERATOR:
            self.stack = self.format_expression_as_list(tok) + self.stack
            return None
        elif tok.kind == p.COMMENT:
            word = "/*" + tok.value + " */"

        else:
            word = "???"

        if tok.comments:
            word += " /* "
            for ctok in tok.comments:
                word += ctok.value.strip()
            word += " */"

        return word

    def format_expression_as_list(self, token : parser.Node):
        """
        Given an operator node, return a list of tokens/nodes/strings to
        be passed to format_op.
        """
        p = self.p
        a = analyzer.Analyzer

        r = []

        if token.value[0].kind in [p.TOKEN, p.OPERATOR]:
            r = [token.value[0]]
            if token.value[1].kind == p.OPERATOR:
                if is_sym(token.value[1].value[0], "("):
                    r += []
                else:
                    r += [" "]
            else:
                # handles e.g. x = L'♥'
                if token.value[1].kind != p.STRING:
                    r += [" "]
            r += [token.value[1]]
            return r

        op = token.value[0].value
    
        left = None
        right = None
        extra = None

        if a.level[op] == 14: # postfix
            if token.value[1] is None:
                left = token.value[2]
            else:
                right = token.value[1]
                if len(token.value) > 2:
                    p.error_token("Operator '" + op + "' can't have two operands here.", token)
        else:
            if len(token.value) == 2:
                right = token.value[1]
            if len(token.value) == 3:
                if token.value[1] is None:
                    left = token.value[2]
                elif op in "([{":
                    right = token.value[1]
                    extra = token.value[2]
                else:
                    left = token.value[1]
                    right = token.value[2]

        if left:
            if left.kind == p.OPERATOR:
                if left.value[0].kind == p.SYMBOL:
                    leftop = left.value[0].value
                else:
                    leftop = " "
                if leftop in "([{" or a.precedence(leftop, op):
                    r += [left]
                else:
                    r += ["(", left, ")"]
            else:
                r += [left]
            if op not in self.operator_hug_left:
                r += [" "]

        operator_value = token.value[0]

        # If x is a pointer, return the type declaration, else None
        def is_pointer(x):
            if x.kind == p.TOKEN:
                # see if it is a pointer declared in the current block
                # or a parent block
                for b in self.current_block:
                    for parameter in b.variables:
                        if parameter.name == x.value:
                            if helper.pointer_indirection(
                                    parameter.declaration.value, p) > 0:
                                return parameter

                # see if it is a pointer from the parameter list
                if self.current_function:
                    for parameter in self.current_function[-1].parameters:
                        if parameter.name == x.value:
                            if helper.pointer_indirection(
                                    parameter.declaration.value, p) > 0:
                                return parameter

                # see if it is a global variable
                if x.value in p.external_variables:
                    return p.external_variables[x.value]
            return None
        
        # special recognition of . as ->
        if token.value[0].kind == p.SYMBOL:
            if token.value[0].value == ".":
                chain = helper.find_dots(p, token)
                param = is_pointer(chain[0])
                if not param:
                    chain = []
                for c in chain[1:-1]:
                    param = helper.get_pointer_member(param, c.value, p)
                    if not param:
                        break
                    if helper.pointer_indirection(param.declaration.value, p) > 0:
                        pass
                    else:
                        break
                else:
                    if param:
                        operator_value = "->"

        r += [operator_value]

        if right:
            if op not in self.operator_hug_right:
                r += " "
            if right.kind == p.OPERATOR:
                if right.value[0].kind == p.SYMBOL:
                    rightop = right.value[0].value
                else:
                    rightop = " "
                if rightop not in "([{" and a.precedence(op, rightop):
                    r += ["(", right, ")"]
                else:
                    r += [right]
            else:
                r += [right]

        if extra:
            r += [extra]

        if op == "//":
            r = ["(int)", "("] + r + [")"]
            
        return r

    def format_line(self, tokens):
        """
        Weave a formatted string out of a list of tokens.
        """
        self.stack = list(tokens)
        self.line = ""
        self.do_output()
        return self.line

    def do_output(self):
        prev = None
        while self.stack:
            tok = self.stack.pop(0)
            if isinstance(tok, str):
                self.line += tok
                prev = None
                continue

            if tok:
                self.in_row, _ = parser.get_row_col(tok)
            else:
                prev = None

            word = self.format_op(tok)
            if not word:
                prev = None
                continue
            if prev:
                if prev[-1].isalnum() and word[0].isalnum():
                    self.line += " "

            self.line += word
            prev = word

    def handle_function(self, node):
        no_decl = False
        p = self.p

        line = ""

        if node.is_static:
            line = "static "
            if node.ret and node.ret[0].value == "not":
                no_decl = True
                del node.ret[0]
        
        if node.ret:
            line += self.format_line(node.ret)
            line += " "
        else:
            line += "void "

        if node.is_pointer:
            line += "(*" + node.name.value + ")"
        else:
            line += node.name.value
        line += "("

        if node.parameters:
            plines = []
            for parameter in node.parameters:
                pline = ""
                pline += self.format_line([parameter.declaration])
                plines.append(pline)
            line += ", ".join(plines)                
        else:
            line += "void"

        line += ")"

        # Write prototype into header.
        if not self.in_macro and not node.parent_class:
            if node.is_static :
                # always forward declare static functions, just in
                # case - that way it's never required to do so
                if not no_decl:
                    self.static_cdecl += line + ";\n"
            else:
                self.add_header_line(line + ";")

        if node.block:
            self.add_line(self.indent * "    " + line + " {")
            self.indent += 1
            self.write_block(node.block)
            self.indent -= 1
            self.add_line(self.indent * "    " + "}")
        else:
            self.add_iline(line + ";");
        

    def handle_import(self, tokens, is_static):
        is_global = False
        name = ""

        condition = None
        names = []
        for tok in tokens:
            if condition is not None:
                condition += [tok.value]
            elif tok.value == "global" and not names:
                is_global = True
            elif tok.value == "if":
                condition = []
            elif tok.value == ",":
                names.append(name)
                name = ""
            elif tok.value in [".", "/"]:
                name += "/"
            else:
                name += tok.value
        names.append(name)

        for name in names:
            if is_global:
                word = "<" + name + ".h>"
            else:
                if self.p.ignore_local_imports: return
                word = '"' + name + '.h"'
            include = ""
            if condition:
                include += "#if " + " ".join(condition) + "\n"
            include += "#include " + word + "\n"
            if condition:
                include += "#endif\n"
            if is_static:
                self.static_import += include
            else:
                if is_global:
                    self.global_import_global += include
                else:
                    for line in include.splitlines():
                        self.add_header_line(line)

    def handle_class(self, node):
        name = node.name.value if node.name else ""
        in_header = self.in_header
        if self.indent == 0 and not node.is_static:
            self.in_header = True

        variable_name = ""
        if node.parent_class:
            kind = node.value[0].value
            if len(node.value) > 1:
                variable_name = " " + node.value[1].value
        else:
            kind = self.format_line(node.value)

        if node.block:
            
            if not node.parent_class:
                decl = "typedef " + kind + " " + name + ";\n"
                if self.in_header:
                    self.type_hdecl += decl
                else:
                    self.type_cdecl += decl

            self.add_iline(kind + " {")
            self.indent += 1

            self.write_block(node.block)

            #for field in node.fields:
            #    line = self.format_line(field.declaration)
            #    line += " " + field.name;
            #    self.add_line(self.indent * "    " + line + ";")

            self.indent -= 1
            self.add_line(self.indent * "    " + "}" + variable_name + ";")
        else:
            decl = kind + variable_name + ";\n"
            if self.in_header:
                self.type_hdecl += decl
            else:
                self.type_cdecl += decl

        self.in_header = in_header

    def write_enum_block(self, b):
        p = self.p
        i = 0
        while i < len(b.value):
            line = "    " * self.indent
            tokens = b.value[i].value
            line += self.format_line(tokens)
            if i < len(b.value) - 1:
                line += ","
            self.in_row, _ = parser.get_row_col(tokens[0])
            self.add_line(line)
            i += 1

    def handle_enum(self, s):
        name = None

        if len(s.value) > 1:
            name = s.value[1].value
       
        in_header = self.in_header
        if self.indent == 0 and not s.is_static:
            self.in_header = True
        if s.block:
            if name:
                decl = "typedef enum " + name + " " + name + ";\n"
                if self.in_header:
                    self.type_hdecl += decl
                else:
                    self.type_cdecl += decl
                self.add_line(self.indent * "    " + "enum " + name + " {")
            else:
                self.add_line(self.indent * "    " + "enum {")
            self.indent += 1
            self.write_enum_block(s.block)
            self.indent -= 1
            self.add_line(self.indent * "    " + "};")

        self.in_header = in_header

    def handle_macro(self, s):
        tokens = s.value

        in_header = self.in_header
        if self.indent == 0 and not s.is_static:
            self.in_header = True
        
        if s.is_static:
            macro_name = self.get_flat_list(tokens)[0].value
            self.undef_at_end.append(macro_name)
        
        if s.block:
            line = self.format_line(tokens)
            self.in_macro += 1
            self.add_line("#define " + line)
            self.indent += 1
            self.write_block(s.block, is_macro = True)

            # Remove the last backslash
            if self.in_header:
                self.header = self.header[:-3] + "\n"
            else:
                self.code = self.code[:-3] + "\n"

            self.indent -= 1
            self.in_macro -= 1
        else:            
            line = self.format_line(tokens)
            if s.replacement:
                line += " " + self.format_line(s.replacement)
            self.add_line("#define " + line)

        self.in_header = in_header

    def handle_preprocessor(self, s):
        in_header = self.in_header
        if self.indent == 0 and s.is_global:
            self.in_header = True

        #print(s.value)

        command = s.name.value.strip('"')
        if s.value:
            line = command + " " + self.format_line(s.value)
        else:
            line = command
        self.add_line(self.indent * "    " + "#" + line)

        self.in_header = in_header
    
    def write_for_while(self, statement):
        p = self.p

        decl = self.format_line(statement.value)

        condition = self.format_line(statement.part)

        if statement.part2:
            loop = self.format_line(statement.part2)
        else:
            loop = ""

        line = "for ("
        line += decl + "; "
        line += condition + "; "
        line += loop + ") {"

        self.add_iline(line)
        
        self.indent += 1
        self.write_block(statement.block)
        self.indent -= 1
        self.add_iline("}")

    def get_decl_var(self, decl):
        p = self.p
        if decl[0].kind == p.OPERATOR:
            op = decl[0]
            if op.value[0].value == "*":
                var = op.value[2] # right operator
                return var
            return op.value[1]
        if decl[0].kind == p.TOKEN:
            return decl[0]
        return None

    def get_decl_type_name(self, decl):
        op = decl[0] # assume it's just a * operator
        if op.kind == self.p.TOKEN:
            v = self.find_variable(op.value)
            if v:
                type_token = v.declaration.value[1]
            else:
                return ""
        else:
            type_token = op.value[1] # left operator
        return type_token.value

    # given something like "(a, b + 1, c)" return "a b+1 c"
    def get_flat_list(self, decl):
        p = self.p
        r = []
        for op in decl:
            if op.kind == p.OPERATOR:
                if is_sym(op.value[0], "("):
                    r += self.get_flat_list(op.value[1:])
                elif is_sym(op.value[0], ","):
                    r += self.get_flat_list(op.value[1:])
                elif op.value[0].kind == p.TOKEN:
                    r += self.get_flat_list(op.value)
                else:
                    r += [op]
            elif op.kind != p.SYMBOL:
                r += [op]
        return r

    def write_for_in_range(self, statement):
        p = self.p

        token_for = statement.name
        tokens_decl = statement.value
        tokens_range = statement.part
        var_name = self.get_decl_var(tokens_decl)

        range_parts = self.get_flat_list(tokens_range)
        
        if len(range_parts) == 1:
            a = "0"
            b = self.format_line([range_parts[0]])
            c = "1"
            comparison = "<"
        elif len(range_parts) == 2:
            a = self.format_line([range_parts[0]])
            b = self.format_line([range_parts[1]])
            c = "1"
            comparison = "<"
        elif len(range_parts) == 3:
            a = self.format_line([range_parts[0]])
            b = self.format_line([range_parts[1]])
            c = self.format_line([range_parts[2]])
            # FIXME: that check has to be done at runtime
            if c.startswith("-"):
                comparison = ">"
            else:
                comparison = "<"
        else:
            p.error_token("Need 1, 2 or 3 parameters for range.", tokens_range[0])

        line = token_for.value + " ("
        line += self.format_line(tokens_decl) + " = " + a + "; "
        line += self.format_line([var_name]) + " " + comparison + " " + b + "; "
        line += self.format_line([var_name]) + " += " + c + ") {"

        self.add_iline(line)
        
        if not statement.block:
            p.error_token("Expected block for for.", token_for)

        self.indent += 1
        self.write_block(statement.block)
        self.indent -= 1
        self.add_iline("}")

    # handle for in loop
    def write_for_in(self, statement):
        p = self.p
        # example
        # for x in Type *list:
        #
        # translates to
        #
        # TypeIterator i = TypeIterator_first(list)
        # for(x = TypeIterator_item(list, i);
        #   TypeIterator_next(list, i); x = TypeIterator_item(list, i))

        token_for = statement.name        
        token_decl = statement.value
        token_container = statement.part
        var_name = self.get_decl_var(token_decl)
        container_name = self.get_decl_var(token_container)
        loop_iter_name = "__iter%d__" % self.iter_id
        self.iter_id += 1
       
        type_name = self.get_decl_type_name(token_container)
        if type(type_name) != str:
            p.error_token("Need iterator type", token_for)
        else:
            iter_name = type_name + "Iterator"

        container_name = self.format_line([container_name])

        #print(token_for)
        #print(token_decl)
        #print(token_container)
        #print(var_name)
        #print(container_name)
        #print(type_name)

        self.add_iline("{")
        self.indent += 1
        
        line = iter_name + " " + loop_iter_name + " = "
        line += iter_name + "_first(" + container_name + ");"

        self.add_iline(line)

        line = token_for.value + " (" # for
        line += self.format_line(token_decl)

        line += " = " + iter_name + "_item(" + container_name + ", "
        line += "&" + loop_iter_name + "); "

        line += iter_name + "_next(" + container_name + ", "
        line += "&" + loop_iter_name + "); "

        line += self.format_line([var_name])
        line += " = " + iter_name + "_item(" + container_name + ", "
        line += "&" + loop_iter_name + ")) {"

        self.add_iline(line)
        
        self.indent += 1
        self.write_block(statement.block)
        self.indent -= 1
        self.add_iline("}")
        
        self.indent -= 1
        self.add_iline("}")

        self.iter_id -= 1

    def handle_statement(self, statement):
        p = self.p
        name = statement.name.value

        if name == "elif":
            name = "else if"

        if name == "case":
            cases = self.get_flat_list(statement.value)
            if not cases:
                p.error_token("Weird case: %s" % str(statement.value), statement.name)

            lines = [
                "case " + self.format_line([case]) + ":"
                for case in cases]
            for line in lines[:-1]:
                self.add_iline(line)
            line = lines[-1]
            
        elif name == "default":
            line = "default:"

        elif name == "pass":
            self.add_iline(";")
            return

        elif name == "return":
            self.add_iline("return " + self.format_line(statement.value) + ";")
            return

        elif name == "for":
            if statement.sub_kind == "range":
                self.write_for_in_range(statement)
            elif statement.sub_kind == "in":
                self.write_for_in(statement)
            else:
                self.write_for_while(statement)

            return
        else:
            line = name
            tokens = statement.value
            
            if tokens:
                line += " (" + self.format_line(tokens) + ")"

        self.add_iline(line + " {")
        if statement.block:
            self.indent += 1
            self.write_block(statement.block)
            self.indent -= 1
        self.add_iline("}")

    def find_variable(self, name):
        # check if the type is declared in the current or a parent block
        for block in self.current_block:
            for v in block.variables:
                if v.name == name:
                    return v
        # check if the type comes from a parameter
        if self.current_function:
            for parameter in self.current_function[-1].parameters:
                if parameter.name == name:
                    return parameter.as_variable()

    def find_function(self, name):
        f = self.p.analyzer.functions.get(name)
        if f is not None:
            # .name
            # .parameters
            # .ret
            return f

    def check_auto_assignment(self, first):
        if first.kind == self.p.OPERATOR:
            tokens = first.value
            op = tokens[0]
            if analyzer.Analyzer.is_sym(op, "="):
                if tokens[1].kind == self.p.OPERATOR:
                    if analyzer.Analyzer.is_tok(tokens[1].value[0], "auto"):
                        v = self.find_variable(tokens[2].value)
                        if v:
                            first.value = (tokens[0], v.replace(tokens[1].value[1])) + tokens[2:]
                        else:
                            f = self.find_function(tokens[2].value[0].value)
                            if f:
                                first.value[1].value = (f.ret[1], f.ret[0], first.value[1].value[1])

    def write_line(self, s, block):
        """
        Write out one statement in C language.
        """

        if s.is_hidden:
            return
        
        p = self.p
        tokens = s.value[:]

        if tokens:
            # docstring
            if tokens[0].kind == p.STRING:
                if not self.in_header:
                    self.add_code_line(None)
                    first = True
                    for line in tokens[0].value.splitlines():
                        line = line.strip()
                        if line in ["", '"""', "'''"]: continue
                        if first: self.code += "    /* "; first = False
                        else: self.code += "     * "
                        self.code += line
                        self.code += "\n"
                        self.out_crow += 1
                    if not first: self.code += "     */\n"
                    self.out_crow += 1
                return

            self.check_auto_assignment(tokens[0])

            line = self.format_line(tokens)
            if s.is_static:
                line = "static " + line
            if block:
                self.add_line(self.indent * "    " + line + " {")
                self.indent += 1
                self.write_block(block)
                self.indent -= 1
                self.add_line(self.indent * "    " + "}")
            else:
                self.add_line(self.indent * "    " + line + ";")

                if s.is_global:
                    # global variable declaration
                    op = tokens[0] # assume it's just a = operator
                    if op.kind == p.OPERATOR and is_sym(op.value[0], "="):
                        left = op.value[1]
                    else:
                        left = op
                    line = self.format_line([left])
                    self.add_header_line("extern " + line + ";")

    def write_block(self, b, is_macro = False):
        self.current_block.append(b)

        p = self.p
        i = 0
        n = len(b.value)
        while i < n:
            s = b.value[i]
            i += 1

            if s.value:
                self.in_row, _ = parser.get_row_col(s)
            
            block = None
            if i < n:
                if b.value[i].kind == p.BLOCK:
                    block = b.value[i]
                    i += 1

            if not self.in_header:
                for c in s.comments:
                    self.code += self.indent * "    "
                    self.code += "//"
                    self.code += c.value.rstrip()
                    self.code += "\n"
                    self.out_crow += 1
                    
            if s.kind == p.LINE:
                self.write_line(s, block)
            elif s.kind == p.STATEMENT:
                self.handle_statement(s)
            elif s.kind == p.TYPE:
                self.handle_class(s)
            elif s.kind == p.FUNCTION:
                if self.before_first_function_code is None:
                    self.before_first_function_code = self.code
                    self.code = ""
                self.current_function.append(s)
                self.handle_function(s)
                self.current_function.pop()
            elif s.kind == p.IMPORT:
                self.handle_import(s.value[1:], s.is_static)
            elif s.kind == p.PREPROCESSOR:
                self.handle_preprocessor(s)
            elif s.kind == p.MACRO:
                self.handle_macro(s)
            elif s.kind == p.ENUM:
                self.handle_enum(s)
            elif s.kind == p.LABEL:
                self.add_iline(self.format_line(s.value[1:]) + ":;")
            elif s.kind == p.GOTO:
                self.add_iline("goto " + self.format_line(s.value[1:]) + ";")
            elif s.kind == p.INCLUDE:
                self.p = s.value

                if not self.no_lines:
                    prev_crow = self.out_crow
                    self.code += "#line 1 \"" + self.p.filename + "\"\n"
                    self.out_crow = 1
                    
                    prev_hrow = self.out_hrow
                    self.header += "#line 1 \"" + self.p.filename + "\"\n"
                    self.out_hrow = 1
                
                self.undef_at_end = []
                self.write_block(self.p.root)
                self.p = p

                if not self.no_lines:
                    self.out_crow = prev_crow + 1
                    self.code += "#line " + str(self.out_crow) + " \"" +\
                        self.p.filename + "\"\n"
                    
                    self.out_hrow = prev_hrow + 1
                    self.header += "#line " + str(self.out_hrow) + " \"" +\
                        self.p.filename + "\"\n"
                
                for u in self.undef_at_end:
                    self.code += "#undef " + u + "\n"
                    self.out_crow += 1
                
            else:
                row, col = parser.get_row_col(s)
                p.error_pos("Unexpected node type %d." % s.kind, row, col)
        self.current_block.pop()

    def generate(self, p, name, no_lines, prefix):
        self.p = p
        self.indent = 0
        self.before_first_function_code = None
        self.code = ""
        self.header = ""
        self.name = name
        self.no_lines = no_lines
        self.prefix = prefix
        self.need_min = False
        self.need_max = False
        self.in_header = False
        self.out_crow = 0 # line-number of c-source
        self.out_hrow = 0 # line number of header
        self.in_row = 1
        self.type_cdecl = ""
        self.static_cdecl = ""
        self.static_import = ""
        self.type_hdecl = ""
        self.global_import_global = ""
        self.in_macro = 0
        self.undef_at_end = []
        self.iter_id = 0
        self.current_function = []
        self.current_block = []

        self.write_block(p.root)

        guard = name.upper().replace("/", "_")
        guard = prefix + "_" + guard + "_"

        code = self.first_line()
        code += "#include \"" + name + ".h\"\n"
        if self.need_min: code += "#define _scramble_min(x, y) ((y) < (x) ? (y) : (x))\n"
        if self.need_max: code += "#define _scramble_max(x, y) ((y) > (x) ? (y) : (x))\n"
        code += self.type_cdecl
        code += self.static_import
        if self.before_first_function_code:
            code += self.before_first_function_code
        code += self.static_cdecl
        code += self.code
        if not no_lines: code += self.note

        header = self.first_line()
        header += "#ifndef " + guard + "\n"
        header += "#define " + guard + "\n"
        header += self.global_import_global
        header += self.type_hdecl
        header += self.header
        header += "#endif\n"
        if not no_lines: header += self.note

        return code, header
