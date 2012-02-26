from parser import *

dep = {}
in_file = {}

def parse_block(p, b, fname):
    expect_class = False
    for s in b.value:
        if s.kind == p.INCLUDE:
            parse_block(p, s.value.root)
            continue
        if s.kind == p.LINE:
            expect_class = False
            tokens = s.value
            if not tokens: continue
            if tokens[0].kind != p.TOKEN: continue
            if tokens[0].value == "class":
                name = tokens[1].value
                in_file[name] = fname
                expect_class = True
        if s.kind == p.BLOCK and expect_class:
            if expect_class:
                expect_class = False

                for s2 in s.value:
                    if s2.kind == p.LINE:
                        tokens2 = s2.value
                        
                        if len(tokens2) >= 2:
                            the_type = tokens2[0].value
                            # pointer
                            if tokens2[1].value == "*":
                                continue
                            # function pointer
                            if tokens2[1].value == "(":
                                continue
                            deps = dep.get(name, [])
                            dep[name] = deps + [the_type]
                            

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
    
    types = set(dep.keys())
    for t in types:
        dep[t] = [x for x in dep[t] if x in types]
        if not dep[t]: del dep[t]
    
    fdep = {}
    for t, needs in dep.items():
        fdep[in_file[t]] = fdep.get(in_file[t], []) + [in_file[x] for x in needs if in_file[x] != in_file[t]]

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
        output.write("include \"" + name + "\" ignore_local_imports \"" +
            prefix + "\"\n")
        already.add(name)
