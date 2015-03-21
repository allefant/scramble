import helper, parser

class Variable:
    def __init__(self, name, declaration):
        self.declaration = declaration
        self.name = name

    def __repr__(self):
        return self.name

class Analyzer:
    def __init__(self, parser):
        self.parser = parser
        self.root = parser.root
        self.types = {}
        self.functions = {}
        self.variables = {}
        self.in_class = None

    level = {
        "," : 0,
        "=" : 1,
        "*=" : 1,
        "/=" : 1,
        "%=" : 1,
        "+=" : 1,
        "-=" : 1,
        "<<=" : 1,
        ">>=" : 1,
        "&=" : 1,
        "^=" : 1,
        "|=" : 1,
        "?" : 2,
        ":" : 2,
        "or" : 3,
        "and" : 4,
        "|" : 5,
        "^" : 6,
        "&" : 7,
        "==" : 8,
        "!=" : 8,
        "<" : 9,
        ">" : 9,
        "<=" : 9,
        ">=" : 9,
        "<<" : 10,
        ">>" : 10,
        "+" : 11,
        "-" : 11,
        "*" : 12,
        "/" : 12,
        "%" : 12,

        "(" : 13,
        ")" : 13,
        "}" : 13,
        "]" : 13,
        "{" : 13,
        "[" : 13,

        "++" : 14,
        "--" : 14,
        "sizeof" : 14,
        "~" : 14,
        "not" : 14,

        "." : 15,
        "->" : 15,

        " " : 16,
        
        }
        
    @staticmethod
    def precedence(left, right):
        
        level = Analyzer.level

        for parenthesis in ("()", "[]", "{}"):
            L, R = parenthesis
            if left == L:
                if right == R:
                    return True
                return False
            if right == L: return False
            if left == R: return False
            if right == R: return True

        if level[right] == 0: return True
        if level[left] == 0: return False

        if level[left] == 1: return False
        if level[right] == 1: return True

        if level[left] == 2: return False
        if level[right] == 2: return True

        for l in [3, 4, 5, 6, 7, 8, 9, 10, 11, 12]:
            if level[right] == l: return True
            if level[left] == l: return False

        if level[left] == 14: return False
        if level[right] == 14: return True

        if level[right] == 15:
            if level[left] == 16:
                # Special case to handle this:
                # (A)x.y
                # Normally (A)x has the highest possible precedence, but in
                # this case we want (A)(x.y).
                # A non-hackish solution likely would be to give the type
                # case its own level (with lower precendence than .).
                return False
            return True
        if level[left] == 15: return False

        if level[right] == 16: return True
        if level[left] == 16: return False

    # right is an operator symbol
    @staticmethod
    def precedence_sym(left, right):
        #print("sym «" + left + "» «" + right + "»")
        if right == ")":
            return True
        if left == "{" and right == "}":
            return True
        if left == "[" and right == "]":
            return True

        # hack
        if right == "," and left == "*":
            return True
        return False

    @staticmethod
    def postfix(value):
        if value in ["++", "--"]:
            return True
        return False

    @staticmethod
    def prefix(value):
        if value in ["++", "--", "sizeof"]:
            return True
        return False

    @staticmethod
    def is_tok(token, value = None):
        if token and token.kind == parser.Parser.TOKEN:
            if value is not None:
                return token.value == value
            return True
        return False

    @staticmethod
    def is_op(token):
        return token and (
            token.kind == parser.Parser.TOKEN 
            or token.kind == parser.Parser.OPERATOR 
            or token.kind == parser.Parser.STRING
            )

    @staticmethod
    def is_sym(token, value = None):
        if token and token.kind == parser.Parser.SYMBOL:
            if value is not None:
                return token.value == value
            return True
        return False

    def reduce(self, row, ti):
        p = self.parser

        #print("reduce: " + str(row[ti]))
        #print("        " + str(row))

        if ti <= 0:
            p.error_token("cannot reduce", row[0])

        operand2 = row[ti]
        operation = row[ti - 1]

        if operation.kind in [p.TOKEN, p.OPERATOR]:

            newop = parser.Node(p.OPERATOR, (operation, operand2))
            del row[ti - 1]
            row[ti - 1] = newop
            return

        if self.is_sym(operation, "("):
            if self.is_sym(operand2, ")"):
                right = ti
            else:
                right = ti + 1
                if right >= len(row) or not self.is_sym(row[right], ")"):
                    p.error_token("need closing parenthesis", operation)

            # function call or cast or just parenthesis
            newop = parser.Node(p.OPERATOR, row[ti - 1:right + 1])
            del row[ti:right + 1]
            row[ti - 1] = newop
            return

        if self.is_sym(operation, "{"):
            if self.is_sym(operand2, "}"):
                right = ti
            else:
                right = ti + 1
                if right >= len(row) or not self.is_sym(row[right], "}"):
                    print(row)
                    p.error_token("need closing curly brace", operation)

            # {}
            newop = parser.Node(p.OPERATOR, row[ti - 1:right + 1])
            del row[ti:right + 1]
            row[ti - 1] = newop
            return

        if self.is_sym(operation, "["):
            if self.is_sym(operand2, "]"):
                right = ti
            else:
                right = ti + 1
                if right >= len(row) or not self.is_sym(row[right], "]"):
                    p.error_token("need closing bracket", operation)

            # []
            newop = parser.Node(p.OPERATOR, row[ti - 1:right + 1])
            del row[ti:right + 1]
            row[ti - 1] = newop
            return

        # binary operator
        if ti >= 2 and not self.prefix(operation.value):
            operand1 = row[ti - 2]
            if self.is_op(operand1):
                newop = parser.Node(p.OPERATOR, (operation, operand1, operand2))
                del row[ti - 2:ti]
                row[ti - 2] = newop
                return

        # prefix operator
        newop = parser.Node(p.OPERATOR, (operation, operand2))
        del row[ti - 1:ti]
        row[ti - 1] = newop

    def reduce_postfix(self, row, ti):
        p = self.parser
        operand = row[ti]
        operation = row[ti + 1]
        # None to distinguish postfix from prefix
        newop = parser.Node(p.OPERATOR, (operation, None, operand))
        del row[ti:ti + 1]
        row[ti] = newop
       
    def transform_statement(self, statement):
        if not statement: return
        p = self.parser

        if statement.kind == self.parser.BLOCK:
            self.analyze_block(statement)
            return

        self.transform_row(statement.value)

    def transform_row(self, row):
        if not row: return
        p = self.parser

        # handle textual operators by changing them to symbols
        ti = 0
        while ti < len(row):
            token = row[ti]
            if self.is_tok(token):
                if token.value == "and":
                    token.kind = p.SYMBOL
                elif token.value == "or":
                    token.kind = p.SYMBOL
                elif token.value == "not":
                    token.kind = p.SYMBOL
                elif token.value == "sizeof":
                    token.kind = p.SYMBOL

            # macro concatenation
            if self.is_sym(token, "***"):
                if ti + 1 < len(row):
                    if self.is_tok(row[ti + 1]):
                        del row[ti]
                        row[ti].value = "#" + row[ti].value
                    elif self.is_sym(row[ti + 1], "***"):
                         if ti + 2 < len(row):
                            if self.is_tok(row[ti + 2]):
                                del row[ti:ti + 2]
                                row[ti].value = "##" + row[ti].value
                                
            ti += 1

        # 1 + 2
        # !1 + 2
        # (1 + 2)
        # x(y + 2)
        while True:
            ti = 0

            while ti < len(row):
                token = row[ti]

                left = None
                right = None
                is_op = False

                if ti > 0:
                    left = row[ti - 1]

                if self.is_op(token):
                    is_op = True
                    if ti < len(row) - 1:
                        right = row[ti + 1]

                        # two strings next to each other get concatenated
                        if token.kind == p.STRING and right.kind == p.STRING:
                            del row[ti + 1]
                            token.value += right.value
                            break
                else:
                    # two consecutive operator symbols
                    right = token
                    token = None

                if left:
                    if left.kind != p.SYMBOL:
                        left_value = " "
                    else:
                        left_value = left.value
                    
                    if left_value not in Analyzer.level:
                        p.error_token("Unknown operator " + left_value,
                            left)

                if right:
                    if right.kind != p.SYMBOL:
                        right_value = " "
                    else:
                        right_value = right.value

                    if right_value not in Analyzer.level:
                        p.error_token("Unknown operator " + right_value,
                            right)

                #print("token: " + str(token))
                #print("left: " + str(left))
                #print("right: " + str(right))

                if left and right:
                    if is_op:
                        if self.precedence(left_value, right_value):
                            self.reduce(row, ti)
                            break
                    else:
                        if self.precedence_sym(left_value, right_value):
                            if right_value in ")," and left_value != "(":
                                # If we have "(void *)" we see the "*)" here
                                # and force it to apply the "*" as a postfix
                                # to "void".
                                if ti >= 2:
                                    if self.is_sym(row[ti - 2], "("):
                                        # (*)
                                        self.reduce(row, ti - 1)
                                    else:
                                        self.reduce_postfix(row, ti - 2)
                                else:
                                    p.error_token("Cannot deal with «%s»" % str(row), right_value)
                            else:
                                self.reduce(row, ti)
                            break
                elif left:
                    self.reduce(row, ti)
                    break

                if right and token:
                    if self.postfix(right_value):
                        self.reduce_postfix(row, ti)
                        break
                
                ti += 1
            else:
                break

    def analyze_class(self, name, node):
        node.name = name

        if node.value[0].value == "class":
            node.value[0].value = "struct"
        #for row in block.value:
            #p = helper.parse_parameter_list(self.parser, row.value)
            #node.fields += p

        prev = self.in_class
        self.in_class = node
        self.transform_statement(node.block)
        self.in_class = prev

    def analyze_function(self, name, node, retlist, paramlist):
        node.name = name
        node.parameters = helper.parse_parameter_list(self.parser, paramlist)
        node.ret = retlist

    def find_token_pos(self, tokens, name):
        for ti in range(len(tokens)):
            if self.is_tok(tokens[ti], name):
                return ti

    def analyze_block(self, block_node):
        block_node.variables = []
        nodes = block_node.value
        p = self.parser
        ni = 0

        while ni < len(nodes):
            node = nodes[ni]
            ni += 1

            def add_block():
                nonlocal node
                block = nodes[ni] if ni < len(nodes) else None
                if block and block.kind == p.BLOCK:
                    del nodes[ni]
                    node.block = block
                else:
                    node.block = None

            # detect if the statement declares a variable
            # TODO: As long as we don't have knowledge of which tokens
            # are types, this is only a crude heuristic.
            def check_variable_declaration(first):
                if first.kind == self.parser.OPERATOR:
                    tokens = first.value
                    op = tokens[0]
                    if op.kind == self.parser.SYMBOL:
                        if op.value == "*":
                            if len(tokens) == 3:
                                v = Variable(first.value[2].value,
                                    first.value)
                                block_node.variables.append(v)
                        if op.value == "=":
                            check_variable_declaration(tokens[1])
            
            if node.kind == self.parser.LINE:
                tokens = node.value

                t = tokens[0]

                if self.is_tok(t, "static"):
                    del tokens[0]
                    t = tokens[0]
                    node.is_static = True
                    
                elif self.is_tok(t, "global"):
                    del tokens[0]
                    t = tokens[0]
                    node.is_global = True

                if self.is_sym(t, "***"):
                    node.kind = p.PREPROCESSOR
                    del node.value[0]
                    node.name = node.value[0]
                    del node.value[0]
                    self.transform_statement(node)
                    continue

                elif self.is_tok(t, "class") or self.is_tok(t, "union") or\
                        self.is_tok(t, "typedef"):
                    add_block()
                    node.parent_class = self.in_class

                    name = tokens[1] if len(tokens) > 1 else None
                    self.analyze_class(name, node)

                    if not self.in_class:
                        self.types[name.value] = node

                    node.kind = self.parser.TYPE

                    continue

                elif self.is_tok(t, "import"):
                    node.kind = p.IMPORT
                    continue

                elif self.is_tok(t, "goto"):
                    node.kind = p.GOTO
                    continue

                elif self.is_tok(t, "label"):
                    node.kind = p.LABEL
                    continue

                elif self.is_tok(t, "enum"):
                    node.kind = p.ENUM
                    add_block()
                    continue

                elif self.is_tok(t, "macro"):
                    node.kind = p.MACRO
                    add_block()
                    
                    node.replacement = None

                    del node.value[0] # macro token

                    if not node.block:
                        if len(tokens) > 1:
                            name = tokens[0]
                            end = name.col + len(name.value)
                            if tokens[1].col == end:
                                y = helper.find_matching_parenthesis(
                                    p, tokens, 1)
                                if y is not None:
                                    node.replacement = tokens[y + 1:]
                                    del tokens[y + 1:]
                            if node.replacement is None:
                                node.replacement = tokens[1:]
                                del tokens[1:]
                        node.block = None
                    self.transform_statement(node)
                    self.transform_row(node.replacement)
                    self.transform_statement(node.block)
                    continue

                elif self.is_tok(t, "for"):
                    add_block()
                    node.name = t
                    del node.value[0]
                    node.kind = p.STATEMENT
                    node.sub_kind = None

                    sub_pos = self.find_token_pos(tokens, "in")
                    if sub_pos is not None:
                        if self.is_tok(tokens[sub_pos + 1], "range"):
                            node.sub_kind = "range"
                            node.part = tokens[sub_pos + 2:]
                        else:
                            node.sub_kind = "in"
                            node.part = tokens[sub_pos + 1:]
                        del tokens[sub_pos:]
                    else:
                        sub_pos = self.find_token_pos(tokens, "while")
                        if sub_pos is not None:
                            node.sub_kind = "while"
                            node.part = tokens[sub_pos + 1:]
                            node.part2 = None
                            del tokens[sub_pos:]
                            sub_pos2 = self.find_token_pos(node.part, "with")
                            if sub_pos2 is not None:
                                node.part2 = node.part[sub_pos2 + 1:]
                                del node.part[sub_pos2:]
                                self.transform_row(node.part2)
                        else:
                            p.error_token("Invalid for loop.", t)

                    self.transform_statement(node)

                    if node.value:
                        check_variable_declaration(node.value[0])
                    if node.sub_kind:
                        self.transform_row(node.part)

                    
                    self.transform_statement(node.block)
                        
                    continue

                def_pos = self.find_token_pos(tokens, "def")

                if def_pos is not None:
                    ti = def_pos

                    add_block()
                    self.transform_statement(node.block)

                    if ti + 1 == len(tokens):
                        p.error_pos("Definition without name.",
                            tokens[ti].row, tokens[ti].col)

                    node.is_pointer = False
                    name = tokens[ti + 1]
                    if len(tokens) > ti + 2 and self.is_sym(name, "*"):
                        del tokens[ti + 1]
                        name = tokens[ti + 1]
                        node.is_pointer = True

                    node.parent_class = self.in_class

                    if len(tokens) == ti + 2:
                        self.analyze_function(name, node, tokens[:ti], [])
                    else:
                        if tokens[ti + 2].value != "(":
                            p.error_pos("Invalid function definition",
                                tokens[ti + 2].row, tokens[ti + 2].col)

                        if tokens[-1].value != ")":
                            p.error_pos("Invalid function definition",
                                tokens[-1].row, tokens[-1].col)
                        
                        self.analyze_function(name, node,
                            tokens[:ti],
                            tokens[ti + 3:-1])
                    self.functions[name] = node

                    node.kind = self.parser.FUNCTION

                    continue

                if t.kind == p.TOKEN and t.value in [
                        "switch", "while", "if", "elif", "else", "return",
                        "pass", "default", "case"]:
                    add_block()
                    node.name = t
                    del node.value[0]
                    self.transform_statement(node)

                    node.kind = p.STATEMENT
                    
                    self.transform_statement(node.block)
                    
                    continue

                #if t.kind == p.TOKEN:
                #    node.kind = p.COMMAND
                #    node.name = t
                #    del node.value[0]
                #    continue

                self.transform_statement(node)

                check_variable_declaration(node.value[0])

            if node.kind == self.parser.BLOCK:
                self.analyze_block(node)
                

    def analyze(self):
        self.analyze_block(self.root)
