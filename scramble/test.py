#!/usr/bin/env python3
from .parser import *
from .sout import SWriter
from .cout import *
from .eout import EWriter
import sys, traceback
from . import module

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

def e_test(prog, exp):
    exp = exp.strip()
    p = Parser("test", prog)
    p.parse()
    e = EWriter()
    code = e.generate(p)
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

def c_test(prog, exp_c, external=None):
    return ch_test(prog, exp_c=exp_c, external=external)

def h_test(prog, exp):
    return ch_test(prog, exp_h=exp)

def _comp(name, p, exp, code):
    print("Expected %s:" % name)
    print_diff(exp, code)
    print("Found %s:" % name)
    print(code)

    print("Found parser tokens:")
    s = SWriter()
    code = s.generate(p)
    print(code)

def ch_test(prog, exp_c=None, exp_h=None, external=None):

    p = Parser("test", prog, comments=True)

    if external:
        p2 = Parser("external", external)
        p2.parse()
        ecode = EWriter().generate(p2)
        module.parse_e_file(p, ecode)

    try:
        p.parse()
        c = CWriter()
        code, header = c.generate(p, "test", 1, "_TEST")
        code = code.strip()
        header = header.strip()
    except Exception as e:
        traceback.print_exc()
        code = ""
        header = ""

    if exp_c:
        exp = exp_c.strip()
        exp = '#include "test.h"\n' + exp
        if code != exp:
            _comp("c", p, exp, code)
            return False

    if exp_h:
        exp = exp_h.strip()
        exp = "#ifndef _TEST_TEST_\n#define _TEST_TEST_\n" + exp + "\n#endif"
        if header != exp:
            _comp("h", p, exp, header)
            return False

    return True

def err_test(prog, err):
    p = Parser("test", prog, comments = True)
    try:
        p.parse()
        c = CWriter()
        code, header = c.generate(p, "test", 1, "_TEST")
        code = code.strip()
    except parser.MyError as e:
        if e.value == err:
            return True
        print("Expected:", err)
        print("But got: ", e.value)
    except Exception as e:
        traceback.print_exc()

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
while (a = 1); a = 2 # a comment
while (a = 1): a = 2 # another one
""", """
while ((a = 1)) {
}
static a = 2 /* a comment */;
while ((a = 1)) {
    a = 2 /* another one */;
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

def test_for_nested_iter():
    return c_test("""
for MyElem *x in MyArray *arr:
    for MyElem *y in MyArray *arr2:
        handle(x, y)
    """, """
{
    MyArrayIterator __iter0__ = MyArrayIterator_first(arr);
    for (MyElem * x = MyArrayIterator_item(arr, &__iter0__); MyArrayIterator_next(arr, &__iter0__); x = MyArrayIterator_item(arr, &__iter0__)) {
        {
            MyArrayIterator __iter1__ = MyArrayIterator_first(arr2);
            for (MyElem * y = MyArrayIterator_item(arr2, &__iter1__); MyArrayIterator_next(arr2, &__iter1__); y = MyArrayIterator_item(arr2, &__iter1__)) {
                handle(x, y);
            }
        }
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
void(*)(int x) x(void(* f)(int x, void * g), void * g) {
    ;
}""")

def test_param3():
    return c_test("""
def x(int **a, b, *c, **d): pass
""", """
void x(int * (* a), int b, int * c, int * (* d)) {
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
static import b
static import global c, d
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

def test_static_variable():
    return c_test("""
int a
static int b
global int c
""", """
static int a;
static int b;
int c;
""")

def test_static_call():
    return c_test("""
fun() # a macro call
""", """
fun() /* a macro call */;
""")

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

def test_for_in_auto():
    return c_test("""
class Global:
    MyArray *arr
Global *g
for MyElem *x in g.arr: handle(x)
    """, """
static Global * g;
{
    MyArrayIterator __iter0__ = MyArrayIterator_first(g->arr);
    for (MyElem * x = MyArrayIterator_item(g->arr, &__iter0__); MyArrayIterator_next(g->arr, &__iter0__); x = MyArrayIterator_item(g->arr, &__iter0__)) {
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

def test_meta2():
    return c_test("""
***scramble
parse('x = ""')
***
    """, """
static x = "";
""")

def test_triple():
    return c_test("""
x = '''
A"
B'
C
'''
    """, r"""
static x = "\n"
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
static int a [] = {1, 2, 3};
""")

def test_array_init2():
    return c_test("""
LandVector v = {a[0], a[1], a[2]}
""", """
static LandVector v = {a [0], a [1], a [2]};
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
static (d)();
""")

def test_cast():
    return c_test("""
x = (unsigned int)(2)
""", """
static x = (unsigned int)(2);
""")

def test_cast2():
    return c_test("""
return (void *)self
""", """
return (void *) self;
""")

def test_forward_decl():
        return c_test("""
static def x:
    y()

static def y:
    x()
""", """
static void x(void);
static void y(void);
static void x(void) {
    y();
}
static void y(void) {
    x();
}
""")

def test_no_forward_decl():
        return c_test("""
static not def x:
    y()

static def y:
    x()
""", """
static void y(void);
static void x(void) {
    y();
}
static void y(void) {
    x();
}
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
static x = "a""b";
""")

def test_postfix():
    return c_test("""
x++
""", """
static x++;
""")

def test_prefix():
    return c_test("""
--x
""", """
static --x;
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
void x(void(* (* cb)())()) {
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
    int* (*x)(int, int);
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

def test_named_union():
    return c_test("""
static union A:
    int x
    union y:
        int y
        float z
""", """
typedef union A A;
union A {
    int x;
    union {
        int y;
        float z;
    } y;
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
static x = (void *) & (int) y;
""")

def test_pointer_params():
    return c_test("""
int **def *x(int *, int **)
""", """
int** (*x)(int * , int * (* ));
""")  

def test_typedef():
    return c_test("""
static typedef A B
""", """
typedef A B;
""")  

def test_cast_prefix():
    return c_test("""
if l < (int)sizeof(var) - 1: l++
""", """
if (l < (int) sizeof (var) - 1) {
    l++;
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

def test_global_var_comment():
    return c_test("""
# blah
int b
""", """
// blah
static int b;
""")

def test_multibyte():
    return c_test("""
if c == L'♥': pass
""", """
if (c == L'♥') {
    ;
}
""")

def test_for_in_access():
    return c_test("""
for MyElem *x in MyArray *arr: x.y = 0
    """, """
{
    MyArrayIterator __iter0__ = MyArrayIterator_first(arr);
    for (MyElem * x = MyArrayIterator_item(arr, &__iter0__); MyArrayIterator_next(arr, &__iter0__); x = MyArrayIterator_item(arr, &__iter0__)) {
        x->y = 0;
    }
}
""")

def test_for_in_dot():
    return c_test(r"""
class A:
    LandArray *b
A *a
for int *c in a.b:
    print(*c)
""", r"""
static A * a;
{
    LandArrayIterator __iter0__ = LandArrayIterator_first(a->b);
    for (int * c = LandArrayIterator_item(a->b, &__iter0__); LandArrayIterator_next(a->b, &__iter0__); c = LandArrayIterator_item(a->b, &__iter0__)) {
        print(* c);
    }
}
""")

def test_class_access():
    return c_test("""
static class B:
    pass
static class A:
    B *b
static class X:
    A *a
X *x
x.a = None
x.a.b = None
x.a.b.hu = None
    """, """
typedef struct B B;
typedef struct A A;
typedef struct X X;
struct B {
    ;
};
struct A {
    B * b;
};
struct X {
    A * a;
};
static X * x;
static x->a = NULL;
static x->a->b = NULL;
static x->a->b->hu = NULL;
    """)

def test_class_access2():
    return c_test("""
class A:
    B *b
class X:
    A *a
X *x
x.a.b.c = None
    """, """
static X * x;
static x->a->b->c = NULL;
    """)

def test_class_access3():
    return c_test("""
class A:
    B *b
class X:
    A *a
def fun(X *x):
    x.a.b.c = None
    """, """
void fun(X * x) {
    x->a->b->c = NULL;
}
    """)

def test_external_class_access():
    return c_test("""
X *x
x.a = None
x.a.b = None
x.a.b.hu = None
    """, """
static X * x;
static x->a = NULL;
static x->a->b = NULL;
static x->a->b->hu = NULL;
    """, external = """
static class B:
    pass
static class A:
    B *b
static class X:
    A *a
""")

def test_local_class():
    return ch_test("""
class A:
    pass

static class B:
    pass
    """, exp_c="""
typedef struct B B;
struct B {
    ;
};
    """, exp_h="""
typedef struct A A;
struct A {
    ;
};
    """)

def test_local_class_underscore():
    return ch_test("""
class A:
    pass

class _B:
    pass
    """, exp_c="""
typedef struct _B _B;
struct _B {
    ;
};
    """, exp_h="""
typedef struct A A;
struct A {
    ;
};
    """)

def test_alternative_return():
    return c_test("""
def fun(int x) -> int:
    pass
""", """
int fun(int x) {
    ;
}
""")

def test_inline():
    return c_test("""
inline def fun(int x) -> int:
    pass
""", """
inline int fun(int x) {
    ;
}
""")

def test_not_error():
    return err_test("""
x = a not = b
""", "test: 2/6: Operator 'not' can't have two operands here.")

def test_type_def():
    return c_test("""
type Game *game
type class Game:
    Game *b

def fun:
    print(game.x)
    print(game.a.x)
    print(game.b.x)
""", """
void fun(void) {
    print(game->x);
    print(game->a.x);
    print(game->b->x);
}
""")

def test_integer_div():
    return c_test("""
x = a // b
""", """
static x = (int)(a / b);
""")

def test_auto():
    return c_test("""
Blah *x
auto y = x
""", """
static Blah * x;
static Blah * y = x;
""")

def test_auto_global():
    return c_test("""
Blah *x
def fun:
    auto y = x
""", """
static Blah * x;
void fun(void) {
    Blah * y = x;
}
""")

def test_auto_param():
    return c_test("""
def fun(Blah *x):
    auto y = x
""", """
void fun(Blah * x) {
    Blah * y = x;
}
""")

def test_array_type():
    return e_test("""
class X:
    Blah *a
    Blah *b[]
    Blah *c[10]
    Blah *d[10][10]
""", """
X
    a : Blah*
    b : Blah*
    c : Blah*
    d : Blah*
""")

def test_const_type():
    return e_test("""
class C:
    char *a
    char const *b
    const char *c
    char const **d
    char const *e[]
""", """
C
    a : char*
    b : char const*
    c : const char*
    d : char const**
    e : char const*
""")

def test_auto_loop():
    return c_test("""
def fun(LandArray *x):
    for X *a in x:
        print(a)
    LandList *y
    for X *a in y:
        print(a)
""", """
void fun(LandArray * x) {
    {
        LandArrayIterator __iter0__ = LandArrayIterator_first(x);
        for (X * a = LandArrayIterator_item(x, &__iter0__); LandArrayIterator_next(x, &__iter0__); a = LandArrayIterator_item(x, &__iter0__)) {
            print(a);
        }
    }
    LandList * y;
    {
        LandListIterator __iter0__ = LandListIterator_first(y);
        for (X * a = LandListIterator_item(y, &__iter0__); LandListIterator_next(y, &__iter0__); a = LandListIterator_item(y, &__iter0__)) {
            print(a);
        }
    }
}
""")

def test_outer_preprocessor():
    return c_test("""
global ***if X > BLAH
***if X > BLAH
def fun:
    bah()
static def bah:
    pass
***endif
global ***endif
""",
"""
#if X > BLAH
static void bah(void);
void fun(void) {
    bah();
}
static void bah(void) {
    ;
}
#endif
""")

def test_outer_preprocessor_h():
    return h_test("""
global ***if X > BLAH
def fun:
    bah()
static def bah:
    pass
global ***endif
""",
"""
#if X > BLAH
void fun(void);
#endif
""")

def test_typedef():
    return c_test("""
def fun(Int i):
    pass
static typedef int Int
""",
"""
typedef int Int;
void fun(Int i) {
    ;
}
""")

def test_import_if():
    return c_test("""
static import test if defined BLAH
""",
"""
#if defined BLAH
#include "test.h"
#endif
""")

def test_len():
    return c_test("""
Array *a
x = len(a)
""",
"""
static Array * a;
static x = Array__len__(a);
""")

def test_len_error():
    return err_test("""
int len = 0
""",
"test: 2/4: len() needs an argument")

def test_len_error2():
    return err_test("""
x = len(0)
""",
"test: 2/4: Cannot use len() on 0")

def test_underscore():
    return c_test("""
def _fun:
    pass
""",
"""
static void _fun(void);
static void _fun(void) {
    ;
}
""")

def test_auto_return():
    return c_test("""
def fun -> X*:
    pass
auto x = fun();
""",
"""
X* fun(void) {
    ;
}
static X * x = fun();
""")

def test_external_auto_return():
    return c_test("""
auto x = fun();
""",
"""
static X * x = fun();
""", external = """
def fun -> X*:
    pass
""")

def test_external_auto_pointer():
    return c_test("""
def ba:
    auto x = fun();
    x.a = 2
""",
"""
void ba(void) {
    X * x = fun();
    x->a = 2;
}
""", external = """
def fun -> X*:
    pass
""")

def test_auto_struct():
    return c_test("""
class A:
    A* x
    B* y
    C* z
def fun:
    A *a
    auto b = a.x
    auto c = a
    auto d = a.y
    auto e = a.z
""",
"""
void fun(void) {
    A * a;
    A * b = a->x;
    A * c = a;
    B * d = a->y;
    C * e = a->z;
}
""")

def test_external_auto_struct():
    return c_test("""
def fun:
    A *a
    auto b = a.x
    auto c = a
    auto d = a.y
    auto e = a.z
""",
"""
void fun(void) {
    A * a;
    A * b = a->x;
    A * c = a;
    B * d = a->y;
    C * e = a->z;
}
""",
external = """
class A:
    A* x
    B* y
    C* z
""")

def test_auto_pointer():
    return c_test("""
class A:
    B* x
class B:
    C* c
def fun:
    A *a
    auto b = a.x
    auto c = b.c
""", """
void fun(void) {
    A * a;
    B * b = a->x;
    C * c = b->c;
}
""")

def test_auto_function_pointer():
    return c_test("""
class A:
    B* x
def fun_a -> A*:
    pass
def fun:
    auto a = fun_a()
    auto b = a.x
""", """
A* fun_a(void) {
    ;
}
void fun(void) {
    A * a = fun_a();
    B * b = a->x;
}
""")

def test_auto_external_function_pointer():
    return c_test("""
class A:
    B* x
def fun:
    auto a = fun_a()
    auto b = a.x
""", """
void fun(void) {
    A * a = fun_a();
    B * b = a->x;
}
""", external = """
def fun_a -> A*:
    pass
""")

def test_auto_pointer2():
    return c_test("""
class A:
    B* x
class B:
    C* c
def fun:
    A *a
    print(a.x.c)
""", """
void fun(void) {
    A * a;
    print(a->x->c);
}
""")

def test_if_expression():
    return c_test("""
def fun:
    int x = 3 + 1 if a == "three" else 0 + 4
""", """
void fun(void) {
    int x = a == "three" ? 3 + 1 : 0 + 4;
}
""")

def test_typeinfo():
    return c_test("""
class A:
    int* x
print(scramble_type(A).field_names[0])
""", """
#define scramble_type(X) __scramble_type_##X
struct {
    char const * field_names[] = {
        "x",
    };
} __scramble_type_A;
print(scramble_type (A).field_names [0]);
""")

def test_auto_struct_pointer():
    return c_test("""
class A:
    B* b
def fun(A *a):
    int x = a.b.x
""", """
void fun(A * a) {
    int x = a->b->x;
}
""", external = """
class B:
    int x
""")

def test_float_constant():
    return c_test("""
def x(): print(2.0e-2)
""", """
void x(void) {
    print(2.0e-2);
}""")

def test_float_constant2():
    # numbers with "e-" are a token but otherwise e- is not
    return c_test("""
def x(): print(e-2)
""", """
void x(void) {
    print(e - 2);
}""")

def test_named_parameter():
        return c_test("""
def x(a): print(a)
def test:
    v=x(a=1)
""", """
void x(a) {
    print(a);
}
void test(void) {
    v = x(1 /* a */);
}
""")

def test_named_parameter2():
        return c_test("""
def x(a, b, c): pass
def test:
    x(a=1)
    x(a=1,b=2,c=3)
    x(a=x(a=2),b=0)
    x(a=x(a=2,b=fun(3)))
""", """
void x(a, b, c) {
    ;
}
void test(void) {
    x(1 /* a */);
    x(1 /* a */, 2 /* b */, 3 /* c */);
    x( /* a */x(2 /* a */), 0 /* b */);
    x( /* a */x(2 /* a */,  /* b */fun(3)));
}

""")

def test_multiret():
    return c_test("""
(a, b) = fun(2, 3, 4)
""", """
static fun(2, 3, 4, & a, & b);
""")

def test_multiret2():
    return c_test("""
(a, b) = fun(1+2, 3, 4 * fun(2))
""", """
static fun(1 + 2, 3, 4 * fun(2), & a, & b);
""")

def test_multiret3():
    return c_test("""
(a, b, c) = fun(x)
""", """
static fun(x, & a, & b, & c);
""")

def test_multiret4():
    return c_test("""
(int a, b, c) = fun(x)
""", """
int a, b, c;
static fun(x, & a, & b, & c);
""")

def test_multiret5():
    return c_test("""
(int a, b) = fun()
""", """
int a, b;
static fun(& a, & b);
""")

def test_multiline_comment():
    return c_test(r"""
    #   /\
    #  /\/\
    # /\/\/\
    # \/\/\/
    #  \/\/
    #   \/
def fun:
    pass
""", r"""
/*
   /\
  /\/\
 /\/\/\
 \/\/\/
  \/\/
   \/
*/
void fun(void) {
    ;
}
""")

def test_oneline_comment():
    return c_test(r"""
    # /
def fun:
    pass
""", r"""
// /
void fun(void) {
    ;
}
""")

def test_null_pointer_operator():
    return c_test(r"""
def fun:
    print(x?.y)
""", r"""
void fun(void) {
    print(x ? x->y : NULL);
}
""")

def main():
    print("Running tests")
    test = sys.argv[1] if len(sys.argv) > 1 else None
    total = 0
    failed = 0
    if test and not test.startswith("test_"):
        test = "test_" + test
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
