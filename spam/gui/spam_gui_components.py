"""
This module contains all of the widgets that are used by other, higher-level
widgets.
"""
from __future__ import division
from Tkinter import *
from spam.exceptions import InternalError, SpamTypeError

class HelpedWidget(Frame):
   """ This class simply binds the 'help' function """
   def __init__(self, master, help):
      """ Constructor, binds right-click to help window """
      Frame.__init__(self, master)
      self.help = help

   def helpme(self):
      """ Displays the help """
      from tkMessageBox import showinfo
      showinfo(self.help, parent=self)

class MaskEntry(HelpedWidget):
   """ This allows users to inspect their masks before committing to them """
   def __init__(self, master, title, variable, help):
      """ Put a label on top of an entry and the title on bottom """
      from spam.gui.spam_globals import ENTRY_SIZE
      HelpedWidget.__init__(self, master, help)
      self.mask = variable
      self.title = title
      label = Label(self, text=self.title)
      label.pack(fill=X, expand=1)
      entry = Entry(self, textvariable=self.mask, width=ENTRY_SIZE)
      entry.pack(fill=X, expand=1)
      self.button = Button(self, text='Evaluate Mask', command=self.eval_mask)
      self.button.pack(fill=X, expand=1)
      self.bind("<Button-3>", self.helpme)
      self.focus_set()

   def eval_mask(self):
      """ Evaluate the mask """
      from spam.gui.spam_globals import global_spam_files
      from spam.gui.spam_windows import TextWindow
      from spam import AmberParm
      from spam import AmberMask
      # Our prmtop needs to be loaded
      if not hasattr(self.master, 'parm') or (str(self.master.parm) !=  
                                              global_spam_files['prmtop']):
         self.master.parm = AmberParm(global_spam_files['prmtop'])

      parm = self.master.parm
      if not parm.valid:
         raise SpamTypeError('%s is not a valid Amber topology!' % parm)
      
      # Now grab our mask
      mask = AmberMask(parm, self.mask.get())
      selection = mask.Selection()
      ret_str = '\nThe mask %s matches %d atoms:\n\n' % (mask, sum(selection))
      ret_str += "%7s%7s%9s%6s%6s\n" % ('ATOM','RES','RESNAME','NAME','TYPE')
      for i, sel in enumerate(selection):
         if not sel: continue
         ret_str += '%7d%7d%9s%6s%6s\n' % (i+1, parm.residue_container[i],
                   parm.parm_data['RESIDUE_LABEL'][parm.residue_container[i]-1],
                   parm.parm_data['ATOM_NAME'][i], 
                   parm.parm_data['AMBER_ATOM_TYPE'][i])
      if hasattr(self, 'text'):
         self.text.destroy()
         del self.text
      self.text = TextWindow(self.master, state=DISABLED)
      self.text.title(self.title)
      self.text.write(ret_str)

class NumEntry(HelpedWidget):
   """ This is a field to input a number """
   def __init__(self, master, title, variable, help):
      """ Create a labeled field of entry for a number """
      from spam.gui.spam_globals import ENTRY_SIZE
      HelpedWidget.__init__(self, master, help)
      entry = Entry(self, width=ENTRY_SIZE, textvariable=variable)
      entry.pack(fill=X, expand=1)
      label = Label(self, text=title)
      label.pack(fill=X, expand=1)
      self.bind("<Button-3>", self.helpme)
      self.focus_set()

class StrEntry(NumEntry):
   """ This is really just the same as NumEntry """

class SiteShapeRadio(HelpedWidget):
   """ Radio buttons to select the site shape """
   def __init__(self, master, title, variable, help):
      """ Instantiates this object (it is fairly specific) """
      HelpedWidget.__init__(self, master, help)
      radioframe = Frame(self)
      radio1 = Radiobutton(radioframe, text='Box', 
                           variable=variable, value='box')
      radio1.select()
      radio2 = Radiobutton(radioframe, text='Sphere', 
                           variable=variable, value='sphere')
      radio1.grid(column=0, row=0, sticky=N+E+S+W, padx=20)
      radio2.grid(column=1, row=0, sticky=N+E+S+W)
      radioframe.rowconfigure(0, weight=1)
      radioframe.columnconfigure(0, weight=1)
      radioframe.columnconfigure(1, weight=1)
      radioframe.pack(fill=BOTH, expand=1)
      label = Label(self, text=title)
      label.pack(fill=BOTH, expand=1)
      self.bind("<Button-3>", self.helpme)
      self.focus_set()

class ButtonEntry(Button, HelpedWidget):
   """ If the command is one to just 'activate' """
   def __init__(self, master, title, variable, help):
      Button.__init__(self, master, text=title)
      self.help = help
      self.bind("<Button-3>", self.helpme)
      self.master.ncallbacks += 1
      self.config(command=getattr(self.master, 'callback_%d' % 
                                  self.master.ncallbacks)
                 )
      self.bind("<Button-3>", self.helpme)
      self.focus_set()
