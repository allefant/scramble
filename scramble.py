#!/usr/bin/env python

import optparse, os
from parser import *
from sout import *
from cout import *

def main():
    op = optparse.OptionParser(add_help_option = False)
    o = op.add_option
    o("-?", "--help", action = "help"),
    o("-i", "--input", help = "input file")
    o("-c", "--cfile", help = "c output file")
    o("-h", "--hfile", help = "h output file")
    o("-n", "--name", help = "module name")
    o("-p", "--prefix", help = "header guard prefix", default = "")
    o("-N", "--no-lines", action = "store_true",
        help = "don't generate #line directives")
    o("-s", "--sfile", help = "scramble output file")
    options, args = op.parse_args()

    p = None
    if options.input:
        text = open(options.input, "r").read()
        p = Parser(options.input, text)
        try:
            p.parse()
        except MyError as e:
            print(e)
            exit(1)

        if not options.name:
            options.name = os.path.splitext(options.input)[0]
    else:
        print("No input file given with -i.")
        exit(1)

    if p and options.sfile:
        s = SWriter()
        code = s.generate(p)
        f = open(options.sfile, "w")
        f.write(code)

    if p and (options.cfile or options.hfile):
        c = CWriter()
        try:
            code, header = c.generate(p, options.name, options.no_lines,
                options.prefix)
        except MyError as e:
            print(e)
            exit(1)
        if options.cfile:
            f = open(options.cfile, "w")
            f.write(code)
        if options.hfile:
            f = open(options.hfile, "w")
            f.write(header)

if __name__ == "__main__":
    main()
