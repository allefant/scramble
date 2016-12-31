# Scramble

## About

Scramble is a C preprocessor which allows to write C code which looks a bit like Python code with a full Python3 environment available for meta programming. That is, no semantics at all are changed - when using Scramble you still write C code. But it has a syntax more similar to Python.

Similar (and better) projects:

*   [pyrex](http://www.cosc.canterbury.ac.nz/~greg/python/Pyrex/)
*   [shedskin](http://shed-skin.blogspot.com)
*   [pypy](http://pypy.org/)
*   [pyplus](http://www.imitationpickles.org/pyplus/)

## Example

Scramble is used like this:

<tt>scramble.py -i input.py -c output.c -h output.h -n name</tt>

For example, if you have a file main.py, then you could run:

<tt>scramble.py -i src/main.py -c build/c/main.c -h build/h/main.h -n main</tt>

And if your src/main.c would look like to the left, the resulting files would look like to the right:

<table>

<tbody>

<tr>

<td>

src/main.py

<pre>import stdio, string, math

def main(int argc, char **argv) -> int:
    if argc == 2:
        printf("%f\n", sin(strtod(argv[1]))
        return 0
    else:
        fprintf(stderr, "Need exactly one argument!\n")
        return 1
</pre>

</td>

<td>

build/c/main.c

<pre>#include "main.h"

int main(int argc, char **argv)
{
    if (argc == 2) {
        printf("%f\n", sin(strtod(argv[1]));
        return 0;
    }
    else {
        fprintf(stderr, "Need exactly one argument!\n");
        return 1;
    }
}
</pre>

build/h/main.h

<pre>#ifndef _MAIN_

#include "stdio.h"
#include "string.h"
#include "math.h"

extern int main(int argc, char **argv);

#endif
</pre>

</td>

</tr>

</tbody>

</table>

## Keywords

All C, C++ and Python keywords basically are also Scramble keywords. The following control flow constructs are used by scramble: **while**, **switch...case**, **do...while**, **for** X **while** Y **with** Z [for (X; Y; Z) in C], **for...in**, **if...elif...else**, **label** [: in C], **goto**.

And these declarations: **class** [struct in C], **def**, **enum**, **global**, **import**, **macro** [#define in C], **static**, **struct**, **typedef**, **union**.

These Python operators are used instead of the C++ ones: **and** [&& in C], **max**, **min**, **not** [! in C], **or** [|| in C].

And there's a few new constants: **True**, **False**, **None**.

## Features

In general, here is what scramble will do:

*   No more **;** required.
*   **:** and indentation instead of **{** and **}**.
*   No **(** and **)** for builtin C keywords like **if**. For example:

    <table>

    <tbody>

    <tr>

    <td>

    <pre>if x == 2:
        x = 3
        y = 3
    </pre>

    </td>

    <td>translates to</td>

    <td>

    <pre>if (x == 2) {
        x = 3;
        y = 2;
    }
    </pre>

    </td>

    </tr>

    </tbody>

    </table>

*   Use **elif** instead of **else if**, like in python.
*   Use **and**, **or** and **not** inside conditionals, like in python.
*   Functions are declared with **def**, and parameter types can be grouped. For example:

    <table>

    <tbody>

    <tr>

    <td>

    <pre>def f1():
        pass

    def f2(int x, y, z):
        pass

    def f3 -> int:
        pass
    </pre>

    </td>

    <td>translates to</td>

    <td>

    <pre>void f1(void) {
    }

    void f2(int x, int y, int z) {
    }

    int f3(void) {
    }
    </pre>

    </td>

    </tr>

    </tbody>

    </table>

*   Headers are generated automatically. This works by outputting a declaration for each function or global variable which is not declared static. Similarly, struct/union/enum declarations are written into the header unless declared static, and a type is automatically defined for them. For example:

    <table>

    <tbody>

    <tr>

    <td>

    test.py

    <pre>class A:
        int x

    class B:
        A *a

    static class C:
        B *b

    static A *def a_new():
        A *self = calloc(1, sizeof *self)
        return self

    def b_new() -> B*:
        B *self = calloc(1, sizeof *self)
        self->a = a_new()
        return self
    </pre>

    </td>

    <td>translates to</td>

    <td>

    test.c

    <pre>#include "test.h"

    typedef struct C C;

    struct C
    {
        B *b;
    };

    static A *a_new(void)
    {
        A *self = calloc(1, sizeof *self);
        return self;
    }

    B *b_new(void)
    {
        B *self = calloc(1, sizeof *self);
        self->a = a_new();
        return self;
    }
    </pre>

    and

    test.h

    <pre>#ifndef _TEST_

    typedef struct A A;
    typedef struct B B;

    struct A
    {
        int x;
    };

    struct B
    {
        A *a;
    };

    B *a_new(void);

    #endif
    </pre>

    </td>

    </tr>

    </tbody>

    </table>

*   Comments are started with **#**.
*   Include files are included with **import**. For example:

    <table>

    <tbody>

    <tr>

    <td>

    <pre>import test, global stdio
    </pre>

    </td>

    <td>translates to</td>

    <td>

    <pre>#include "test.h"
    #include <stdio.h>
    </pre>

    </td>

    </tr>

    </tbody>

    </table>

*   **Meta programming** using full Python. This is possibly the single most useful feature - at compile time you have the full Python interpreter at your disposal to create any code you want.

    <table>

    <tbody>

    <tr>

    <td>

    <pre>***scramble
    for x in ["A", "B", "C"]:
        parse("char def function" + x + "(): return '" + x + "'")
    ***
    </pre>

    </td>

    <td>translates to</td>

    <td>

    <pre>char functionA(void) {
        return 'A';
    }

    char functionB(void) {
        return 'B';
    }

    char functionC(void) {
        return 'C';
    }
    </pre>

    </td>

    </tr>

    </tbody>

    </table>

*   Triple quoted strings, useful for multi-line string constants.
*   Support for *auto* declarations (type is inferred)
*   Extended for-loop syntax, for example:

    <table>

    <tbody>

    <tr>

    <td>

    <pre>for MyElem *x in arr:
        handle(x)
    </pre>

    </td>

    <td>translates to</td>

    <td>

    <pre>MyArrayIterator __iter__ = MyArrayIterator_first(arr);
    for (MyElem *x = MyArrayIterator_item(arr, &__iter__);
            MyArrayIterator_next(arr, &__iter__);
            x = MyArrayIterator_item(arr, &__iter__)) {
        handle(x);
    }
    </pre>

    </td>

    </tr>

    </tbody>

    </table>

*   **Docstrings** can be used to automatically generate documentation. Strings at the beginning of a function are ignored, but can optionally be outputted to a separate file, associated with the function they are defined in. This can then be used to translate into different documentation formats.

## More stuff (might change?)

*   **None**, **min**, **max**, **True**, **False** keywords. For now min and max are macros for the ternary operator - with the usual problem of evaluating the argument twice.
*   As the hash sign starts a comment, ******* can be used to insert C preprocessor commands.
*   Instead of #define, **macro** and **static macro** can be used to place a #define either into the .h or .c file.
*   Since the : is used up by Python syntax, labels are marked with the **label** keyword instead of :. Bitfields use the keyword **with**. The colon in the C tertiary operator works for now until I implemnt the if-else construct.

[![Valid XHTML 1.0 Strict](http://www.w3.org/Icons/valid-xhtml10)](http://validator.w3.org/check?uri=referer)
