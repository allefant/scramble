import os
from . import analyzer
import inspect

class MyError(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return self.value

class Node:
    """
    A node of the syntax tree. The root always is of kind BLOCK. The children
    of a BLOCK are either another, nested BLOCK or a LINE. The children of a
    LINE are not nodes but directly tokens.
    """
    def __init__(self, kind, value : "List[Node]"):
        self.kind, self.value = kind, value
        self.comments = []
        self.is_static = False
        self.is_global = False
        self.is_hidden = False
        
    def __repr__(self):
        return "Node(%s, %s)" % (Parser.kind_name(self.kind), repr(self.value))

class Token:
    """
    A leaf of the syntax Tree. It describes a textual token in the source code,
    complete with line number and column information.
    """
    def __init__(self, kind, value, row, col):
        self.kind, self.value, self.row, self.col = kind, value, row, col
        self.comments = []
        
    def __repr__(self):
        return "Token(%d:%d, %s, %s)" % (self.row, self.col,
            Parser.kind_name(self.kind),
            repr(self.value))

class Parser:
    STRING = 0
    TOKEN = 1
    SYMBOL = 2

    LINE = 3
    BLOCK = 4
    COMMENT = 5
    INCLUDE = 6

    FUNCTION = 7 # declaration
    VARIABLE = 8 # declaration
    TYPE = 9 # declaration
    OPERATOR = 10
    MACRO = 11 # declaration
    STATEMENT = 12
    IMPORT = 13
    PREPROCESSOR = 14
    ENUM = 15
    LABEL = 16
    GOTO = 17

    # Combined symbols of length 2 and 3.
    operators2 = ["==", "++", "--", "->", "<<", ">>", "+=", "-=", "*=", "/=",
        "|=", "&=", "^=", "~=", ">=", "<=", "!=", "&&", "||", "%=", "//", "?."]
    operators3 = ["***", ">>=", "<<=", "..."]

    @staticmethod
    def kind_name(x):
        for k in Parser.__dict__.keys():
            v = getattr(Parser, k)
            if type(v) is int:
                if v == x:
                    return k
        return "UNKNOWN(" + str(x) + ")"
                

    def __init__(self, filename, text, comments = False, options = None):
        self.text = text.replace("\r", "")
        if len(text) == 0 or text[-1] != "\n": text += "\n"
        self.pos = 0
        self.filename = filename
        self.row = 1
        self.rowpos = 0
        self.c_tertiary_hack = 0
        self.retain_comments = comments
        self.ignore_local_imports = False
        self.prefix_static = ""
        self.unnamed_token = Token(Parser.TOKEN, "unnamed", 0, 0)
        self.external_types = {}
        self.external_variables = {}
        self.external_functions = {}
        if not options:
            class Options:
                def __getattr__(o, k):
                    return False
            options = Options()
        self.options = options

    def error_pos(self, message, l, o):
        message = "%s: %d/%d: %s" % (self.filename, l, o, message)
        raise MyError(message)

    def error(self, message):
        self.error_pos(message, self.row, self.pos - self.rowpos)
    
    def error_token(self, message, tok):
        row, col = get_row_col(tok)
        self.error_pos(message, row, col)

    def add_token(self, kind, value, line, pos):
        token = Token(kind, value, line, pos)
        if self.semicolon:
            self.semicolon = False
            token.semicolon = True
        self.lines[-1].append(token)

    def find_quote_end(self, quote, end_pos, type, l, o):
        pos = self.pos
        while 1:
            quote_pos = self.text.find(quote, pos, end_pos)
            if quote_pos == -1:
                self.error_pos("Unclosed %s-quote(%s) string." % (type, quote),
                    l, o)

            npos = pos
            while 1:
                npos = self.text.find("\n", npos, quote_pos)
                if npos == -1: break
                npos += 1
                self.row += 1
                self.rowpos = npos
    
            esc = quote_pos - 1
            while self.text[esc] == "\\":
                esc -= 1
            if (quote_pos - esc) % 2 == 1:
                return quote_pos
            pos = quote_pos + 1

    def find_single_quote_end(self, quote):
        l = self.row
        o = self.pos - self.rowpos - 1
        line_pos = self.text.find("\n", self.pos)
        if line_pos == -1: line_pos = len(self.text)
        return self.find_quote_end(quote, line_pos, "single", l, o)

    def find_triple_quote_end(self, quote):
        l = self.row
        o = self.pos - self.rowpos - 3
        return self.find_quote_end(quote, len(self.text), "triple", l, o)

    def find_token_end(self):
        pos = self.pos
        while pos < len(self.text):
            if not self.text[pos].isalnum() and self.text[pos] != "_":
                # handle numbers like 0.1e-10
                if self.text[pos] == "-" and pos > 0 and self.text[pos - 1] == "e" and self.text[self.pos - 1].isdigit():
                    pass
                else:
                    break
            pos += 1
        return pos

    def get_token(self):
        c = self.text[self.pos]
        if c == '"' or c == "'":
            spos = self.pos
            l = self.row
            o = self.pos - self.rowpos
            if self.text[self.pos:self.pos + 3] == c + c + c:
                self.pos += 3
                epos = self.find_triple_quote_end(c + c + c)
                epos += 3
            else:
                self.pos += 1
                epos = self.find_single_quote_end(c)
                epos += 1
            self.add_token(self.STRING, self.text[spos:epos], l, o)
            self.pos = epos

        elif c == '\\':
            if self.text[self.pos + 1] == '\n':
                self.pos += 2
            else:
                epos = self.text.find("#", self.pos)
                if epos == -1:
                    self.error(
                        "Newline must follow line continuation(\\).")
                else:
                    epos = self.text.find("\n", self.pos)
                    self.pos = epos + 1
            self.row += 1
            self.rowpos = self.pos

        elif c in "([{":
            self.balance += 1
            self.add_token(self.SYMBOL, c, self.row,
                self.pos - self.rowpos)
            self.pos += 1
        elif c in ")]}":
            self.balance -= 1
            if self.balance < 0:
                self.error("Closing parenthesis with no corresponding open parenthesis.")
            self.add_token(self.SYMBOL, c, self.row,
                self.pos - self.rowpos)
            self.pos += 1
        elif c == '\n':
            if self.balance == 0:
                if self.lines[-1]:
                    self.lines.append([])
            self.row += 1
            self.pos += 1
            self.rowpos = self.pos
            self.semicolon = False
        elif c == ';':
            self.lines.append([])
            self.pos += 1
            self.semicolon = True
        elif c == ':' and self.c_tertiary_hack == 0:
            if self.lines[-1]:
                self.lines.append([])
            self.pos += 1
        elif c == '#':
            l = self.row
            o = self.pos - self.rowpos
            self.pos += 1
            epos = self.text.find("\n", self.pos)
            if epos == -1: epos = len(self.text)
            if self.retain_comments:
                self.add_token(self.COMMENT, self.text[self.pos:epos], l, o)
            self.pos = epos
        elif c.isalnum() or c == "_":
            l = self.row
            o = self.pos - self.rowpos
            self.pos += 1
            epos = self.find_token_end()
            self.add_token(self.TOKEN, self.text[self.pos - 1:epos], l, o)
            self.pos = epos
        elif c.isspace():
            self.pos += 1
        else:
            c2 = self.text[self.pos:self.pos + 2]
            c3 = self.text[self.pos:self.pos + 3]
            if c3 in self.operators3:
                self.add_token(self.SYMBOL, c3, self.row,
                    self.pos - self.rowpos)
                self.pos += 3
            elif c2 in self.operators2:
                self.add_token(self.SYMBOL, c2, self.row,
                    self.pos - self.rowpos)
                self.pos += 2
            else:
                self.add_token(self.SYMBOL, c, self.row,
                    self.pos - self.rowpos)
                self.pos += 1
                if c == "?": self.c_tertiary_hack += 1
                if c == ":": self.c_tertiary_hack -= 1

    def get_tokens(self):
        """
        Does tokens, strings, comments, multi-line.
        """

        self.balance = 0
        self.semicolon = False
        self.lines = [[]]
        
        if self.text.startswith("#!/usr/bin/env python"): return

        def parse(text):
            self.insert += [(self.row, text)]

        self.env = {"parse" : parse}

        self.get_tokens_from_text()

    def get_tokens_from_text(self):

        while self.pos < len(self.text):
            x = self.text[self.pos:self.pos + 11]
            if x == "***scramble":
                end = self.text.find("\n***", self.pos)
                if end >= 0:
                    self.insert = []
                    meta = self.text[self.pos + 11:end]
                    try:
                        eval(compile(meta, "meta", "exec"), self.env)
                    except Exception as e:
                        self.error("eval error: " + str(e))
                    remove_rows = self.text[self.pos:end + 4].count("\n")
                    self.row += remove_rows

                    #self.text = self.text[:self.pos] + self.insert +\
                    #    self.text[end + 4:]
                    self.text = self.text[:self.pos] + self.text[end + 4:]

                    backup_text = self.text
                    backup_pos = self.pos
                    backup_rowpos = self.rowpos
                    backup_row = self.row
                    for row, ins in self.insert:
                        self.text = ins
                        self.pos = 0
                        self.rowpos = 0
                        self.row = row
                        self.get_tokens_from_text()
                    self.text = backup_text
                    self.pos = backup_pos
                    self.row = backup_row
                    self.rowpos = backup_rowpos

            x = self.text[self.pos:self.pos + 7]
            if x == '***"""\n':
                end = self.text.find('\n"""***', self.pos)
                if end >= 0:
                    remove_rows = self.text[self.pos:end + 7].count("\n")
                    self.row += remove_rows
                    self.text = self.text[:self.pos] + self.text[end + 7:]

            self.get_token()
            
    def get_includes(self):
        row = 0
        while row < len(self.root.value): 
            node = self.root.value[row]
            if node.kind == Parser.LINE:
                line = node.value
                if line[0].kind == Parser.TOKEN and line[0].value == "include":
                    path = line[1].value.strip("\"'")
                    n = os.path.join(os.path.dirname(self.filename), path)
                    print("including " + n)
                    text = open(n, "r").read()
                    p2 = Parser(n, text)
                    if len(line) > 2:
                        if line[2].value == "ignore_local_imports":
                            p2.ignore_local_imports = True
                        if len(line) > 3:
                            if line[3].kind == Parser.STRING:
                                p2.prefix_local = line[3].value
                    p2.parse()
                    node.kind = Parser.INCLUDE
                    node.value = p2
                    #self.root.value = self.root.value[:row] +\
                    #    p2.root.value + self.root.value[row + 1:]
                    #row += len(p2.root.value) - 1
            row += 1

    def get_blocks(self):
        """
        Groups a flat list of statements into nested blocks.
        """
        self.root = Node(self.BLOCK, [])
        class Nested: pass
        nes = Nested()
        nes.col = 0
        nes.row = 0
        nes.node = self.root
        nested = [nes]
        comments = []
        for line in self.lines:
            if not line: continue
            if line[0].kind == self.COMMENT:
                comments.extend(line)
                continue

            # remove comments
            if self.retain_comments:
                prev = None
                for tok in line:
                    if tok.kind == self.COMMENT:
                        if prev:
                            prev.comments = [tok]
                        else:
                            self.error_token("Comment not possible here", tok)
                    prev = tok
                line = [tok for tok in line if tok.kind != self.COMMENT]

            row = line[0].row
            col = line[0].col
            n2 = Node(self.LINE, line)
            n2.comments.extend(comments)
            comments = []

            if col == nested[-1].col:
                nested[-1].node.value.append(n2)
            elif col > nested[-1].col:
                if hasattr(line[0], "semicolon"):
                    nested[-1].node.value.append(n2)
                else:
                    n3 = Node(self.BLOCK, [n2])
                    nested[-1].node.value.append(n3)
                    nes = Nested()
                    nes.row = row
                    nes.col = col
                    nes.node = n3
                    nested.append(nes)
            else:
                while 1:
                    del nested[-1]
                    if not nested or col > nested[-1].col:
                        self.error_pos("Unindent does not match" +
                            " any outer indentation level.",
                            line[0].row, line[0].col)
                    if col == nested[-1].col: break
                nested[-1].node.value.append(n2)

    def parse(self):
        self.get_tokens()
        # at this point, self.lines is a list of lists of tokens
        if self.options.debug_tokens:
            with open(self.options.debug_tokens, "w") as f:
                for l in self.lines:
                    f.write(str(l) + "\n")
                
        self.get_blocks()
        # now we have a tree of nodes

        # handles the special include preprocessor
        self.get_includes()

        self.analyzer = analyzer.Analyzer(self)
        self.analyzer.analyze()

    def add_external_type(self, name, node : Node):
        self.external_types[name] = node

    def add_external_variable(self, variable : analyzer.Variable):
        self.external_variables[variable.name] = variable

    def add_external_function(self, definition):
        """
        definition is in the form written by eout.EWriter:
        (def) (name) (->) (rtype)
        """

        rtype = definition[definition.rfind("->") + 2:].strip()
        fname = definition[4:definition.find(" ", 4)]
        
        t = Token(Parser.STRING, fname, 0, 0)
        node = Node(Parser.FUNCTION, [t])
        node.name = fname
        node.ret = []
        node.parameters = []
        for rt in rtype.split():
            # TODO: maybe re-use a separate parser in module.py to
            # tokenize/parse those definitions, maybe even use a
            # separate Parser to do so
            tokt = Parser.TOKEN if rt != "*" else Parser.SYMBOL
            t = Token(tokt, rt, 0, 0)
            node.ret.append(t)
        self.external_functions[fname] = node
        return node

def get_row_col(node):

    if isinstance(node, Token):
        return node.row, node.col

    if node.kind == Parser.PREPROCESSOR:
        return node.name.row, node.name.col

    if node.kind == Parser.INCLUDE:
        return 0, 0
   
    return get_row_col(node.value[0])
   
