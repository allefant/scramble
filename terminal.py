import curses
from curses.textpad import Textbox, rectangle
import traceback
import parser
import cout
import sout

def restore():
    curses.nocbreak()
    screen.keypad(False)
    curses.echo()
    curses.endwin()

def run():
    try:
        global screen
        screen = curses.initscr()
        curses.noecho()
        curses.cbreak()
        screen.keypad(True)
        prog()
    except Exception as e:
        restore()
        traceback.print_exc()
    finally:
        restore()

def prog():
    h, w = screen.getmaxyx()

    screen.addstr(0, 0, "Scramble Interactive Shell (Ctrl-G to compile, Ctrl-C to quit)")
    editwin = curses.newwin(8, w, h - 8, 0)
    bwin = screen.subwin(h - 11, w - 2, 2, 1)
    bwin.border()
    bwin.refresh()
    outwin = bwin.subwin(h - 13, w - 4, 3, 2)
    screen.refresh()

    box = Textbox(editwin)

    while True:
        # Let the user edit until Ctrl-G is struck.
        box.edit()

        # Get resulting contents
        message = box.gather()

        p = parser.Parser("inline", message, comments = True)
        try:
            p.parse()
            s = sout.SWriter()
            scode = s.generate(p)
            c = cout.CWriter()
            code, header = c.generate(p, "inline", 1, "_INLINE")
        except parser.MyError as e:
            header = e.value
            code = ""

        outwin.clear()
        div = "\n" + "-" * (w - 4) + "\n\n"
        outwin.addstr(0, 0, scode + div + header + div + code)
        outwin.refresh()
