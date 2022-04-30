#!/usr/bin/env python -W ignore::FutureWarning -W ignore::UserWarning -W ignore:DeprecationWarning
"""Tkinter interactive interface for PINT pulsar timing tool"""
import sys
import argparse

import numpy as np

import tkinter as tk
import tkinter.filedialog as tkFileDialog
import tkinter.messagebox as tkMessageBox
from tkinter import ttk

import pint.logging
from loguru import logger as log

log.remove()
log.add(
    sys.stderr,
    level="WARNING",
    colorize=True,
    format=pint.logging.format,
    filter=pint.logging.LogFilter(),
)

import pint
from pint.pintk.paredit import ParWidget
from pint.pintk.plk import PlkWidget, helpstring
from pint.pintk.pulsar import Pulsar
from pint.pintk.timedit import TimWidget


__all__ = ["main"]


class PINTk:
    """Main PINTk window."""

    def __init__(
        self,
        master,
        parfile=None,
        timfile=None,
        fitter="auto",
        ephem=None,
        loglevel=None,
        **kwargs,
    ):
        self.master = master
        self.master.title("Tkinter interface to PINT")

        self.mainFrame = tk.Frame(master=self.master)
        self.mainFrame.grid(row=0, column=0, sticky="nesw")
        self.master.grid_rowconfigure(0, weight=1)
        self.master.grid_columnconfigure(0, weight=1)
        self.loglevel = loglevel
        self.maxcols = 2

        self.createWidgets()
        if parfile is not None and timfile is not None:
            self.openPulsar(
                parfile=parfile, timfile=timfile, fitter=fitter, ephem=ephem
            )

        self.initUI()
        self.updateLayout()

    def initUI(self):
        # Create top level menus
        top = self.mainFrame.winfo_toplevel()
        self.menuBar = tk.Menu(top)
        top["menu"] = self.menuBar

        self.fileMenu = tk.Menu(self.menuBar)
        self.fileMenu.add_command(label="Open par/tim", command=self.openParTim)
        self.fileMenu.add_command(label="Switch model", command=self.switchModel)
        self.fileMenu.add_command(label="Switch TOAs", command=self.switchTOAs)
        self.fileMenu.add_command(label="Exit", command=top.destroy)
        self.menuBar.add_cascade(label="File", menu=self.fileMenu)

        self.viewMenu = tk.Menu(self.menuBar)
        self.viewMenu.add_checkbutton(
            label="Plk (C-p)", command=self.updateLayout, variable=self.active["plk"]
        )
        self.viewMenu.add_checkbutton(
            label="Model Editor (C-m)",
            command=self.updateLayout,
            variable=self.active["par"],
        )
        self.viewMenu.add_checkbutton(
            label="TOAs Editor (C-t)",
            command=self.updateLayout,
            variable=self.active["tim"],
        )
        self.menuBar.add_cascade(label="View", menu=self.viewMenu)

        self.helpMenu = tk.Menu(self.menuBar)
        self.helpMenu.add_command(label="About", command=self.about)
        self.helpMenu.add_command(label="Plk Help", command=lambda: print(helpstring))
        self.menuBar.add_cascade(label="Help", menu=self.helpMenu)

        # Key bindings
        top.bind("<Control-p>", lambda e: self.toggle("plk"))
        top.bind("<Control-m>", lambda e: self.toggle("par"))
        top.bind("<Control-t>", lambda e: self.toggle("tim"))
        top.bind("<Control-o>", lambda e: self.openParTim)

    def createWidgets(self):
        self.widgets = {
            "plk": PlkWidget(master=self.mainFrame, loglevel=self.loglevel),
            "par": ParWidget(master=self.mainFrame),
            "tim": TimWidget(master=self.mainFrame),
        }
        self.active = {"plk": tk.IntVar(), "par": tk.IntVar(), "tim": tk.IntVar()}
        self.active["plk"].set(1)

    def updateLayout(self):
        for widget in self.mainFrame.winfo_children():
            widget.grid_forget()

        visible = 0
        for key in self.active.keys():
            if self.active[key].get():
                row = int(visible / self.maxcols)
                col = visible % self.maxcols
                self.widgets[key].grid(row=row, column=col, sticky="nesw")
                self.mainFrame.grid_rowconfigure(row, weight=1)
                self.mainFrame.grid_columnconfigure(col, weight=1)
                visible += 1

    def openPulsar(self, parfile, timfile, fitter="auto", ephem=None):
        self.psr = Pulsar(parfile, timfile, ephem, fitter=fitter)
        self.widgets["plk"].setPulsar(
            self.psr,
            updates=[self.widgets["par"].set_model, self.widgets["tim"].set_toas],
        )
        self.widgets["par"].setPulsar(self.psr, updates=[self.widgets["plk"].update])
        self.widgets["tim"].setPulsar(self.psr, updates=[self.widgets["plk"].update])

    def switchModel(self):
        parfile = tkFileDialog.askopenfilename(title="Open par file")
        self.psr.parfile = parfile
        self.psr.reset_model()
        self.widgets["plk"].update()
        self.widgets["par"].set_model()

    def switchTOAs(self):
        timfile = tkFileDialog.askopenfilename()
        self.psr.timfile = timfile
        self.psr.reset_TOAs()
        self.widgets["plk"].update()
        self.widgets["tim"].set_toas()

    def openParTim(self):
        parfile = tkFileDialog.askopenfilename(title="Open par file")
        timfile = tkFileDialog.askopenfilename(title="Open tim file")
        self.openPulsar(parfile, timfile)

    def toggle(self, key):
        self.active[key].set((self.active[key].get() + 1) % 2)
        self.updateLayout()

    def about(self):
        tkMessageBox.showinfo(
            title="About PINTk",
            message=f"A Tkinter based graphical interface to PINT (version={pint.__version__})",
        )


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Tkinter interface for PINT pulsar timing tool"
    )
    parser.add_argument("parfile", help="parfile to use")
    parser.add_argument("timfile", help="timfile to use")
    parser.add_argument("--ephem", help="Ephemeris to use", default=None)
    parser.add_argument(
        "--test",
        help="Build UI and exit. Just for unit testing.",
        default=False,
        action="store_true",
    )
    parser.add_argument(
        "-f",
        "--fitter",
        type=str,
        choices=(
            "auto",
            "downhill",
            "WLSFitter",
            "GLSFitter",
            "WidebandTOAFitter",
            "PowellFitter",
            "DownhillWLSFitter",
            "DownhillGLSFitter",
            "WidebandDownhillFitter",
            "WidebandLMFitter",
        ),
        default="auto",
        help="PINT Fitter to use [default='auto'].  'auto' will choose WLS/GLS/WidebandTOA depending on TOA/model properties.  'downhill' will do the same for Downhill versions.",
    )
    parser.add_argument(
        "-v",
        "--version",
        default=False,
        action="store_true",
        help="Print version info and  exit.",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=("TRACE", "DEBUG", "INFO", "WARNING", "ERROR"),
        default="WARNING",
        help="Logging level",
        dest="loglevel",
    )
    args = parser.parse_args(argv)

    if args.version:
        print(f"This is PINT version {pint.__version__}")
        sys.exit(0)

    if args.loglevel != "WARNING":
        log.remove()
        log.add(
            sys.stderr,
            level=args.loglevel,
            colorize=True,
            format=pint.logging.format,
            filter=pint.logging.LogFilter(),
        )

    root = tk.Tk()
    root.minsize(1000, 800)
    if not args.test:
        app = PINTk(
            root,
            parfile=args.parfile,
            timfile=args.timfile,
            fitter=args.fitter,
            ephem=args.ephem,
            loglevel=args.loglevel,
        )
        root.protocol("WM_DELETE_WINDOW", root.destroy)
        tk.mainloop()


if __name__ == "__main__":
    main()
