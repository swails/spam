"""
This contains the 3 main SPAM buttons, based on a derived class
"""
from __future__ import division
from Tkinter import *
from spam.exceptions import InternalError, SpamTypeError
from spam.gui.action_windows import (ActionFrame, DensityFrame, 
                                     TrajReorderFrame, SpamCalcFrame)

class _TopLevelButton(Button):
   """ General class for all top level command buttons """
   ActionFrame = ActionFrame
   def __init__(self, *args, **kwargs):
      """ Constructor """
      Button.__init__(self, *args, **kwargs)
      self.bind("<Button-3>", self._print_help)
      self.config(command=self.execute)
      self.actionframe = self._get_action_frame()
      self.actionframe.messages = self.master.masterlog
      self._is_pressed = False

   def execute(self):
      """ 
      Event binding for being clicked.  Perform common tasks then dispatch it
      to a class-specific _execute method
      """
      self._is_pressed = not self._is_pressed
      self.master.activate_button(self)
      if self._is_pressed:
         self.config(relief=SUNKEN)
      else:
         self.config(relief=RAISED)
      self.actionframe.toggle()

   def _get_action_frame(self):
      """ Returns the ActionFrame associated with this button """
      return self.ActionFrame(self.master)

   def turn_off(self):
      """
      Turns off this button -- trickles down to the action frame as well
      """
      self._is_pressed = False
      self.config(relief=RAISED)
      self.actionframe.turn_off()

class DensityButton(_TopLevelButton):
   """ Button that activates density calculation """
   ActionFrame = DensityFrame
   def _print_help(self, eventobj):
      """ Opens up a file dialog of the help button """
      import tkMessageBox
      tkMessageBox.showinfo("Peak Identification Information",
                            "The options in this section deal with calculating "
                            "the water density and determining the density "
                            "peak locations.  cpptraj is used for this step")
   
class TrajButton(_TopLevelButton):
   """ Button that activates trajectory reordering """
   ActionFrame = TrajReorderFrame
   def _print_help(self, eventobj):
      """ Opens up a file dialog of the help button """
      import tkMessageBox
      tkMessageBox.showinfo("Trajectory Reordering Information",
                            "The options in this section deal with generating "
                            "a reordered trajectory file in which the same "
                            "water molecule is in the same site for each frame "
                            "so the free energies can be calculated")

class SpamButton(_TopLevelButton):
   """ Button that activates density calculation """
   ActionFrame = SpamCalcFrame
   def _print_help(self, evenobj):
      """ Opens up a file dialog of the help button """
      import tkMessageBox
      tkMessageBox.showinfo("SPAM Free Energy Calculation",
                            "The options in this section deal with calculating "
                            "the energy for each water site using NAMD and "
                            "calculating SPAM statistics for each site.  This "
                            "is typically the most time-consuming step.")

