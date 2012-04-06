#!/usr/bin/env python3
from parser import *
from sout import *
from cout import *

def s_test(prog, exp):
    exp = exp.strip()
    p = Parser("test", prog)
    p.parse()
    s = SWriter()
    code = s.generate(p)
    code = code.strip()
    if code == exp:
        return True
    print("<" + code + ">")
    return False

def c_test(prog, exp, c99 = True):
    exp = exp.strip()
    exp = '#include "test.h"\n' + exp
    p = Parser("test", prog)
    p.parse()
    c = CWriter()
    code, header = c.generate(p, "test", 1, "_TEST", c99)
    code = code.strip()
    if code == exp:
        return True
    print("<" + code + ">")
    return False

def h_test(prog, exp, c99 = True):
    exp = exp.strip()
    exp = "#ifndef _TEST_TEST_\n#define _TEST_TEST_\n" + exp + "\n#endif"
    p = Parser("test", prog)
    p.parse()
    c = CWriter()
    code, header = c.generate(p, "test", 1, "_TEST", c99)
    header = header.strip()
    if header == exp:
        return True
    print("<" + header + ">")
    return False

def test_sameline():
    return s_test("""
int def a(int x): x *= 2; return x
""", """
int def a(int x):
    x *= 2
    return x
""")

def test_sameline2():
    return s_test("""
while (a = 1); a = 2 # a commment
while (a = 1): a = 2
""", """
while(a = 1)
a = 2
while(a = 1):
    a = 2
""")

def test_tertiary():
    return s_test("if a == x > 2 ? 2 : x: y = 3", """
if a == x > 2 ? 2 : x:
    y = 3
""")


def test_for():
    return c_test("""
for int x = 0 while x < 10 with x++:
    pass
""", """
for (int x = 0; x < 10; x++) {
    ;
}""")

def test_for_noc99():
    return c_test("""
for int x = 0 while x < 10 with x++:
    pass
""", """
{int x; for (x = 0; x < 10; x++) {
    ;
}
}
""", False)

def test_void():
    return c_test("""
def x(): pass
""", """
void x(void) {
    ;
}""")

def test_param():
    return c_test("""
def x(char const *a, *b, *c, float x, y, z): pass
""", """
void x(char const * a, char const * b, char const * c, float x, float y, float z) {
    ;
}""")

def test_param2():
    return c_test("""
void (*)(int x) def x(void (*f)(int x, void *g), void *g): pass
""", """
void( * ) (int x) x(void( * f) (int x, void * g) , void * g) {
    ;
}""")

def test_param3():
    return c_test("""
def x(int **a, b, *c, **d): pass
""", """
void x(int * * a, int b, int * c, int * * d) {
    ;
}""")

def test_import_multi():
    return c_test("""
static import a, b, c
""", """
#include "a.h"
#include "b.h"
#include "c.h"
""")

def test_import_global():
    return c_test("""
static import global a
static import b, global c, d
""", """
#include <a.h>
#include "b.h"
#include <c.h>
#include <d.h>
""")

def test_import_module():
    return c_test("""
static import a.b, c.d.e, e/f, g/h.j
""", """
#include "a/b.h"
#include "c/d/e.h"
#include "e/f.h"
#include "g/h/j.h"
""")

def test_static():
    return h_test("""
static def a(): pass
def b(): pass""", "void b(void);")

def test_macro():
    return h_test("""
macro A 1
macro B 2""", """
#define A 1
#define B 2
""")

def test_macro2():
    return h_test("""
macro A:
    def x():
        pass
""", """
#define A \\
    void x(void) { \\
        ; \\
    }
""")

def test_macro3():
        return h_test("""
macro X(x)
macro X = (x)""", """
#define X(x)
#define X (x)""")

def test_preprocessor():
    return h_test("""
global *** "ifdef" TEST""",
"""
#ifdef TEST
""")

def test_preprocessor2():
    return c_test("""
def x():
    *** "if" defined(TEST) and not defined(DEBUG)
    print(m)
    *** "endif"
""", """
void x(void) {
    #if defined(TEST) && ! defined(DEBUG)
    print(m);
    #endif
}
""")

def test_enum():
    return h_test("""
enum Test:
    a
    b
    c
""", """
typedef enum Test Test;
enum Test {
    a,
    b,
    c
};
""")

def test_enum2():
    return h_test("enum: x", """
enum {
    x
};
""")

def test_label():
    return c_test("label x; goto x", """
x :;
goto x;""")

def test_for_range():
    return c_test("""
for x in range(10): print(x)
    """, """
for (x = 0; x < 10; x += 1) {
    print(x);
}
""")

def test_for_range2():
    return c_test("""
for x in range(1, 10): print(x)
    """, """
for (x = 1; x < 10; x += 1) {
    print(x);
}
""")

def test_for_range3():
    return c_test("""
for x in range(2, 10, 3): print(x)
    """, """
for (x = 2; x < 10; x += 3) {
    print(x);
}
""")

def test_for_range_type():
    return c_test("""
for int x in range(2): print(x)
    """, """
for (int x = 0; x < 2; x += 1) {
    print(x);
}
""")

def test_meta():
    return c_test("""
***scramble
x = 2
parse("print(" + str(x) + ")")
***
    """, """
print(2);
""")

def test_triple():
    return c_test("""
x = '''
A
B
C
'''
    """, r"""
x = "\n"
    "A\n"
    "B\n"
    "C\n"
    "";
""")

G = "\x1b[1;32m"
R = "\x1b[1;31m"
O = "\x1b[0m"

def main():
    for name, func in sorted(globals().items()):
        if name.startswith("test"):
            result = func()
            if result:
                print("%s%4s%s %s" % (G, "OK", O, name))
            else:
                print("%s%4s%s %s" % (R, "FAIL", O, name))

if __name__ == "__main__":
    main()
