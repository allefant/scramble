#!/usr/bin/env python3
import argparse, os, sys
from parser import *
from sout import *
from cout import *
from ctypesout import *
import join

def main():
    op = argparse.ArgumentParser(add_help = False)
    o = op.add_argument
    o("-?", "--help", action = "help"),
    o("-i", "--input", help = "input file")
    o("-c", "--cfile", help = "c output file")
    o("-C", "--comments", help = "keep comments", action = "store_true")
    o("-h", "--hfile", help = "h output file")
    o("-n", "--name", help = "module name")
    o("-p", "--prefix", help = "header guard prefix", default = "")
    o("-N", "--no-lines", action = "store_true",
        help = "don't generate #line directives")
    o("-s", "--sfile", help = "intermediate code output file")
    o("--noc99", action = "store_true", help = "do not use C99")
    o("-j", "--join", nargs = "+", help = "files to join")
    o("-o", "--output", help = "source code output file")
    o("-t", "--ctypes", help = "ctypes output file")
    options = op.parse_args()

    p = None
    
    if options.join:
        if options.output:
            f = open(options.output, "wb")
        else:
            f = sys.stdout
        join.join(options.join, f)
    elif options.input:
        text = open(options.input, "rb").read().decode("utf8")

        p = Parser(options.input, text, comments = options.comments)
        try:
            p.parse()
        except MyError as e:
            print(e)
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

    if p and (options.cfile or options.hfile):
        c = CWriter()
        try:
            code, header = c.generate(p, options.name, options.no_lines,
                options.prefix, not options.noc99)
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

if __name__ == "__main__":
    main()
