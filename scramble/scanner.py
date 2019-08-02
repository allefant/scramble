def scan(filename):
    for row in open(filename):
        if row.startswith("import "):
            print_paths(row[len("import "):])
        if row.startswith("static import "):
            print_paths(row[len("static import "):])
            
def print_paths(row):
    imports = [x.strip() for x in row.split(",")]
    for i in imports:
        if i.startswith("global "): continue
        print(i.replace(".", "/") + ".py")
