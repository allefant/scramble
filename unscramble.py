#!/usr/bin/env python3
import sys, re

if len(sys.argv) == 1:
    sys.stderr.write("unscramble input.c [output.py]\n")
    sys.exit(-1)

input = sys.argv[1]
if len(sys.argv) == 2:
    dot = input.rfind(".")
    output = input[:dot] + ".py"
else:
    output = sys.argv[2]

def parenthesis_balance(l, x, y):
    b = 0
    s = 0
    e = 0
    pos = 0
    for c in l:
        pos += 1
        if e:
            e = 0
        elif s:
            if c == "\\":
                e = 1
            elif s == 1 and c == "\"":
                s = 0
            elif s == 2 and c == "'":
                s = 0
        elif c == "\"":
            s = 1
        elif c == "'":
            s = 2
        elif c == x:
            b += 1
        elif c == y:
            b -= 1
            if b <= 0: return pos
    return pos

inf = open(input)
ouf = open(output, "w")

text = inf.read()

# // comments
text = re.compile(r"//").sub("# ", text)
# /* */ comments
def cb(mob):
    text = mob.group(0)[2:-2]
    text = re.compile(r"\n ?(\s*)\*?").sub(r"\n\1#", text)
    return "#" + text
text = re.compile(r"/\*.*?\*/", re.S).sub(cb, text)
# remove ; at end of line
text = re.compile(r";$", re.M).sub("", text)
text = re.compile(r";(\s*#)", re.M).sub(r"\1", text)
# convert else if
text = re.compile(r"\belse\s*if\b").sub(r"elif ", text)
# convert elif, if, while, for so they have no more ()
pos = 0
while 1:
    mob = re.compile(r"\b(elif|if|while|for)\b\s*\(").search(text[pos:])
    if not mob: break
    pos = pos + mob.end(0) - 1
    pos2 = pos + parenthesis_balance(text[pos:], "(", ")")
    colon = ""
    if not re.compile(r"\s*{").match(text[pos2:]): colon = ":"
    condition = re.compile(r"^!\s*").sub("not ", text[pos + 1:pos2 - 1])
    text = text[:pos] + condition + colon + text[pos2:]
# remove {
text = re.compile(r"\n\s*{\s*$", re.M).sub(":", text)
# remove }
text = re.compile(r"^\s*}\s*$", re.M).sub("", text)
# convert function declarations
def cb(mob):
    text = mob.group(0)
    text = re.compile(r"\(void\)").sub("()", text)
    text = re.compile(r"^(.*?)\s*\b(\w+)\s*\(").sub(r"\1 def \2(", text)
    text = re.compile(r"^static\s+void\s+def\b").sub(r"static def", text)
    text = re.compile(r"^void\s+def\b").sub(r"def", text)
    return text
text = re.compile(r"^\w.*?\b\w+\s*\(.*?$", re.M).sub(cb, text)
# convert #define
text = re.compile(r"#define").sub("macro", text)
# convert #include
text = re.compile(r'#include\s*"(.*)\.h"').sub(r"import \1", text)
text = re.compile(r'#include\s*<(.*)\.h>').sub(r"import global \1", text)
# convert struct
text = re.compile(r"\bstruct\b").sub("class", text)
# adjust for loops
text = re.compile(r"\bfor\b(.*?);(.*?);(.*?):").sub(r"for\1 while\2 with\3:", text)
    
ouf.write(text)
