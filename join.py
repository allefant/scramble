from parser import *

dep = {}
in_file = {}

def parse_block(p, b, fname):
    expect_class = False
    for s in b.value:
        if s.kind == p.INCLUDE:
            parse_block(p, s.value.root)
            continue
        if s.kind == p.TYPE:
            if s.value[0].value in ["struct", "union"]:
                name = s.value[1].value
            elif s.value[0].value == "typedef":
                name = s.value[-1].value
            in_file[name] = fname

            if s.block:
                for line in s.block.value:
                    if line.kind != p.LINE:
                        p.error_token("expected field declaration", line)

                    def parse_field(f):
                        if line.value[0].kind != p.OPERATOR:
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
                            # TODO: could for example be a an array
                            return

                        deps = dep.get(name, [])
                        dep[name] = deps + [the_type]

                    parse_field(line.value[0])
            else:
                pass # probably a typedef

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

    types = set(in_file.keys())

    fdep = {}
    for t, needs in dep.items():
        fdep[in_file[t]] = fdep.get(in_file[t], [])

        for need in needs:
            if need not in in_file:
                continue
            if in_file[need] == in_file[t]:
                continue
            fdep[in_file[t]].append(in_file[need])

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
