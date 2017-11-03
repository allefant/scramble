from .parser import *
from . import helper

class_dep = {}
imports = {}
provided_by_file = {}
needed_by_file = {}

def parse_block(p, b, fname):
    expect_class = False
    imports[fname] = []
    for s in b.value:
        if s.kind == p.INCLUDE:
            parse_block(p, s.value.root)
            continue
        if s.kind == p.IMPORT:
            is_global = False
            name = ""
            for x in s.value[1:]:
                if x.kind == p.SYMBOL:
                    if x.value in [".", "/"]:
                        name += "/"
                    elif x.value == ",":
                        if is_global:
                            imports[fname].append(name)
                            name = ""
                    else:
                        name += x.value
                elif x.kind == p.TOKEN:
                    if x.value == "global":
                        is_global = True
                        name = ""
                    elif x.value == "if":
                        name += " if "
                    elif x.value == "defined":
                        name += "defined "
                    else:
                        name += x.value
            if is_global and name:
                imports[fname].append(name)
            continue
        if s.kind == p.TYPE:
            if s.value[0].value in ["struct", "union"]:
                name = s.value[1].value
            elif s.value[0].value == "typedef":
                name = s.value[-1].value
            provided_by_file[name] = fname

            if s.block:
                for line in s.block.value:
                    if line.kind != p.LINE:
                        p.error_token("expected field declaration", line)

                    def parse_field(f):
                        if f.kind != p.OPERATOR:
                            # probably a comment line
                            return
                        fields = f.value
                        if fields[0].kind == p.TOKEN:
                            the_type = fields[0].value
                        elif fields[0].kind == p.SYMBOL:
                            if fields[0].value == ',':
                                parse_field(fields[1])
                                return
                            elif fields[0].value == '*':
                                # we ignore pointers
                                return
                            else:
                                # TODO
                                return
                        else:
                            # TODO: could for example be an array
                            return

                        deps = class_dep.get(name, set())
                        class_dep[name] = deps | set([the_type])

                    parse_field(line.value[0])
            else:
                pass # probably a typedef
        elif s.kind == p.FUNCTION:
            if len(s.value) > 4:
                params = helper.parse_parameter_list(p, s.value[3:-1])
                for param in params:
                    decl = param.declaration
                    param_type = decl[0].value
                    if len(decl) > 1:
                        if decl[1].value == "*":
                            # we ignore pointers
                            continue
                    deps = needed_by_file.get(name, set())
                    needed_by_file[fname] = deps | set([param_type])

def join(names, output):

    for name in names:
        text = open(name, "r").read()
        p = Parser(name, text)
        try:
            p.parse()
        except MyError as e:
            print(e)
            exit(1)

        parse_block(p, p.root, name)

    types = set(provided_by_file.keys())

    fdep = {}
    for t, needs in class_dep.items():
        fdep[provided_by_file[t]] = fdep.get(provided_by_file[t], set())

        for need in needs:
            if need not in provided_by_file:
                continue
            if provided_by_file[need] == provided_by_file[t]:
                continue
            fdep[provided_by_file[t]].add(provided_by_file[need])

    for f, needs in needed_by_file.items():
        for t in needs:
            if t in provided_by_file and provided_by_file[t] != f:
                fdep[f] = fdep.get(f, set())
                fdep[f].add(provided_by_file[t])

    all_imports = set()
    for x in imports:
        all_imports |= set(imports[x])

    for imp in sorted(all_imports):
        output.write(("import global " + imp + "\n").encode("utf8"))

    already = set()
    later = set(names)
    while later:
        name = later.pop()

        def skip():
            if name in fdep:
                for d in fdep[name]:
                    if d not in already:
                        return True
            return False

        if skip():
            later.add(name)
            continue               
                
        prefix = name.replace("/", "_")
        if prefix.endswith(".py"): prefix = prefix[:-3]
        output.write(("include \"" + name + "\" ignore_local_imports \"" +
            prefix + "\"\n").encode("utf8"))
        already.add(name)
