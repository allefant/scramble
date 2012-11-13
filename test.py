#!/usr/bin/env python3
from parser import *
from sout import *
from cout import *
import sys, traceback

G = "\x1b[1;32m"
R = "\x1b[1;31m"
O = "\x1b[0m"

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

def print_diff(new, old):
    new_lines = new.splitlines()
    old_lines = old.splitlines()
    for row in range(len(new_lines)):
        for i in range(len(new_lines[row])):
            c = new_lines[row][i]
            ok = False
            if row < len(old_lines):
                if i < len(old_lines[row]):
                    if c == old_lines[row][i]:
                        ok = True
            if ok:
                sys.stdout.write(O)
                sys.stdout.write(c)
            else:
                sys.stdout.write(R)
                if ord(c) <= 32:
                    c = "«%d»" % ord(new_lines[row][i])
                sys.stdout.write(c)
        sys.stdout.write(R)
        if row < len(old_lines):
            for j in range(i + 1, len(old_lines[row])):
                sys.stdout.write("?")
        sys.stdout.write("\n")
    if len(old_lines) < len(new_lines):
        sys.stdout.write(R)
        sys.stdout.write("line missing\n")
    sys.stdout.write(O)

def c_test(prog, exp):
    exp = exp.strip()
    exp = '#include "test.h"\n' + exp
    p = Parser("test", prog)
    try:
        p.parse()
        c = CWriter()
        code, header = c.generate(p, "test", 1, "_TEST")
        code = code.strip()
    except Exception as e:
        traceback.print_exc()
        code = ""
    
    if code == exp:
        return True

    print_diff(code, exp)

    s = SWriter()
    code = s.generate(p)
    print(code)

    return False

def h_test(prog, exp):
    exp = exp.strip()
    exp = "#ifndef _TEST_TEST_\n#define _TEST_TEST_\n" + exp + "\n#endif"
    p = Parser("test", prog)
    p.parse()
    c = CWriter()
    code, header = c.generate(p, "test", 1, "_TEST")
    header = header.strip()
    if header == exp:
        return True
    print("<" + header + ">")

    s = SWriter()
    code = s.generate(p)
    print(code)
    return False

def test_sameline():
    return c_test("""
int def a(int x): x *= 2; return x
""", """
int a(int x) {
    x *= 2;
    return x;
}""")

def test_sameline2():
    return c_test("""
while (a = 1); a = 2 # a commment
while (a = 1): a = 2
""", """
while ((a = 1)) {
}
a = 2;
while ((a = 1)) {
    a = 2;
}
""")

def test_tertiary():
    return c_test("if a == x > 2 ? 2 : x: y = 3", """
if (a == x > 2 ? 2 : x) {
    y = 3;
}""")


def test_for():
    return c_test("""
for int x = 0 while x < 10 with x++:
    pass
""", """
for (int x = 0; x < 10; x++) {
    ;
}
""")

def test_for_nested():
    return c_test("""
for int x = 0 while x < 10 with x++:
    for int y = 0 while y < 10 with y++:
        a = x
        b = y
""", """
for (int x = 0; x < 10; x++) {
    for (int y = 0; y < 10; y++) {
        a = x;
        b = y;
    }
}
""")

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
void ( * ) ( int x ) x(void ( * f ) ( int x , void * g ), void * g) {
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
macro X (x)""", """
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
x:;
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

def test_for_range4():
    return c_test("""
for x in range(9, 2, -2): print(x)
    """, """
for (x = 9; x > 2; x += - 2) {
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

def test_for_in():
    return c_test("""
for MyElem *x in MyArray *arr: handle(x)
    """, """
{
    MyArrayIterator __iter0__ = MyArrayIterator_first(arr);
    for (MyElem * x = MyArrayIterator_item(arr, &__iter0__); MyArrayIterator_next(arr, &__iter0__); x = MyArrayIterator_item(arr, &__iter0__)) {
        handle(x);
    }
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
A"
B'
C
'''
    """, r"""
x = "\n"
    "A\"\n"
    "B'\n"
    "C\n"
    "";
""")

def test_ellipsis():
    return c_test("""
def x(...):
    pass
""", """
void x(...) {
    ;
}
""")

def test_ellipsis2():
    return c_test("""
def x(int a, b, ...):
    pass
""", """
void x(int a, int b, ...) {
    ;
}
""")

def test_array_init():
    return c_test("""
int a[] = {1, 2, 3}
""", """
int a [] = {1, 2, 3};
""")

def test_array_init2():
    return c_test("""
LandVector v = {a[0], a[1], a[2]}
""", """
LandVector v = {a [0], a [1], a [2]};
""")

def test_empty_call():
    return c_test("""
a()
b ()
c ( )
(d)();
""", """
a();
b();
c();
(d)();
""")

def test_cast():
    return c_test("""
x = (unsigned int)(2)
""", """
x = (unsigned int)(2);
""")

def test_cast2():
    return c_test("""
return (void *)self
""", """
return (void *) self;
""")

def test_foward_decl():
        return c_test("""
static def x()
static def y()
""", """
static void x(void);
static void y(void);
""")

def test_empty_for_while():
    return c_test("""
for while with:
    pass
""", """
for (; ; ) {
    ;
}
""")

def test_string_concat():
    return c_test("""
x = "a" "b"
""", """
x = "a""b";
""")

def test_postfix():
    return c_test("""
x++
""", """
x++;
""")

def test_prefix():
    return c_test("""
--x
""", """
--x;
""")

def test_var():
    return c_test("""
static unsigned int const * const *v = (unsigned int **){{3}}, **w = v + 1
""", """
static unsigned int const * const * v = (unsigned int * *) {{3}}, * (* w) = v + 1;
""")

def test_callback():
    return c_test("""
def x(void (*(*cb)())()): *cb()()
""", """
void x(void ( * ( * cb ) ( ) ) ( )) {
    * cb()();
}
""")

def test_class_member():
    return c_test("""
static class A:
    int *def *x(int, int)
""", """
typedef struct A A;
struct A {
    int * (*x)(int, int);
};
""")

def test_union():
    return c_test("""
static union A:
    int x
    union:
        int y
        float z
""", """
typedef union A A;
union A {
    int x;
    union {
        int y;
        float z;
    };
};
""")

def test_elif():
    return c_test("""
if x: A
elif y: B
else: C
""", """
if (x) {
    A;
}
else if (y) {
    B;
}
else {
    C;
}
""")

def test_case():
    return c_test("""
switch x * 2:
    case a, b:
        A
        break
    case c:
        pass
    default:
        D
""", """
switch (x * 2) {
    case a:
    case b: {
        A;
        break;
    }
    case c: {
        ;
    }
    default: {
        D;
    }
}
""")

def test_no_extra_parentheses():
    return c_test("""
x = (void *)&(int)y
""", """
x = (void *) & (int) y;
""")

def test_pointer_params():
    return c_test("""
int **def *x(int *, int **)
""", """
int * * (*x)(int *, int * *);
""")  

def test_typedef():
    return c_test("""
static typedef A B
""", """
typedef A B;
""")  

def test_cast_prefix():
    return c_test("""
if len < (int)sizeof(var) - 1: len++
""", """
if (len < (int) sizeof (var) - 1) {
    len++;
}
""")  

def test_macro_concat():
    return c_test("""
static macro add(x):
    _add_fnc(l, ***x, fun_******x)
""", """
#define add(x) \\
    _add_fnc(l, #x, fun_ ##x);
""") 

def test_global_var_header():
    return h_test("""
global A *a
global double const pi = 3
""", """
extern A * a;
extern double const pi;
""") 


def main():
    test = sys.argv[1] if len(sys.argv) > 1 else None
    total = 0
    failed = 0
    for name, func in sorted(globals().items()):
        if name.startswith("test"):
            if test and test != name: continue
            result = func()
            total += 1
            if result:
                print("%s%4s%s %s" % (G, "OK", O, name))
            else:
                failed += 1
                print("%s%4s%s %s" % (R, "FAIL", O, name))
    if failed == 0:
        print("%s%4s%s All is well. (%d/%d)" % (G, "OK", O, total, total))
    else:
        print("%s%4s%s %d/%d failed!" % (R, "FAIL", O, failed, total))

if __name__ == "__main__":
    main()
