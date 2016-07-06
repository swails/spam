"""
This module contains the other windows that are used throughout the duration of
the SPAM GUI operation
"""
from __future__ import division
from Tkinter import *

class TextWindow(Toplevel):
   """ A basic, scrollable text window that can either be editable or not """
   def __init__(self, master, state=DISABLED, noclose=False, safe_close=False):
      """ Make a scrollable, resizeable text """
      Toplevel.__init__(self, master)
      # Allow disabling of window killing
      if noclose:
         self.protocol('WM_DELETE_WINDOW', self.hideme)
      # See if we want to prompt saving before closing the window
      self.safe_close = safe_close
      # Store our original state so we can restore it after a write()
      self.original_state = state
      # Add a horizontal and vertical scroller
      self.hscroller = Scrollbar(self, orient=HORIZONTAL)
      self.vscroller = Scrollbar(self, orient=VERTICAL)
      # Make the text box
      self.text = Text(self, width=90, state=state, height=30, wrap=NONE,
                       xscrollcommand=self.hscroller.set,
                       yscrollcommand=self.vscroller.set)
      # Pack everything in there, nice and tight. Let the text expand and the
      # scroll bars lengthen, but do not let the scroll bars thicken.
      self.text.grid(column=0, row=0, sticky=N+S+E+W)
      self.hscroller.grid(column=0, row=1, sticky=N+S+E+W)
      self.vscroller.grid(column=1, row=0, sticky=N+S+E+W)
      self.columnconfigure(0, weight=1)
      self.columnconfigure(1, weight=0)
      self.rowconfigure(0, weight=1)
      self.rowconfigure(1, weight=0)
      # Now make the scroll bars actually work
      self.hscroller.configure(command=self.text.xview)
      self.vscroller.configure(command=self.text.yview)

      # Add a 'file' Menu
      filemenu = Menu(self, tearoff=0)
      filemenu.add_command(label='Save', activeforeground='white',
                           activebackground='blue', command=self.savetext,
                           accelerator='<Ctrl-s>')
      filemenu.add_command(label='Save As', activeforeground='white',
                           activebackground='blue', command=self.saveastext,
                           accelerator='<Ctrl-S>')
      filemenu.add_command(label='Clear Text', activeforeground='white',
                           activebackground='blue', command=self.clear,
                           accelerator='<Ctrl-l>')
      filemenu.add_separator()
      if noclose:
         filemenu.add_command(label='Hide Window',  activeforeground='white',
                              activebackground='blue', command=self.hideme)
      else:
         filemenu.add_command(label='Close Window',  activeforeground='white',
                              activebackground='blue', command=self.destroy)
      # Add a menu bar
      menubar = Menu(self, tearoff=0)
      menubar.add_cascade(label='File', underline=0, menu=filemenu)
      self.configure(menu=menubar)

      # Track whether we are hidden or not
      self.hidden = False

      # This is updated as we need to to make sure we know when to ask if we
      # want to save appropriately.  This will only work for a DISABLE'd
      # original state, otherwise we will have to check.
      self.up_to_date = True

      # Bind ctrl-S to the save function
      self.focus_set()
      self.bind("<Control-KeyPress-s>", self.savetext)
      self.bind("<Control-KeyPress-S>", self.saveastext)
      self.bind("<Control-KeyPress-l>", self.clear)

   def write(self, s):
      """ 
      Writes 's' to the window, such that it will emulate a file.  We have to
      change the state to ACTIVE in order to add text, but then change it back
      to the original state afterwards
      """
      self.text.configure(state=NORMAL)
      self.text.insert(END, s)
      self.text.configure(state=self.original_state)
      self.up_to_date = False
      # If we write something, show this window if it's not already
      self.revealme()

   def savetext(self, event=None):
      """ Save to the old filename if we already saved once """
      if hasattr(self, 'fname'):
         self.text.configure(state=NORMAL)
         f = open(self.fname, 'w')
         f.write(self.text.get('0.0', END))
         f.close()
         self.text.configure(state=self.original_state)
         self.up_to_date = True

      else:
         return self.saveastext(event)

   def saveastext(self, event=None):
      """ Offer to save this to a new file """
      from tkFileDialog import asksaveasfilename
      from tkMessageBox import showwarning

      fname = asksaveasfilename(parent=self, title='Save Text to File', 
                                defaultextension='.txt')
      # Allow cancelling
      if not fname: return

      self.fname = fname

      try:
         f = open(fname, 'w')
      except IOError:
         showwarning('Bad Permissions', 'Could not open %s for writing!' %
                     fname)
         return
      
      # Activate text object, extract the text, then reset the state
      self.text.configure(state=NORMAL)
      f.write(self.text.get('0.0', END))
      self.text.configure(state=self.original_state)
      f.close()
      self.up_to_date = True

   def destroy(self):
      """ See if we want to save before closing """
      from tkMessageBox import askyesno
      if not self.safe_close: 
         Toplevel.destroy(self)
         return
      if not hasattr(self, 'fname'):
         # No filename?  We have to ask to save
         if askyesno('Save File?', 'Do you want to save the text in this '
                     'window?', parent=self):
            self.saveastext()
         Toplevel.destroy(self)
         return
      # If we are here, we want to ask to save
      if self.original_state is DISABLED and self.up_to_date:
         # Already up-to-date
         Toplevel.destroy(self)
      elif self.original_state is NORMAL or not self.up_to_date:
         # Now we have to do text comparison. Yuck
         file_text = open(self.fname, 'r').read()
         window_text = str(self.text.get('0.0', END))
         if file_text != window_text:
            if askyesno('Save File?', 'Do you want to save the text in this '
                        'window?', parent=self):
               self.savetext()
         Toplevel.destroy(self)
         return

      # See if our text is different
   def hideme(self):
      """ Hides the current window """
      if not self.hidden:
         self.withdraw()
         self.hidden = True

   def revealme(self):
      """ Brings the window back """
      if self.hidden:
         self.deiconify()
         self.hidden = False

   def clear(self, event=None):
      """ Clears all text from this window """
      self.text.config(state=NORMAL)
      self.text.delete('0.0', END)
      self.text.config(state=self.original_state)

class PeakEditor(Toplevel):
   """ Class to allow users to edit the peaks they want """
   def __init__(self, master):
      """ Instantiates the new window """
      from spam.gui.spam_globals import global_spam_files
      from spam.xyzpeaks import read_xyz_peaks
      from spam.exceptions import BaseSpamError, BaseSpamWarning
      from tkMessageBox import showwarning
      self.allvar = IntVar() # define this here since it is required in destroy
      self.allvar.set(1)
      # Load the peak file, and bail out early if it is no good
      self.peak_file = global_spam_files['xyz']
      try:
         self.peaks = read_xyz_peaks(self.peak_file)
      except (BaseSpamError, BaseSpamWarning), err:
         showwarning('Bad Peak File', '%s : %s' % (type(err).__name__, err))
         self.destroy()
         return
      
      # Now set up the window
      Toplevel.__init__(self, master, width=200, height=50)
      self.title('SPAM Peak Editor')

      # Set up the geometry and apply a scrollbar in the Y-direction
      self.resizable(True, True)
      self.scroller = Scrollbar(self, orient=VERTICAL)
      self.scroller.grid(column=1, row=0, sticky=N+S+E+W)
      self.columnconfigure(0, weight=1)
      self.columnconfigure(1, weight=0)
      self.rowconfigure(0, weight=1)

      # Set up the buttons in the window in its own scrollable 'rootframe'
      canvas = Canvas(self, yscrollcommand=self.scroller.set, width=350, 
                      height=450)
      self.rootframe = Frame(canvas)
      self.scroller.config(command=canvas.yview)
      # Set the title and 'all' checkbox
      label = Label(self.rootframe, text='Select Peaks to Keep')
      label.grid(column=0, row=0, padx=10, pady=20, columnspan=3)
      self.all = Checkbutton(self.rootframe, command=self.toggle_all, 
                             text='Select All', variable=self.allvar)
      self.all.grid(column=0, row=1, padx=10, pady=20, sticky=W)
      label = Label(self.rootframe, text='(X     Y     Z)')
      label.grid(column=1, row=1, padx=10, pady=20, sticky=W)
      label = Label(self.rootframe, text='Density')
      label.grid(column=2, row=1, padx=10, pady=20, sticky=E)
      # Now make a list of all the peaks, and turn them all on by default
      self.vars = [IntVar() for i in range(len(self.peaks))]
      for var in self.vars: var.set(1)
      self.buttons = []
      for i, peak in enumerate(self.peaks):
         self.buttons.append(PeakButton(self.rootframe, 'Peak %d' % (i+1), 
                                        self.vars[i], self.check_boxes))
      # Now grid all of the buttons
      for i, button in enumerate(self.buttons):
         button.grid(column=0, row=2+i, pady=5, padx=10, sticky=W)
         label = Label(self.rootframe, text='(%.3f, %.3f, %.3f)' % 
                       (self.peaks[i].x, self.peaks[i].y, self.peaks[i].z)
                      )
         label.grid(column=1, row=2+i, pady=5, padx=10, sticky=W)
         label = Label(self.rootframe, text='%.4f' % self.peaks[i].density)
         label.grid(column=2, row=2+i, pady=5, padx=10, sticky=E)
      # Check all of the boxes to see if they're all activated (they should be)
      self.check_boxes()
      # Now create the window to the canvas
      canvas.create_window(0,0, anchor=NW, window=self.rootframe)
      # Now grid the canvas
      canvas.grid(column=0, row=0, sticky=N+S+E+W)
      # Add a button to close out this window and save the peaks
      self.finish_button = Button(self, text='Write New Peaks File', 
                                  command=self.destroy)
      self.finish_button.grid(column=0, columnspan=1, row=2, sticky=N+S+E+W)
      self.update_idletasks()
      canvas.configure(scrollregion=self.rootframe.bbox(ALL))
      # Throw in a reference to the canvas so there's no chance it's lost
      self.canvas = canvas
      # Grab the attention, and don't relinquish until the window is closed
      self.grab_set()

   def toggle_all(self):
      """ Toggle all of the peaks """
      # If they're all toggled, turn them all off. Otherwise turn them all on
      # Note that the all switch was just toggled, so the allvar value will be
      # the reverse of what you would expect
      if not self.allvar.get():
         for var in self.vars: var.set(0)
      else:
         for var in self.vars: var.set(1)

   def check_boxes(self):
      """
      This is the callback for any 'peak' button that is checked, and causes
      me to go through and check the state of all boxes so I know how 
      'toggle_all' should appear and/or behave...
      """
      for var in self.vars:
         if var.get() == 0:
            self.allvar.set(0)
            return
      self.allvar.set(1)

   def saveme(self):
      """ Ask if we want to save our new peaks file """
      from tkMessageBox import askyesno
      # If we selected all of our boxes, there is nothing to do
      if self.allvar.get():
         return

      if askyesno('Peaks Edited', 'You have not selected all of the '
                  'peaks. Do you wish to modify the peak definitions '
                  'file with your selected peaks and proceed?'):
         # Go through and delete all of the peaks that were not selected, and
         # write out the remaining peaks to the same peak file
         for i in range(len(self.vars)-1, -1, -1):
            if self.vars[i].get(): continue
            del self.peaks[i]
         self.peaks.write_peaks(self.peak_file)
      
   def destroy(self):
      """ Save our peaks first, then destroy """
      self.saveme()
      Toplevel.destroy(self)

class PeakButton(Checkbutton):
   """ This is a button for a peak inside the PeakEditor """

   def __init__(self, master, title, variable, command):
      """ Instantiates a Checkbutton """
      Checkbutton.__init__(self, master, text=title, variable=variable,
                           command=command)
