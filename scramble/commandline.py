#!/usr/bin/env python3
import argparse, os, sys
from .parser import *
from .sout import *
from .cout import *
from .eout import EWriter
from . import dout
from .ctypesout import *
from . import analyzer
from . import join
from . import terminal
from . import module
from . import scanner

def main():
    op = argparse.ArgumentParser(add_help = False)
    o = op.add_argument
    o("-?", "--help", action = "help"),
    o("-m", "--module", action = "append", help = "module folder")
    o("-i", "--input", help = "input file")
    o("-c", "--cfile", help = "c output file")
    o("-C", "--comments", help = "keep comments", action = "store_true")
    o("-h", "--hfile", help = "h output file")
    o("-n", "--name", help = "module name")
    o("-p", "--prefix", help = "header guard prefix", default = "")
    o("-N", "--no-lines", action = "store_true",
        help = "don't generate #line directives")
    o("-s", "--sfile", help = "intermediate code output file")
    o("-e", "--efile", help = "extra output file")
    o("-j", "--join", nargs = "+", help = "files to join")
    o("-o", "--output", help = "source code output file")
    o("-S", "--scan", help = "scan for (direct) dependencies, other output is ignored")
    o("-t", "--ctypes", help = "ctypes output file")
    o("-T", "--terminal", action = "store_true")
    o("-d", "--dfile", help = "output api docs")
    o("-DT", "--debug-tokens")
    options = op.parse_args()

    p = None

    if options.terminal:
        terminal.run()
        exit(0)

    if options.scan:
        scanner.scan(options.scan)
        exit(0)

    if options.join:
        if options.output:
            f = open(options.output, "wb")
        else:
            f = sys.stdout
        join.join(options.join, f)
    elif options.input:
        text = open(options.input, "rb").read().decode("utf8")

        p = Parser(options.input, text, comments = options.comments,
            options = options)

        if options.module:
            module.parse_all(p, options.module)
        
        try:
            p.parse()
        except MyError as e:
            print(e.value.encode("ascii", errors = "replace").decode("ascii"))
            exit(1)

        if not options.name:
            options.name = os.path.splitext(options.input)[0]
    else:
        print("No input file given with -i.")
        op.print_help()
        exit(1)

    if p and options.sfile:
        s = SWriter()
        code = s.generate(p)
        f = open(options.sfile, "wb")
        f.write(code.encode("utf8"))

    if p and options.efile:
        e = EWriter()
        code = e.generate(p)
        f = open(options.efile, "wb")
        f.write(code.encode("utf8"))

    if p and options.dfile:
        d = dout.DWriter()
        code = d.generate(p, options.name)
        f = open(options.dfile, "wb")
        f.write(code.encode("utf8"))

    if p and (options.cfile or options.hfile):
        c = CWriter()
        try:
            code, header = c.generate(p, options.name, options.no_lines,
                options.prefix)
        except MyError as e:
            print(e)
            exit(1)
        if options.cfile:
            f = open(options.cfile, "wb")
            f.write(code.encode("utf8"))
        if options.hfile:
            f = open(options.hfile, "wb")
            f.write(header.encode("utf8"))

    if p and options.ctypes:
        w = CTypesWriter()
        code = w.generate(p)
        f = open(options.ctypes, "wb")
        f.write(code.encode("utf8"))
