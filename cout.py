import parser

class CWriter:
    opencurly = parser.Token(parser.Parser.SYMBOL, "{", 0, 0)
    closecurly = parser.Token(parser.Parser.SYMBOL, "}", 0, 0)
    openparenthesis = parser.Token(parser.Parser.SYMBOL, "(", 0, 0)
    closeparenthesis = parser.Token(parser.Parser.SYMBOL, ")", 0, 0)
    colon = parser.Token(parser.Parser.SYMBOL, ":", 0, 0)
    assignment = parser.Token(parser.Parser.SYMBOL, "=", 0, 0)
    lowerthan = parser.Token(parser.Parser.SYMBOL, "<", 0, 0)
    greaterthan = parser.Token(parser.Parser.SYMBOL, ">", 0, 0)
    increment = parser.Token(parser.Parser.SYMBOL, "+=", 0, 0)
    semicolon = parser.Token(parser.Parser.SYMBOL, ";", 0, 0)
    comma = parser.Token(parser.Parser.SYMBOL, ",", 0, 0)
    void = parser.Token(parser.Parser.TOKEN, "void", 0, 0)
    elseif = parser.Token(parser.Parser.TOKEN, "else if", 0, 0)
    ampersand = parser.Token(parser.Parser.SYMBOL, "&", 0, 0)
    note = "/* This file was generated by scramble.py. */\n"

    # Tokens which when preceding an open parenthesis are not hugged by it.
    no_hug_tokens = ["if", "elif", "else", "for", "while", "switch"]
    # Symbols which hug the following token.
    hug_following_symbols = ["(", ".", "->", "--", "++", "[", "{", "***"]
    # Symbols which hug the preceding token.
    hug_preceding_symbols = [")", ",", ";", "++", "--", ".", "->", "[", "]", "}", "***"]

    def add_header_line(self, code):
        if not self.no_lines and not self.in_macro:
            if self.out_hrow == 0:
                self.header += "#line %d \"%s\"\n" % (self.in_row,
                    self.p.filename)
                self.out_hrow = self.in_row
            if self.out_hrow != self.in_row and not code.strip() in ("}", "};"):
                self.header += "#line %d\n" % self.in_row
                self.out_hrow = self.in_row
        self.header += code
        if self.in_macro: self.header += " \\"
        self.header += "\n"
        self.out_hrow += 1

    def add_code_line(self, code):
        if not self.no_lines and not self.in_macro:
            if self.out_crow == 0:
                self.code += "#line %d \"%s\"\n" % (self.in_row,
                    self.p.filename)
                self.out_crow = self.in_row
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

    def format_line(self, tokens):
        """
        Weave a formatted string out of a list of tokens.
        """
        p = self.p
        line = ""
        prev = None
        for tok in tokens:
            word = tok.value
            if tok.kind == p.TOKEN:
                if word == "not": word = "!"
                if word == "and": word = "&&"
                if word == "or": word = "||"
                if word == "None": word = "NULL"
                if word == "True": word = "1"
                if word == "False": word = "0"
                if word == "min": word = "_scramble_min"; self.need_min = True
                if word == "max": word = "_scramble_max"; self.need_max = True
                if word == "with": word = ":" # for bit fields
            if tok.kind == p.SYMBOL:
                if word == "***": word = "#" # macro string concatenation
            if prev:
                if prev.kind == p.SYMBOL:
                    if tok.kind == p.SYMBOL:
                        if tok.value in "{[()]}" and prev.value in "{[()]}":
                            if tok.value == "(" and prev.value == ")":
                                line += " "
                        elif prev.value in self.hug_following_symbols:
                            if tok.value in self.hug_preceding_symbols:
                                pass
                            else:
                                line += " "
                        else:
                            line += " "
                    else:
                        if prev.value in self.hug_following_symbols:
                            pass
                        else:
                            line += " "
                else:
                    if tok.kind == p.SYMBOL:
                        if tok.value == "(":
                            if prev.value in self.no_hug_tokens:
                                line += " "
                            else:
                                pass
                        elif tok.value in self.hug_preceding_symbols:
                            pass
                        else:
                            line += " "
                    elif tok.kind == p.STRING:
                        # handles e.g. x = L'♥'
                        line += ""    
                    else:
                        line += " "
            if tok.kind == p.STRING:
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
            line += word
            prev = tok
        return line

    def prepare_function(self, tokens):
        """
        - Remove "def" token.
        - Fill in missing "void" tokens.
        - Copy preceding parameter type if just a name is given.
        """
        p = self.p
        got_return = False
        got_static = False
        tokens2 = []
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            i += 1
            if tok.kind == p.TOKEN:
                if tok.value == "def":
                    if not got_return:
                        tokens2.append(self.void)
                    break
                elif tok.value == "static":
                    got_static = True
                    tokens2.append(tok)
                else:
                    got_return = True
                    tokens2.append(tok)
            else:
                tokens2.append(tok)

        if i == len(tokens):
            p.error_pos("Definition without name.", tokens[i - 1].row,
                tokens[i - 1].col)
        name = tokens[i]
        i += 1
        tokens2.append(name)

        op = None
        params = [[0]]
        balance = 0
        while i < len(tokens):
            tok = tokens[i]
            i += 1
            if tok.kind == p.SYMBOL:
                if tok.value == "(":
                    op = tok
                    balance += 1
                    if balance == 1: continue
                if tok.value == ")":
                    cp = tok
                    balance -= 1
                    if balance == 0: continue
                if tok.value == ",":
                    if balance == 1:
                        params.append([0])
                        continue
            params[-1].append(tok)
            if tok.kind != p.SYMBOL or tok.value != "*":
                params[-1][0] += 1

        if op is None:
            p.error_pos("Invalid function definition",
                tokens[i - 1].row, tokens[i - 1].col)

        tokens2.append(op)

        prevtype = None
        for i in range(len(params)):
            param = params[i]
            if param[0] == 0:
                tokens2.append(self.void)
            elif param[0] == 1:
                if prevtype is None:
                    p.error_pos("Parameter type missing.", param[1].row,
                        param[1].col)
                n = len(params[prevtype]) - 1
                while n > 0 and params[prevtype][n - 1].value == "*":
                    n -= 1
                for tok in params[prevtype][1:n] + param[1:]:
                    tokens2.append(tok)
            else:
                prevtype = i
                for tok in param[1:]:
                    tokens2.append(tok)
            if i < len(params) - 1: tokens2.append(self.comma)

        tokens2.append(cp)

        return tokens2, got_static

    def handle_import(self, tokens, is_static):
        is_global = False
        name = ""

        def next():
            if is_global:
                word = "<" + name + ".h>"
            else:
                if self.p.ignore_local_imports: return
                word = '"' + name + '.h"'
            line = "#include " + word
            if is_static:
                self.add_code_line(line)
            else:
                self.add_header_line(line)

        for tok in tokens:
            if tok.value == "global":
                is_global = True
            elif tok.value == ",":
                next()
                name = ""
            elif tok.value in [".", "/"]:
                name += "/"
            else:
                name += tok.value
        next()

    def handle_class(self, tokens, is_static, block):
        name = tokens[0].value
        in_header = self.in_header
        if self.indent == 0 and not is_static:
            self.in_header = True
        if block:
            decl = "typedef " + "struct" + " " + name + " " + name + ";\n"
            if self.in_header:
                self.type_hdecl += decl
            else:
                self.type_cdecl += decl
            self.add_line(self.indent * "    " + "struct" + " " + name + " {")
            self.indent += 1
            self.write_block(block)
            self.indent -= 1
            self.add_line(self.indent * "    " + "};")

        self.in_header = in_header

    def handle_union(self, tokens, is_static, block):
        name = tokens[0].value
        in_header = self.in_header
        if self.indent == 0 and not is_static:
            self.in_header = True
        if block:
            decl = "typedef " + "union" + " " + name + " " + name + ";\n"
            if self.in_header:
                self.type_hdecl += decl
            else:
                self.type_cdecl += decl
            self.add_line(self.indent * "    " + "union" + " " + name + " {")
            self.indent += 1
            self.write_block(block)
            self.indent -= 1
            self.add_line(self.indent * "    " + "};")

        self.in_header = in_header

    def handle_typedef(self, tokens, is_static):
        name = tokens[0].value
        in_header = self.in_header
        if self.indent == 0 and not is_static:
            self.in_header = True

        line = self.format_line(tokens)
        self.add_line(self.indent * "    " + line + ";")

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
            self.in_row = tokens[0].row
            self.add_line(line)
            i += 1

    def handle_enum(self, tokens, is_static, block):
        name = ""
        if tokens:
            name = tokens[0].value
        in_header = self.in_header
        if self.indent == 0 and not is_static:
            self.in_header = True
        if block:
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
            self.write_enum_block(block)
            self.indent -= 1
            self.add_line(self.indent * "    " + "};")

        self.in_header = in_header

    def handle_macro(self, tokens, is_static, block):
        in_header = self.in_header
        if self.indent == 0 and not is_static:
            self.in_header = True
        
        if is_static:
                self.undef_at_end.append(tokens[0].value)
        
        if block:
            line = self.format_line(tokens)
            self.in_macro += 1
            self.add_line("#define " + line)
            self.indent += 1
            self.write_block(block, is_macro = True)

            # Remove the last backslash
            if self.in_header:
                self.header = self.header[:-3] + "\n"
            else:
                self.code = self.code[:-3] + "\n"

            self.indent -= 1
            self.in_macro -= 1
        else:
            # Compare those in C:
            # #define X(x)
            # #define X (x)
            # They are very different things. In scramble, to solve this, you
            # can use an equal sign. So to get the above you can do:
            # #define X(x)
            # #define X = (x)
            if len(tokens) > 1 and tokens[1].value == "=":
                line = tokens[0].value + " " + self.format_line(tokens[2:])
            else:
                line = self.format_line(tokens)
            self.add_line("#define " + line)

        self.in_header = in_header

    def handle_preprocessor(self, tokens, is_static):
        in_header = self.in_header
        if self.indent == 0 and not is_static:
            self.in_header = True

        command = tokens[0].value.strip('"')
        if tokens[1:]:
            line = command + " " + self.format_line(tokens[1:])
        else:
            line = command
        self.add_line(self.indent * "    " + "#" + line)

        self.in_header = in_header
    
    def handle_for_while(self, tokens):
        p = self.p
        got_while = False
        got_with = False

        decl = []
        tokens2 = tokens[0:1] + [self.openparenthesis]
        for tok in tokens[1:]:
            if tok.kind == p.TOKEN and tok.value == "while":
                tokens2 += [self.semicolon]
                got_while = True
            elif tok.kind == p.TOKEN and tok.value == "with":
                tokens2 += [self.semicolon]
                got_with = True
            else:
                if got_while or got_with:
                    tokens2 += [tok]
                else:
                    decl += [tok]

        if self.use_c99:
            tokens2 = tokens2[:2] + decl + tokens2[2:]
        else:
            equals = 0
            token_count = 0
            for i in range(len(decl)):
                e = decl[i]
                if e.kind == p.SYMBOL and e.value == "=":
                    equals = i
                    break
                if e.kind == p.TOKEN: token_count += 1
            if equals and token_count > 1:
                self.c99_hack = True
                decltype = decl[:equals]
                decl = decl[equals - 1:]
                tokens2 = [self.opencurly] + decltype +\
                    [self.semicolon] + tokens2[:2] + decl + tokens2[2:]
            else:
                tokens2 = tokens2[:2] + decl + tokens2[2:]
    
        tokens2 += [self.closeparenthesis]
        if not got_while or not got_with:
            p.error_token("For loop syntax is 'for x while y with z'.",
                tokens[0])
        return tokens2
    
    def handle_for_range(self, tokens_variable, tokens_range):
        p = self.p
        
        ob = tokens_range[0]
        cb = tokens_range[-1]
        if ob.kind != p.SYMBOL or ob.value != "(":
            p.error_token("Need opening brace after range.", ob)
        if cb.kind != p.SYMBOL or cb.value != ")":
            p.error_token("Need closing brace for range.", cb)
        
        tokens_range = tokens_range[1:-1]

        range_parts = []
        toks = []
        for tok in tokens_range:
            if tok.kind == p.SYMBOL and tok.value == ",":
                range_parts.append(toks)
                toks = []
            else:
                toks += [tok]
        range_parts.append(toks)

        if len(range_parts) == 1:
            a = [parser.Token(parser.Parser.TOKEN, "0", 0, 0)]
            b = range_parts[0]
            c = [parser.Token(parser.Parser.TOKEN, "1", 0, 0)]
            comparison = self.lowerthan
        elif len(range_parts) == 2:
            a = range_parts[0]
            b = range_parts[1]
            c = [parser.Token(parser.Parser.TOKEN, "1", 0, 0)]
            comparison = self.lowerthan
        elif len(range_parts) == 3:
            a = range_parts[0]
            b = range_parts[1]
            c = range_parts[2]
            if c[0].value.startswith("-"):
                comparison = self.greaterthan
            else:
                comparison = self.lowerthan
        else:
            p.error_token("Need 1, 2 or 3 parameters for range.", tokens_range[0])

        for_token = tokens_variable[0]
        decl = tokens_variable[1:-1]
        v = tokens_variable[-1]
        tokens2 = [for_token, self.openparenthesis] + decl
        tokens2 += [v, self.assignment] + a + [self.semicolon]
        tokens2 += [v, comparison] +  b + [self.semicolon]
        tokens2 += [v, self.increment] + c + [self.closeparenthesis]
        return tokens2

    def handle_for_in(self, tokens_variable, tokens_list):
        p = self.p
        # examplee
        # for x in Type *list:
        #
        # translates to
        #
        # TypeIterator i = TypeIterator_first(list)
        # for(x = TypeIterator_item(list, i);
        #   TypeIterator_next(list, i); x = TypeIterator_item(list, i))

        if len(tokens_list) < 3:
            p.error_token("for in loop syntax is 'for x in Type *list'.",
                tokens_list[0])

        for_token = tokens_variable[0]
        decl = tokens_variable[1:-1]
        v = tokens_variable[-1]
        type_token = tokens_list[0]
        list_tokens = tokens_list[2:]

        self.c99_hack = True # need closing curly brace
        
        itertype_token = parser.Token(parser.Parser.TOKEN, type_token.value +
            "Iterator", 0, 0)

        iter_name = "__iter%d__" % self.iter_id
        self.iter_id += 1
        iter_token = parser.Token(parser.Parser.TOKEN, iter_name, 0, 0)
        first_token = parser.Token(parser.Parser.TOKEN, type_token.value +
            "Iterator_first", 0, 0)
        item_token = parser.Token(parser.Parser.TOKEN, type_token.value +
            "Iterator_item", 0, 0)
        next_token = parser.Token(parser.Parser.TOKEN, type_token.value +
            "Iterator_next", 0, 0)

        tokens2 = [self.opencurly, itertype_token, iter_token, self.assignment,
            first_token, self.openparenthesis] + list_tokens + [
            self.closeparenthesis, self.semicolon];
        tokens2 += [for_token, self.openparenthesis]
        tokens2 += decl + [v, self.assignment, item_token,
            self.openparenthesis] + list_tokens + [self.comma, self.ampersand,
            iter_token,  self.closeparenthesis]
        tokens2 += [self.semicolon, next_token, self.openparenthesis
            ] + list_tokens + [self.comma, self.ampersand, iter_token,
            self.closeparenthesis, self.semicolon]
        tokens2 += [v, self.assignment, item_token,
            self.openparenthesis] + list_tokens + [self.comma, self.ampersand,
            iter_token, self.closeparenthesis,self.closeparenthesis]

        return tokens2

    def write_line(self, s, block):
        """
        Write out one statement in C language.
        """
        p = self.p
        tokens = s.value[:]
        c99_hack = False

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

            self.in_row = tokens[0].row

            if tokens[0].kind == p.TOKEN:
                if tokens[0].value in ["switch", "while", "if"]:
                    tokens = tokens[0:1] + [self.openparenthesis] + tokens[1:] + [self.closeparenthesis]
                elif tokens[0].value == "case":
                    cases = []
                    for tok in tokens[1:]:
                        if not cases:
                            cases.append([])

                        if tok.kind == p.SYMBOL and tok.value == ",":
                            cases.append([])
                        else:
                            cases[-1].append(tok)

                    casetok = tokens[0]
                    tokens = []
                    for case in cases:
                        tokens.append(casetok)
                        tokens.extend(case)
                        tokens.append(self.colon)
                elif tokens[0].value == "default":
                    tokens = tokens + [self.colon]
                elif tokens[0].value == "for":
                    in_pos = None
                    use_range = False
                    for i, tok in enumerate(tokens):
                        if tok.kind == p.TOKEN and tok.value == "in":
                            in_pos = i
                        elif tok.kind == p.TOKEN and tok.value == "range":
                            if i == in_pos + 1:
                                use_range = True
                                break
                    if use_range:
                        tokens = self.handle_for_range(tokens[:in_pos],
                            tokens[in_pos + 2:])
                    elif in_pos != None:
                        tokens = self.handle_for_in(tokens[:in_pos],
                            tokens[in_pos + 1:])
                    else:
                        tokens = self.handle_for_while(tokens)
                    c99_hack = self.c99_hack
                    self.c99_hack = False
                elif tokens[0].value == "pass":
                    tokens = []
                elif tokens[0].value == "label":
                    tokens = [tokens[1], self.colon]
                elif tokens[0].value == "elif":
                    tokens = [self.elseif] + [self.openparenthesis] + tokens[1:] + [self.closeparenthesis]
                elif tokens[0].value == "import":
                    self.handle_import(tokens[1:], 0)
                    return
                elif tokens[0].value == "static" and len(tokens) > 1 and\
                    tokens[1].value == "import":
                    self.handle_import(tokens[2:], 1)
                    return
                elif tokens[0].value == "class":
                    self.handle_class(tokens[1:], 0, block)
                    return
                elif tokens[0].value == "static" and len(tokens) > 1 and\
                    tokens[1].value == "class":
                    self.handle_class(tokens[2:], 1, block)
                    return
                elif tokens[0].value == "enum":
                    self.handle_enum(tokens[1:], 0, block)
                    return
                elif tokens[0].value == "static" and len(tokens) > 1 and\
                    tokens[1].value == "enum":
                    self.handle_enum(tokens[2:], 1, block)
                    return
                elif tokens[0].value == "union":
                    self.handle_union(tokens[1:], 0, block)
                    return
                elif tokens[0].value == "macro":
                    self.handle_macro(tokens[1:], 0, block)
                    return
                elif tokens[0].value == "static" and len(tokens) > 1 and\
                    tokens[1].value == "macro":
                    self.handle_macro(tokens[2:], 1, block)
                    return
                elif tokens[0].value == "typedef":
                    self.handle_typedef(tokens, 0)
                    return
                elif tokens[0].value == "static" and len(tokens) > 1 and\
                    tokens[1].value == "typedef":
                    self.handle_typedef(tokens[1:], 1)
                    return
                elif tokens[0].value == "global":
                    if tokens[1].value == "***":
                        self.handle_preprocessor(tokens[2:], 0)
                        return
                    else: # assume variable declaration
                        line = self.format_line(tokens[1:])
                        self.add_line(line + ";")
                        tokens2 = []
                        for tok in tokens[1:]:
                            if tok.kind == p.SYMBOL and tok.value == "=":
                                break
                            tokens2.append(tok)
                        line = self.format_line(tokens2)
                        self.add_header_line("extern " + line + ";")
                        return
                else:
                    is_function = False
                    for tok in tokens:
                        if tok.kind == p.TOKEN and tok.value == "def":
                            is_function = True

                    if is_function:
                        tokens, is_static = self.prepare_function(tokens)
                        # Write prototype into header.
                        if not is_static and not self.in_macro:
                            line = self.format_line(tokens)
                            self.add_header_line(line + ";")
            elif tokens[0].kind == p.SYMBOL:
                if tokens[0].value == "***":
                    self.handle_preprocessor(tokens[1:], 1)
                    return

            line = self.format_line(tokens)
            if block:
                self.add_line(self.indent * "    " + line + " {")
                self.indent += 1
                self.write_block(block)
                self.indent -= 1
                self.add_line(self.indent * "    " + "}")
            else:
                self.add_line(self.indent * "    " + line + ";")
               
            if c99_hack:
                self.add_line(self.indent * "    " + "}")

    def write_block(self, b, is_macro = False):
        p = self.p
        i = 0
        n = len(b.value)
        while i < n:
            s = b.value[i]
            i += 1
            block = None
            if i < n:
                if b.value[i].kind == p.BLOCK:
                    block = b.value[i]
                    i += 1
            if s.kind == p.LINE:
                if not self.in_header:
                    for c in s.comments:
                        self.code += self.indent * "    "
                        self.code += "//"
                        self.code += c.value.rstrip()
                        self.code += "\n"
                        self.out_crow += 1
                self.write_line(s, block)
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
                p.error_pos("Unexpected block.", 0, 0)

    def generate(self, p, name, no_lines, prefix, use_c99):
        self.use_c99 = use_c99
        self.c99_hack = False
        self.p = p
        self.indent = 0
        self.code = ""
        self.header = ""
        self.name = name
        self.no_lines = no_lines
        self.prefix = prefix
        self.need_min = False
        self.need_max = False
        self.in_header = False
        self.out_crow = 0
        self.out_hrow = 0
        self.in_row = 1
        self.type_cdecl = ""
        self.type_hdecl = ""
        self.in_macro = 0
        self.undef_at_end = []
        self.iter_id = 0

        self.write_block(p.root)

        guard = name.upper().replace("/", "_")
        guard = prefix + "_" + guard + "_"

        code = ""
        if not no_lines: code += self.note
        code += "#include \"" + name + ".h\"\n"
        if self.need_min: code += "#define _scramble_min(x, y) ((y) < (x) ? (y) : (x))\n"
        if self.need_max: code += "#define _scramble_max(x, y) ((y) > (x) ? (y) : (x))\n"
        code += self.type_cdecl
        code += self.code
        if not no_lines: code += self.note

        header = ""
        if not no_lines: header += self.note
        header += "#ifndef " + guard + "\n"
        header += "#define " + guard + "\n"
        header += self.type_hdecl
        header += self.header
        header += "#endif\n"
        if not no_lines: header += self.note

        return code, header
