"""
This module contains the GUI components for building the windows for each of the
three main actions: Peak Identification, Trajectory Reordering, and SPAM it!
"""

from __future__ import division
from spam import AmberParm
from os.path import exists
from time import sleep
from spam.exceptions import BaseSpamError, BaseSpamWarning
from spam.gui.progressbar import ProgressBar
from spam.gui.spam_globals import global_spam_files
from spam.gui.spam_gui_components import (MaskEntry, NumEntry, SiteShapeRadio,
                                          ButtonEntry, StrEntry)
from Tkinter import *
from tkMessageBox import showwarning

class ActionFrame(Frame):
   """ Basic frame container for all of the Actions """
   widget_keys = ['Dummy']
   widget_types = [StrEntry]
   vartypes = [StringVar]
   defaults = ['dummy']
   help = ['Don\'t click this!']
   go = 'Dummy Go!'

   def __init__(self, master):
      Frame.__init__(self, master.master)
      self.ncallbacks = 0
      self.variables = [var() for var in self.vartypes]
      for i, val in enumerate(self.defaults):
         self.variables[i].set(val)
      # Loop through all of the widgets and pack them in as best as possible
      # in a 3-column layout
      for i, widget in enumerate(self.widget_keys):
         w = self.widget_types[i](self, widget, self.variables[i],
                                  self.help[i])
         row, col = i // 2, i % 2
         w.grid(column=col, row=row, padx=10, pady=20, sticky=N+S+E+W)
      # Now build the Go button
      self.go_button = Button(self, height=2, text=self.go, command=self.cmd)
      self.go_button.grid(column=0, columnspan=2, row=row+1, sticky=N+S+E+W)
      self.columnconfigure(0, weight=1)
      self.columnconfigure(1, weight=1)
      for r in range(row+1):
         self.rowconfigure(r, weight=1)
      self._is_packed = False

   def toggle(self):
      """ Turn it either on or off (pack or unpack) """
      if self._is_packed:
         self.pack_forget()
      else:
         self.pack(fill=BOTH, expand=1)

      self._is_packed = not self._is_packed
      
   def turn_off(self):
      """ Toggles IFF this action is turned on """
      self.pack_forget()
      self._is_packed = False

   def turn_on(self):
      """ Toggles IFF this action is turned off """
      self.pack(fill=BOTH, expand=1)
      self._is_packed = True

   def cmd(self):
      """ Dummy Go command """
      import sys
      sys.stdout.write('Going!\n')

class DensityFrame(ActionFrame):
   """ Frame for controlling the density calculations """
   widget_keys = ['Center', 'X-size', 'Y-size', 'Z-size', 'Grid Mask', 
                  'Solvent Mask', 'Resolution', 'Padding', 'Radius', 'Cutoff']
   widget_types = [StrEntry, NumEntry, NumEntry, NumEntry, MaskEntry, MaskEntry,
                   NumEntry, NumEntry, NumEntry, NumEntry]
   vartypes = [StringVar, DoubleVar, DoubleVar, DoubleVar, StringVar, StringVar,
               DoubleVar, DoubleVar, DoubleVar, DoubleVar]
   defaults = ['', 0, 0, 0, '!(:WAT,Na+,Cl-,Mg+,Br-,Cs+,F-,I-,Rb+)', 
               ':WAT@O=', 0.5, 3.0, 1.3, 0.05]
   help = [ #1
            'Defines the center of the grid. Must be of the form [[ X,Y,Z ]]',
            #2
            'Defines the full length of the grid area in the X-dimension',
            #3
            'Defines the full length of the grid area in the Y-dimension',
            #4
            'Defines the full length of the grid area in the Z-dimension',
            #5
            'Defines the region around which the grid will be defined. Cannot '
            'be used with "center"',
            #6
            'Defines the atoms to consider as part of the solvent when '
            'computing the solvent density on the grid',
            #7
            'Distance in Angstroms between adjacent grid points',
            #8
            'Distance in Angstroms to add to the sizes of the grid area in '
            'each dimension around the defined grid mask. Ignored for "center"',
            #9
            'Radius of the solvent atom (typically water Oxygen) when computing'
            ' the solvent density',
            #10
            'Minimum density value to consider when determining peak locations.'
          ]
   go = 'Calculate Density and Find Peaks!'

   def cmd(self):
      """ Calculate the density and whatnot """
      from spam import AmberMask
      from spam.main import setup_peaks_file
      import sys
      # Check that all of our files exist
      if not global_spam_files['inptraj'] or (False in 
            [exists(f) for f in global_spam_files['inptraj']]):
         showwarning('Missing File(s)', 'Either not input trajectories are '
                     'loaded, or some cannot be found!', parent=self)
         return
      if global_spam_files['cpptraj'] is None or not \
                  exists(global_spam_files['cpptraj']):
         showwarning('Missing File(s)', 'Cannot find cpptraj!', parent=self)
         return
      if not exists(global_spam_files['prmtop']):
         showwarning('Missing File(s)', 'Cannot find topology file %s!' % 
                     global_spam_files['prmtop'], parent=self)
         return

      # Load the topology file if it isn't already
      if not hasattr(self.master, 'parm'):
         self.master.parm = AmberParm(global_spam_files['prmtop'])

      try:
         center = self.variables[0].get()
         xsize = self.variables[1].get()
         ysize = self.variables[2].get()
         zsize = self.variables[3].get()
         grid_mask = self.variables[4].get()
         solvent_mask = self.variables[5].get()
         resolution = self.variables[6].get()
         padding = self.variables[7].get()
         radius = self.variables[8].get()
         cutoff = self.variables[9].get()
      except ValueError:
         showwarning('Bad Data Types', 'Could not convert all input variables '
                     'to the appropriate data types. Please check this.',
                     parent=self)
         return

      # Load up a progress bar
      progress = ProgressBar(self.go_button, 'Density Calculation Progress', 1)

      # A blank center should be re-cast as None, since that is how it is
      # tested in setup_peaks_file
      if len(center) == 0: center = None

      # Send off the command
      try:
         setup_peaks_file(global_spam_files['inptraj'], grid_mask, center,
                          xsize, ysize, zsize, solvent_mask,
                          global_spam_files['dx'], resolution, padding, radius,
                          cutoff, global_spam_files['xyz'], 
                          self.master.parm, self.messages,
                          global_spam_files['cpptraj'])
      except (BaseSpamError, BaseSpamWarning), err:
         progress.update()
         sleep(0.4)
         showwarning('SPAM Failed!', '%s: %s' % (type(err).__name__, err),
                     parent=self)
      progress.update()
      sleep(0.4)
      progress.destroy()

class TrajReorderFrame(ActionFrame):
   """ Frame for controlling the trajectory reordering """
   widget_keys = ['Site Shape', 'Site Size', 'Solvent Mask', 'Edit Peaks']
   widget_types = [SiteShapeRadio, NumEntry, MaskEntry, ButtonEntry]
   vartypes = [StringVar, DoubleVar, StringVar, StringVar]
   defaults = ['box', 2.5, ':WAT@O=', None]
   help = [ #1
            'Shape of the site around the density peak. \'box\' is a cube',
            #2
            'Size of the site around each density peak.',
            #3
            'Mask of the solvent residues to use when reordering the '
            'trajectory.',
            #4
            'This allows you to edit which peaks are included in the '
            'trajectory reordering process.'
          ]
   go = 'Re-order Trajectory!'

   def callback_1(self):
      """
      This will open up a window and allow users to manually edit the peaks
      they want to include in the SPAM calculation
      """
      from spam.gui.spam_windows import PeakEditor

      editor = PeakEditor(self)

   def cmd(self):
      """ Controls the commands for trajectory reordering """
      from spam.main import reorder_trajectory
      # Check that all of our files exist
      if not global_spam_files['inptraj'] or (False in 
            [exists(f) for f in global_spam_files['inptraj']]):
         showwarning('Missing File(s)', 'Either not input trajectories are '
                     'loaded, or some cannot be found!', parent=self)
         return
      if global_spam_files['cpptraj'] is None or not \
                  exists(global_spam_files['cpptraj']):
         showwarning('Missing File(s)', 'Cannot find cpptraj!', parent=self)
         return
      if not exists(global_spam_files['prmtop']):
         showwarning('Missing File(s)', 'Cannot find topology file %s!' % 
                     global_spam_files['prmtop'], parent=self)
         return
      if not exists(global_spam_files['xyz']):
         showwarning('Missing File(s)', 'Cannot find peak file %s!' % 
                     (global_spam_files['xyz']) + ' Did you forget to run the '
                     "'Peak Identification' step?", parent=self)
         return

      # Load the topology file if it isn't already
      if not hasattr(self.master, 'parm'):
         self.master.parm = AmberParm(global_spam_files['prmtop'])

      # Get the variables we need
      try:
         site_shape = self.variables[0].get()
         site_size = self.variables[1].get()
         solvent_mask = self.variables[2].get()
      except ValueError:
         showwarning('Bad Data Types', 'Could not convert all input variables '
                     'to the appropriate data types. Please check this.',
                     parent=self)
         return

      # Load up a progress bar
      progress = ProgressBar(self.go_button, 'Trajectory Reordering Progress',1)

      try:
         reorder_trajectory(global_spam_files['inptraj'],
               global_spam_files['xyz'], global_spam_files['traj'],
               solvent_mask, site_shape, global_spam_files['spaminfo'],
               site_size, global_spam_files['cpptraj'], self.master.parm,
               self.messages, global_spam_files['pdb'], 
               global_spam_files['incrd']
                           )
      except (BaseSpamWarning, BaseSpamError), err:
         progress.update()
         sleep(0.4)
         showwarning('SPAM Failed!', '%s : %s' % (type(err).__name__, err),
                     parent=self)
      progress.update()
      sleep(4)
      progress.destroy()

class SpamCalcFrame(ActionFrame):
   """ Frame for controlling the spam calculation """
   widget_keys = ['Number of Subsamples', 'Size of Subsample',
                  'Number of Processors for NAMD', 'Clean Temporary Files']
   widget_types = [NumEntry, NumEntry, NumEntry, ButtonEntry]
   vartypes = [IntVar, IntVar, IntVar, StringVar]
   defaults = [1, -1, 0, '']
   help = [ #1
            'Number of different random subsamples to take from the full '
            'distribution of energies.  Multiple subsamples will give an '
            'estimate of the statistical uncertainty',
            #2
            'Number of points to include in each subsample.  By default, -1 '
            'selects as many points as are in the data set, chosen randomly '
            'with replacement. This is equivalent to bootstrap sampling',
            #3
            'Number of processors to use for NAMD calculations. < 1 means use '
            'all available processors.',
            #4
            'Get rid of all temporary files with the defined filename prefix '
            '(typically _SPAM_)'
          ]
   go = 'Calculate SPAM Energies!'

   def callback_1(self):
      """ If the button is pressed, delete temporary files """
      import os
      from spam.main import FN_PRE
      purge_list = [f for f in os.listdir('.') if f.startswith(FN_PRE)]
      for fname in purge_list:
         os.remove(fname)

   def cmd(self):
      """ This runs NAMD and collects the SPAM statistics """
      import math
      from spam.gui.spam_windows import TextWindow
      from spam.main import run_namd, spam_energies
      from spam.xyzpeaks import read_xyz_peaks
      if global_spam_files['namd'] is None or not \
                  exists(global_spam_files['namd']):
         showwarning('Missing File(s)', 'Cannot find namd!', parent=self)
         return
      if not exists(global_spam_files['xyz']):
         showwarning('Missing File(s)', 'Cannot find peak file %s!' % 
                     (global_spam_files['xyz']) + ' Did you forget to run the '
                     "'Peak Identification' step?", parent=self)
         return
      if not exists(global_spam_files['pdb']):
         showwarning('Missing File(s)', 'Canot find PDB file %s!' %
                     global_spam_files['xyz'], parent=self)
         return
      if not exists(global_spam_files['traj']):
         showwarning('Missing File(s)', 'Cannot find trajectory file %s. ' %
                     global_spam_files['traj'] + ' Did you forget to run the '
                     "'Trajectory Reordering' step?", parent=self)
         return
      if not exists(global_spam_files['spaminfo']):
         showwarning('Missing File(s)', 'Cannot find trajectory file %s. ' %
                     global_spam_files['spaminfo'] + ' Did you forget to run '
                     "the 'Trajectory Reordering' step?", parent=self)
         return

      # Determine if we need to run NAMD by checking if the necessary output
      # files are there.  This allows us to play with the sampling of the
      # final energies without having to take hours to recalculate the energies
      # each time.
      need_energies = False
      peaks = read_xyz_peaks(global_spam_files['xyz'])
      numdigits = int(math.log10(len(peaks)))
      for i in range(len(peaks)):
         if not exists('%s.%s.out' % (global_spam_files['namdout'], 
                                  str(i).zfill(numdigits))
                      ):
            need_energies = True
            break
      
      # Extract the variables
      try:
         subsamples = self.variables[0].get()
         samplesize = self.variables[1].get()
         nproc = self.variables[2].get()
         nproc = max(nproc, 0)
      except ValueError:
         showwarning('Bad Data Types', 'Could not convert all input variables '
                     'to the appropriate data types. Please check this.',
                     parent=self)
         return

      if need_energies:
         import namdcalc
         # Test for the topology file's existence, but this is only necessary
         # if we have to run NAMD
         if not exists(global_spam_files['prmtop']):
            showwarning('Missing File(s)', 'Cannot find topology file %s!' % 
                        global_spam_files['prmtop'], parent=self)
            return
         if not hasattr(self.master, 'parm'):
            self.master.parm = AmberParm(global_spam_files['prmtop'])
   
         # Set up the number of processors we're going to use
         namdcalc.MAXPROCS = nproc
            
         # Load up a progress bar
         progress = ProgressBar(self.go_button, 'NAMD Calculations')

         try:
            run_namd(global_spam_files['pdb'], global_spam_files['traj'],
                     self.master.parm, global_spam_files['incrd'],
                     global_spam_files['namdout'],
                     global_spam_files['xyz'], self.messages, progress)
         except (BaseSpamError, BaseSpamWarning), err:
            showwarning('SPAM Failed!', '%s: %s' % (type(err).__name__, err),
                        parent=self)
            progress.destroy()
         return
         sleep(0.4)
         progress.destroy()

      # Now try to collect the statistics, and put them in a text window
      self.results_window = TextWindow(self, safe_close=True)
      if global_spam_files['output'] is not None:
         self.results_window.title('SPAM Energies (Also written to %s)' %
                                   global_spam_files['output'])
      else:
         self.results_window.title('SPAM Energies')

      try:
         spam_energies(global_spam_files['namdout'], 
                       global_spam_files['spaminfo'], samplesize, 
                       subsamples, self.results_window)
      except (BaseSpamError, BaseSpamWarning), err:
         showwarning('SPAM Failed!', '%s : %s' % (type(err).__name__, err),
                     parent=self)
         return

      # If the user specified an output file, also write it there.
      if global_spam_files['output'] is not None:
         self.results_window.fname = global_spam_files['output']
         self.results_window.savetext()
