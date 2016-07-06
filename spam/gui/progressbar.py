"""
This module provides a progress bar for showing the user the progress of the
current step of the calculation
"""
from __future__ import division

from spam.exceptions import InternalError
from Tkinter import *

class ProgressBar(Toplevel):
   """ A progress bar window for SPAM calcs """
   WIDTH = 420 
   HEIGHT = 40
   LW = 6 # width of the line
   def __init__(self, master, title, end_count=None):
      """ Constructor for ProgressBar """
      Toplevel.__init__(self, master)
      self.resizable(False, False)
      # Disable deleting
      self.protocol('WM_DELETE_WINDOW', lambda: 0)
      self.title(title)
      self.canv = Canvas(self, width=self.WIDTH, height=self.HEIGHT)
      self.count = 0
      # Pack the canvas
      self.canv.pack()
      if end_count is not None:
         self.initialize(end_count)
      else:
         self.withdraw()

   def initialize(self, end_count):
      """ Sets up a progress bar """
      self.end_count = end_count
      self.box = self.canv.create_rectangle(0, 0, self.WIDTH, self.HEIGHT,
                     width=self.LW)
      self.progress = self.canv.create_rectangle(self.LW, self.LW, 
                     self.LW, self.HEIGHT-self.LW, fill='green4', width=0)
      self.text = self.canv.create_text(self.WIDTH//2, self.HEIGHT//2, 
                     text='0 %')
      self.update_idletasks()
      self.deiconify()
      self.placeme()

   def placeme(self):
      """ This places the progress bar over the center of the master widget """
      import re
      geore = re.compile(r'(\d+)x(\d+)([+-]\d+)([+-]\d+)')

      self.master.update_idletasks()
      rematch = geore.match(self.master.winfo_geometry())
      i, j, masterxoff, masteryoff = rematch.groups()

      rematch = geore.match(self.geometry())
      myx, myy, i, j = rematch.groups()

      self.geometry('%sx%s%s%s' % (myx, myy, masterxoff, masteryoff))
      self.master.update_idletasks()

   def update(self):
      """ If we update our progress bar """
      self.count += 1
      self.print_method()

   def print_method(self):
      """ Here we update the progress bar """
      from time import sleep
      if not hasattr(self, 'end_count'):
         raise InternalError('Progress bar not initialized!')
      self.update_idletasks() # Let this flush to the screen
      self.canv.delete(self.progress)
      self.canv.delete(self.text)

      width, height = self.WIDTH - self.LW, self.HEIGHT - self.LW
      frac_done = self.count / self.end_count
      self.progress = self.canv.create_rectangle(self.LW, self.LW, 
                        frac_done*width, height, fill='green4', width=0)
      self.text = self.canv.create_text(self.WIDTH//2, self.HEIGHT//2,
                        text = '%.1f %%' % (frac_done * 100))
      self.update_idletasks() # Let this flush to the screen

   def reset(self):
      """ Resets the progress bar """
      self.count = 0
      del self.end_count
      self.canv.delete(self.progress)
      self.canv.delete(self.text)
      self.withdraw()
