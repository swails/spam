"""
Contains all of the widgets necessary for creating the SPAM menu bar
"""
from __future__ import division
from Tkinter import *
from spam.exceptions import InternalError

# Nonsense codes.
NEW = 1234321
OLD = 4321234
NEWAPPEND = -1234321
OLDAPPEND = -4321234

class SpamMenu(Menu):
   """ Generates the menu bar for SPAM """
   def __init__(self, master):
      """ Constructor. Generates how the menu will look """
      Menu.__init__(self, master, tearoff=0, relief=FLAT, 
                    activeborderwidth=0)
      self.program_menu = FileMenu(self, name='Programs',
                                   files=('cpptraj', 'namd'),
                                   statuses=(OLD, OLD),
                                   keys=('cpptraj', 'namd'))
      self.needed_file_menu = FileMenu(self, name='Files',
                     files=('Prmtop', 'Add Trajectory', 'DX Density', 
                            'Output File', 'Clear Input Trajectories'),
                     statuses=(OLD, OLDAPPEND, NEW, NEW, NEW),
                     filetypes=(('Amber Prmtop'), ('Amber Traj', 'Amber NetCDF',
                                                   'CHARMM/NAMD Dcd'), 
                                ('Data Explorer'), ('Output'), ()),
                     typesfx=(('.prmtop'), ('.mdcrd', '.nc', '.dcd'), ('.dx'),
                              ('.out'), ()),
                     keys=('prmtop', 'inptraj', 'dx', 'output', 'callback_2'),
                     separators=[3],
                     ask_file=[True, True, True, True, False],
                                      )
      self.intermediate_file_menu = FileMenu(self, name='Intermediate Files',
                     files=('Prefix', 
                            'Peak', 'SPAM Info', 'Reordered Trajectory',
                            'PDB Prefix', 'Inpcrd', 'NAMD Output Prefix'),
                     statuses=(NEW, NEW, NEW, NEW, NEW, NEW, NEW),
                     filetypes=((), 
                                ('XYZ File'), ('SPAM Info File'), ('DCD File'),
                                ('PDB File'), 
                                ('Amber Inpcrd File', 'Amber Restart File'), 
                                ()),
                     typesfx=((), ('.xyz'), ('.info'), ('.dcd'), ('.pdb'),
                              ('.inpcrd', '.restrt'), ()),
                     keys=('callback_1', 'xyz', 'spaminfo', 
                           'traj', 'pdb', 'incrd', 'namdout')
                                            )
      self.help_menu = SpamHelpMenu(self)
      self.option_menu = OptionMenu(self)
      self.add_cascade(label='Options', underline=0, menu=self.option_menu)
      self.add_cascade(label='Programs', underline=0, menu=self.program_menu)
      self.add_cascade(label='Files', underline=0, menu=self.needed_file_menu)
      self.add_cascade(label='Intermediate Files', underline=0,
                       menu=self.intermediate_file_menu)
      self.add_cascade(label='Help', underline=0, menu=self.help_menu)

class FileMenu(Menu):
   """ This is the Menu items of the list of file options """
   def __init__(self, master, name, files, statuses, filetypes=None, 
                typesfx=None, keys=None, separators=None,
                ask_file=None):
      """ Instantiates a cascade list of file name options """
      Menu.__init__(self, master, tearoff=0)
      self.name = name
      nfiles = len(files)
      if typesfx is None: typesfx = tuple([() for i in range(nfiles)])
      if filetypes is None: filetypes = tuple([() for i in range(nfiles)])
      # See if we need to ask for a file -- by default we have to every time
      if ask_file is None: ask_file = [True for i in range(nfiles)]
      if keys is None:
         raise InternalError('keys cannot be None in FileMenu!')

      self.items = [FileMenuItem(self, keys[i], statuses[i], filetypes[i], 
                                 typesfx[i]) for i in range(len(files))]
      # Now add all of these items into the 
      for i, item in enumerate(self.items):
         if ask_file[i]:
            self.add_command(activeforeground='white', activebackground='blue',
                             label=files[i], command=self.items[i].get_filename)
         else:
            self.add_command(activeforeground='white', activebackground='blue',
                             label=files[i], command=self.items[i].do_cmd)
         # See if we want to add a separator here
         if separators is not None and i in separators:
            self.add_separator()

      # Now add the 'show' command, separated from the others
      self.add_separator()
      self.add_command(activeforeground='white', activebackground='blue',
                       label='Show Current Names', command=self.show)

   def show(self):
      """ Shows the default values for all of the allowed options """
      from os.path import split
      from spam.gui.spam_globals import global_spam_files
      from tkMessageBox import showinfo
      
      infotext = ''
      keys = [item.key for item in self.items]
      for key in [item.key for item in self.items]:
         if key.startswith('callback_'): continue
         if global_spam_files[key] is None or global_spam_files[key] == []:
            infotext += '%s : <No File Selected>\n' % key
         elif isinstance(global_spam_files[key], list):
            infotext += '%s : %s\n' % (key, [split(f)[1] for f in 
                  global_spam_files[key]])
         else:
            infotext += '%s : %s\n' % (key, split(global_spam_files[key])[1])

      showinfo(self.name, infotext)

   def callback_1(self):
      """ Change Prefix """
      import spam.gui.spam_globals as main
      # First swap all default file names over to the new prefix if it has the
      # old prefix
      for key in main.global_spam_files.keys():
         if key == 'callback_1': continue
         if isinstance(main.global_spam_files[key], str) and \
                     main.global_spam_files[key].startswith(main.FN_PRE):
            main.global_spam_files[key] = (main.global_spam_files['callback_1']
               + main.global_spam_files[key][len(main.FN_PRE):])
      main.FN_PRE = main.global_spam_files['callback_1']
      del main.global_spam_files['callback_1']

   def callback_2(self):
      """ Clear Trajectory List """
      import spam.gui.spam_globals as main
      main.global_spam_files['inptraj'] = []

class FileMenuItem(object):
   """ This is a button that resides in a file cascade menu """
   def __init__(self, master, key, status=OLD, filetypes=(), suffixes=()):
      """ Sets up how this button will appear """
      self.status = status
      self.key = key
      self.master = master
      filetypes = _totuple(filetypes)
      suffixes = _totuple(suffixes)
      # Construct the filetypes
      self.filetypes = []
      if len(filetypes) != len(suffixes):
         raise InternalError("Bad Description/File Type list for "
                             "FileMenuButton! (%d and %d should be the same)" %
                             (len(filetypes), len(suffixes)) )
      for i in range(len(filetypes)):
         self.filetypes.append((filetypes[i], suffixes[i]))
      self.filetypes.append(('All Files', '*'))

   def get_filename(self):
      """ This is called if the file should already exist """
      from spam.gui.spam_globals import global_spam_files
      if self.status is OLD:
         from tkFileDialog import askopenfilename as dialog
      elif self.status is OLDAPPEND:
         from tkFileDialog import askopenfilenames as dialog
      elif self.status is NEW or self.status is NEWAPPEND:
         from tkFileDialog import asksaveasfilename as dialog

      key = self.key
      if key.startswith('callback_'):
         key = getattr(self.master, self.key).__doc__
      item = dialog(title=key, parent=self.master, filetypes=self.filetypes)
      if item is u'': return
      # See if we have to append the file (i.e., this is a file list), or if
      # we just want to select one file
      if self.status is NEW or self.status is OLD:
         global_spam_files[self.key] = item
      elif self.status is NEWAPPEND or self.status is OLDAPPEND:
         global_spam_files[self.key].extend(item)

      # Handle any callbacks
      if self.key.startswith('callback_'):
         getattr(self.master, self.key)()

   def do_cmd(self):
      """ This is basically get_filename without the file prompt window """
      if self.key.startswith('callback_'):
         getattr(self.master, self.key)()
      else:
         raise InternalError('do_cmd must have a callback!')
      
class SpamHelpMenu(Menu):
   """ The Help menu for the spam menu bar """
   def __init__(self, master):
      """ Instantiates the Spam Help Menu on the main toolbar """
      from spam.gui.toplevel_app import Help, Credits
      Menu.__init__(self, master, tearoff=0)
      self.add_command(activeforeground='white', activebackground='blue',
                       label='Help', accelerator='<F1>', 
                       command=lambda: Help(self.master))
      self.add_separator()
      self.add_command(activeforeground='white', activebackground='blue',
                       label='About', command=lambda: Credits(master))

class OptionMenu(Menu):
   """ The menu for the Option cascade """
   def __init__(self, master):
      """ Instantiates the OptionMenu on the main toolbar """
      Menu.__init__(self, master, tearoff=0)
      self.add_command(activeforeground='white', activebackground='blue',
                       label='Show Messages', 
                       command=self.master.master.show_messages)
      self.add_separator()
      self.add_command(activeforeground='white', activebackground='blue',
                       label='Quit SPAM.pie', 
                       command=self.master.master.annihilate)

def _totuple(obj):
   """ Cast something into a TUPLE if it is not already """
   if isinstance(obj, tuple):
      return obj
   if isinstance(obj, list):
      return tuple(obj)
   if isinstance(obj, str):
      return tuple([obj])
   raise SpamTypeError("Can only cast str and list to tuple! You are %s" %
                       type(obj).__name__)
