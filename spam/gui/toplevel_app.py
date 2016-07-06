"""
This module contains the main, top-level application class for the GUI wrapper
"""
from __future__ import division

import Tkinter as tk
import sys
from spam.gui.spam_globals import ENTRY_SIZE
from spam.gui.spam_menu import SpamMenu
from spam.gui.spam_widgets import (DensityButton, TrajButton, SpamButton)
from spam.main import set_overwrite

class SpamApp(tk.Frame):
   """ The main Spam App """
   def __init__(self, parent=None):
      """ constructor for the main App """
      from spam.gui.spam_windows import TextWindow
      tk.Frame.__init__(self, parent, class_='SpamApp')
      self.pack(fill=tk.BOTH, expand=1)

      # Create a message window where all output from the 'logfile' is dumped
      self.masterlog = TextWindow(self, state=tk.DISABLED, noclose=True)
      self.masterlog.title("Master SPAM Log Messages")

      # We have three options that we want to expose to users. Users can either
      # generate the density file and determine the peak locations, they can
      # generate the re-ordered trajectory file based on where the peaks are,
      # and they can calculate the energies and SPAM statistics.  A separate
      # button will activate a separate window for each
      self.density_button = DensityButton(self, text='Peak Identification')
      self.traj_button = TrajButton(self, text='Trajectory Reordering')
      self.spam_button = SpamButton(self, text='SPAM it!')
      
      # Make all buttons same width as a mask entry
      self.density_button.config(width=ENTRY_SIZE)
      self.traj_button.config(width=ENTRY_SIZE)
      self.spam_button.config(width=ENTRY_SIZE)

      # Generate the menu at the top
      menu = SpamMenu(self)
      parent.config(menu=menu)

      # Pack in the 3 buttons
      self.density_button.grid(column=0, row=0, sticky=tk.N+tk.S+tk.E+tk.W,
                               padx=2, pady=2)
      self.traj_button.grid(column=1, row=0, sticky=tk.N+tk.S+tk.E+tk.W,
                            padx=2, pady=2)
      self.spam_button.grid(column=2, row=0, sticky=tk.N+tk.S+tk.E+tk.W,
                            padx=2, pady=2)
      
      # Make the parent and widget expandable
      parent.rowconfigure(0, weight=1)
      parent.columnconfigure(0, weight=1)
      for col in range(self.grid_size()[0]):
         self.columnconfigure(col, weight=1)
      for row in range(self.grid_size()[1]):
         self.rowconfigure(row, weight=1)
      
      # Grab the focus
      self.focus_set()
      # Bind the <F1> key to the Help function
      self.bind('<F1>', self.Help)

      # Finally make everything overwritable, since the file saveas dialog will
      # ask if we want to overwrite our files
      set_overwrite(True)
      
      # Set stdout and stderr to the message log
      sys.stdout = self.masterlog
      sys.stderr = self.masterlog

      # Update 'idletasks' and then move the windows side by side
      self.master.update_idletasks()
      sidebyside(self.master, self.masterlog)

   def activate_button(self, button):
      """
      This is called when a button is clicked, and will result in the greying-
      out of the other buttons, or un-greying them if the passed button is
      not pressed
      """
      other_buttons = [b for b in (self.density_button, self.traj_button, 
                                   self.spam_button) if b is not button]
      if len(other_buttons) != 2:
         raise InternalError("What button was just pressed?!")

      if button._is_pressed:
         for button in other_buttons: button.turn_off()

      # If all buttons are off, re-grab the focus
      if not True in [b._is_pressed for b in (self.density_button, 
                                       self.traj_button, self.spam_button)]:
         self.focus_set()

   def destroy(self):
      """ We have to specially destroy the log window """
      tk.Frame.destroy(self)

   def annihilate(self):
      """
      Don't just destroy this frame, destroy the root frame, too
      """
      self.master.destroy()

   def Help(self, event):
      """ Wrapper to call the Help method from the F1-binding """
      Help(self)

   def show_messages(self):
      """ Reactivates the message log if a user has closed it """
      self.masterlog.revealme()

def Help(master):
   """ Displays a helpful message """
   from tkMessageBox import showinfo
   help_message = (
      'SPAM calculations require 3 steps.\n\n'

      '   1) Calculate water density and find the density peaks.\n'
      '   2) Trajectory re-ordering\n'
      '   3) Energy calculation and SPAM Free energy calculation\n\n'
      
      'The three primary buttons can be clicked to expand the window\n'
      'with the options pertinent to that portion of the SPAM\n'
      'calculation. Help is available on a command-by-command basis\n'
      'for some commands by pressing the right mouse button'
                  )

   # Count the number of lines and maximum width of the help message
   nlines = len(help_message.split('\n'))
   maxwidth = max([len(l) for l in help_message.split('\n')])

   # Generate a toplevel window to put the help text into
   window = tk.Toplevel(master)
   window.title('Help')
   text = tk.Text(window, width=maxwidth+1, height=nlines)
   text.insert(tk.END, help_message)
   text.config(relief=tk.FLAT)
   text.config(state=tk.DISABLED)
   text.pack()
   window.resizable(False, False)
   window.grab_set()

def Credits(master):
   """ Display the "About" section """
   from spam.__init__ import __version__
   from sys import argv
   from os import path
   CRW = 450 # credits window width
   CRH = 350 # credits window height

   header_text = (
      "SPAM.py is a wrapper that uses cpptraj to calculate and identify\n"
      "water density peaks, NAMD to calculate the energies of individual\n"
      "water molecules, and SciPy to analyze the data and calculate SPAM\n"
      "Free Energies to identify water hotspots."
                 )
   tailer_text = (
      "SPAM.Pie Version %s\n\n" % __version__ +
      "Cpptraj modifications and SPAM.Pie\n"
      "by Jason Swails and Guanglei Cui\n"
      "GlaxoSmithKline, Copyright 2012"
                 )
   credits = tk.Toplevel(master)
   credits.resizable(False, False)
   credits.title('About SPAM.Pie')
   # Get the file name
   fname = path.join(path.abspath(path.split(__file__)[0]), 'spam.gif')
   canv = tk.Canvas(credits, width=CRW, height=CRH)
   canv.pack()
   image = tk.PhotoImage(name='SPAM', master=canv, file=fname)
   canv.create_image(CRW//2, CRH//2, anchor=tk.CENTER, image=image)
   canv.create_text(CRW//2, 10, anchor=tk.N, text=header_text,
                    justify=tk.CENTER)
   canv.create_text(CRW//2, CRH-10, anchor=tk.S, text=tailer_text,
                    justify=tk.CENTER)
   credits.grab_set()
   credits.mainloop()

def sidebyside(w1, w2, buffer=20):
   """ This adjusts the geometry of w2 so it is to the right of w1 """
   import re
   import warnings
   # regex to extract the geometry
   geore = re.compile(r'(\d+)x(\d+)([\+-]\d+)([\+-]\d+)')

   # First, get the geometry of w1
   rematch = geore.match(w1.winfo_geometry())
   if not rematch:
      # We tried...
      warnings.warn('Could not determine geometry of parent window!')
      return

   w1_width, w1_height, w1_offsetx, w1_offsety = rematch.groups()

   # Now get w2's geometry
   rematch = geore.match(w2.winfo_geometry())
   if not rematch:
      # We tried...
      warnings.warn('Could not determine geometry of slave window!')
      return

   w2_width, w2_height, w2_offsetx, w2_offsety = rematch.groups()

   # If the original x offset is - (i.e., closer to RHS of screen), put w2
   # on the left. Otherwise, put it on the right
   if w1_offsetx[0] is '-':
      w2_offsetx = '-%d' % (int(w1_offsetx) - int(w1_width) - 20)
      w2.geometry('%sx%s%s%s' % (w2_width, w2_height, w2_offsetx, w2_offsety))
   else:
      w2_offsetx = '+%d' % (int(w1_offsetx) + int(w1_width) + 20)
      w2.geometry('%sx%s%s%s' % (w2_width, w2_height, w2_offsetx, w2_offsety))
