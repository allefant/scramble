import parser
import analyzer
import glob

def parse_all(p, modules):
    for module in modules:
        for e in glob.glob(module + "/*.e"):
            parse_e_file(p, open(e).read())

def parse_e_file(p : parser.Parser, text):
    type_name = None
    for row in text.splitlines():
        a = row.split(":")
        if len(a) == 1:
            name = a[0]
            if name.startswith("def "):
                rtype = name[name.rfind("->") + 2:].strip()
                fname = name[4:name.find(" ", 4)]
                p.add_external_function(fname, rtype)
            elif name not in p.external_types:
                block = parser.Node(p.BLOCK, [])
                block.variables = []
                p.add_external_type(name, block)
            type_name = name
        else:
            name, kind = a[0], a[1]
            if name.startswith(" ") and type_name.startswith("def "):
                pass
            else:
                node = parser.Node(p.OPERATOR, [
                    # TODO: ** and so on pointers
                    parser.Token(p.SYMBOL, "*", 0, 0),
                    parser.Token(p.TOKEN, kind.strip(" *"), 0, 0)
                    ])
                v = analyzer.Variable(name.strip(), node)
                if name.startswith(" "):
                    p.external_types[type_name].variables.append(v)
                else:
                    p.add_external_variable(v)
                        
