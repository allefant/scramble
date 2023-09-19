from . import parser
from . import analyzer
from . import helper
import glob

def parse_all(p, modules):
    for module in modules:
        for e in glob.glob(module + "/**/*.e", recursive = True):
            parse_e_file(p, open(e).read())

def parse_e_file(p : parser.Parser, text):
    type_name = None
    current_fun = None
    for row in text.splitlines():
        a = row.split(":")
        if len(a) == 1:
            name = a[0]
            current_fun = None
            if name.startswith("def "):
                current_fun = p.add_external_function(name)
            elif name not in p.external_types:
                block = parser.Node(p.BLOCK, [])
                block.variables = []
                p.add_external_type(name, block)
            type_name = name
        else:
            name, kind = a[0], a[1]
            if name.startswith(" ") and current_fun:
                # function parameter
                par = helper.Parameter()
                par.name = name.strip()
                par.declaration = kind
                current_fun.parameters.append(par)
            else:
                node = parser.Node(p.OPERATOR, [
                    # TODO: ** and so on pointers
                    parser.Token(p.SYMBOL, "*", 0, 0),
                    parser.Token(p.TOKEN, kind.strip(" *"), 0, 0),
                    parser.Token(p.TOKEN, name.strip(), 0, 0)
                    ])
                v = analyzer.Variable(name.strip(), node)
                if name.startswith(" "):
                    p.external_types[type_name].variables.append(v)
                else:
                    p.add_external_variable(v)
                        
