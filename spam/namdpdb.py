"""
This module contains classes/methods pertinent to writing the PDB files that
NAMD needs in order to run pair-wise interactions.
"""
from __future__ import division
import os
import re
import sys
from spam.exceptions import (PDBRecordWarning, BaseSpamWarning, SpamLoopBreak,
                             SpamAtomsWarning, InternalError, NoFileExists,
                             FileExists, SpamTypeError)

overwrite = False

def create_pdb_from_dcd(dcdname, prmtop, pdbname, err_console=sys.stderr):
   """ 
   This function will generate a PDB (dummy file) that can be used to set up
   pair-wise interaction energy calculations
   """
   from subprocess import Popen, PIPE
   from spam.checkprogs import which, CPPTRAJ_NAME
   from spam.exceptions import ExternalProgramError, WarnFileExists, MissingFile

   global overwrite 

   # First look for cpptraj
   cpptraj = which(CPPTRAJ_NAME)

   if cpptraj is None:
      raise ExternalProgramError("Could not find %s" % CPPTRAJ_NAME)

   # Now set up the cpptraj run
   cpptraj_cmd = "trajin %s 1 1 1\ntrajout %s pdb\ngo\n" % (dcdname, pdbname)

   if not os.path.exists(str(prmtop)):
      raise MissingFile("Could not find topology file [[ %s ]]" % prmtop)

   if not overwrite and os.path.exists(pdbname):
      raise WarnFileExists("%s exists. Not overwriting" % pdbname)

   process = Popen([cpptraj, str(prmtop)], stdin=PIPE, stdout=PIPE, stderr=PIPE)

   out, err = process.communicate(cpptraj_cmd)

   if process.wait():
      raise ExternalProgramError("PDB generation in cpptraj failed!")

   # Now that we have the PDB, return the PDB object
   return read_pdb(pdbname, err_console)

def read_pdb(pdbname, err_console=sys.stderr):
   """ Opens a PDB and returns a System object with the included data """
   if not os.path.exists(pdbname):
      raise NoFileExists("Cannot find %s" % pdbname)

   if not hasattr(err_console, 'write'):
      raise InternalError("Cannot write errors to err_console!")

   pdbfile = open(pdbname, 'r')
   return_sys = PdbSystem()
   for line in pdbfile:
      try:
         return_sys.add_pdb_line(line)
      except SpamLoopBreak:
         break
      except BaseSpamWarning, err:
         err_console.write('%s\n' % err)

   return return_sys

class _Atom(object):
   """ Container for an Atom type """
   def __init__(self, num, name, resname, resnum, x, y, z, *args):
      """ Constructor for _Atom """
      self.num = int(num)
      self.name = str(name).strip()
      self.resname = str(resname).strip()
      self.resnum = int(resnum)
      self.x, self.y, self.z = float(x), float(y), float(z)
      self.attributes = [float(arg) for arg in args]

   def set_occupancy(self, occupancy):
      """ Sets the occupancy value, which is the first attribute """
      self.attributes[0] = float(occupancy)

   def __str__(self):
      return ("%-6s%5d %4s %3s  %4i    %8.3f%8.3f%8.3f%6.2f%6.2f" % (
            'ATOM', self.num, self.name.center(4, ' '), 
            self.resname.center(3, ' '), self.resnum, self.x, self.y, 
            self.z, self.attributes[0], self.attributes[1]))

   def write_pdb_line(self, dest):
      """ Writes the line to destination """
      if not hasattr(dest, 'write'):
         raise InternalError("write_pdb_line argument must have a ",
                             "write attribute!")
      dest.write('%s\n' % self)

def pdb_line_to_atom(line):
   """ 
   Parses a line of the format:
   "%-6s%5d %4s %3s  %4i    %8.3f%8.3f%8.3f%6.2f%6.2f          %2s"
   and returns the resulting _Atom
   """
   if line[:6] != 'ATOM  ' and line[:6] != 'HETATM':
      raise PDBRecordWarning("PDB line has unrecognized record [ %s ]!" %
                             line[:6])
   return _Atom(line[6:11], line[12:16], line[17:20], line[22:26],
               line[30:38], line[38:46], line[46:54], line[54:60],
               line[60:66])

class _MultiAtom(object):
   """
   This is a class that contains a list of atoms
   """
   def __init__(self):
      """ Constructor for _Molecule object. Just set up an empty atoms list """
      self.atoms = []

   def add_atom(self, atom):
      """ Add an atom to the list """
      # Set the occupancy of this atom to 1.0 (unlabeled)
      atom = self._set_atom_type(atom)
      self.atoms.append(atom)

   def _set_atom_type(self, atom):
      """ 
      Makes sure we have an _Atom type.  It will convert from a PDB line if
      it is a string type and set the occupancy (attributes[0]) to 1 so that
      it is not labeled. If it is already an _Atom, it keeps its label status
      """
      if type(atom).__name__ == "str":
         try:
            atom = pdb_line_to_atom(atom)
            atom.attributes[0] = 1.00
         except BaseSpamWarning, err:
            raise type(err)("Atom not added to _MultiAtom")
      elif type(atom).__name__ != "_Atom":
         raise SpamTypeError("add_atom: Can only accept _Atom or ",
                             "PDB record line")
      return atom

   def write_to_pdb(self, dest):
      """ Writes all of the atoms to a destination """
      for atom in self.atoms:
         atom.write_pdb_line(dest)

   def label(self):
      """
      Label this collection of _Atoms. In SPAM PDBs, because they are to be read
      by NAMD, "labeling" this collection of atoms is done by setting the
      occupancy of each atom to 2.00
      """
      for atom in self.atoms:
         atom.attributes[0] = 2.00

   def unlabel(self):
      """
      Unlabel this collection of _Atoms. In SPAM PDBs, because they are to be
      read by NAMD, "unlabeling" this collection of atoms is done by setting the
      occupancy of each atom to 1.00
      """
      for atom in self.atoms:
         atom.attributes[0] = 1.00

   def labeled(self):
      """
      Determine if this sequence of atoms is entirely labeled or unlabeled. If
      it is partially labeled, raise a BaseSpamWarning
      """
      _labeled = self.atoms[0].attributes[0] == 2.00
      for atom in self.atoms:
         if _labeled and atom.attributes[0] != 2.00:
            raise SpamAtomsWarning("Only part of _MultiAtom is labeled!")
         elif not _labeled and atom.attributes[0] == 2.00:
            raise SpamAtomsWarning("Only part of _MultiAtom is labeled!")
      return _labeled

   def natom(self):
      """ How many atoms are in this container? """
      return len(self.atoms)

class _Molecule(_MultiAtom):
   """
   This is a collection of multiple atoms in which everybody is connected via a
   bond.  That is, each atom can be reached by any other atom by traversing some
   sequence of bonds
   """
   def write_to_pdb(self, dest, tail='TER'):
      """ 
      We need to write everybody to the PDB, and then add a TER card at the end
      """
      _MultiAtom.write_to_pdb(self, dest)
      dest.write("%s\n" % tail.upper())

class _Residue(_MultiAtom):
   """ 
   This is a residue as defined in a PDB.  Therefore all atoms in this structure
   must have the same residue name and number, or a SpamAtomsWarning is raised
   """
   def add_atom(self, atom):
      """ 
      Make sure we have the same residue name and number as the atoms already
      in this _Residue
      """
      atom = _MultiAtom._set_atom_type(self, atom)
      if len(self.atoms) != 0:
         if (self.atoms[0].resname != atom.resname or
             self.atoms[0].resnum != atom.resnum):
            raise SpamAtomsWarning("Tried adding _Atom to _Residue already ",
                                   "containing atoms from other _Residue's!")
      self.atoms.append(atom)

class PdbSystem(_MultiAtom):
   """ This is a full system, composed of _Molecules and _Residues """
   def __init__(self):
      """ Constructor -- set up blank residue/molecule lists """
      self.molecules = [_Molecule()]
      self.residues = [_Residue()]

   def add_pdb_line(self, pdbline):
      """ 
      Adds an atom from a PDB line to the corresponding _Molecule/_Residue 
      """
      # Make sure pdbline is a string -- this will force an _Atom type into
      # a PDB line, if that's what gets passed
      pdbline = str(pdbline)
      if pdbline[:6] == 'ATOM  ' or pdbline[:6] == 'HETATM':
         atom = _MultiAtom._set_atom_type(self, str(pdbline))

      # This is a TER card, so terminate the current molecule by adding a new
      # one on the end and bail out (nothing more to do)
      elif pdbline[:3] == 'TER':
         self.molecules.append(_Molecule())
         return None

      # Most of the valid PDB records we ignore here.
      elif pdbline[:6] in ('MODEL ', 'HELIX ', 'HEADER', 'SOURCE', 
                           'AUTHOR', 'OBSLTE', 'KEYWDS', 'REVDAT',
                           'TITLE ', 'EXPDAT', 'SPRSDE', 'SPLIT ',
                           'CAVEAT', 'COMPND', 'NUMMDL', 'MDLTYP',
                           'JRNL  ', 'REMARK', 'DBREF ', 'SEQADV',
                           'MODRES', 'DBREF1', 'DBREF2', 'SEQRES',
                           'HET   ', 'HETNAM', 'HETSYN', 'FORMUL',
                           'SHEET ', 'SSBOND', 'LINK  ', 'CONECT',
                           'CISPEP', 'SITE  ', 'CRYST1', 'ORIGXn',
                           'SCALEn', 'MTRIXn', 'ANISOU', 'MASTER'):
         return None
      
      # If we reach an ENDMDL, raise a specialized exception to signify we are
      # done
      elif pdbline[:6] == 'ENDMDL':
         raise SpamLoopBreak("Reached ENDMDL")

      elif pdbline[:3] == 'END':
         raise SpamLoopBreak("Reached END")

      # Otherwise we don't know what this is
      else:
         raise PDBRecordWarning("Unrecognized PDB line:\n %s" % pdbline.strip())

      # Try to add our new atom to our last residue. If it fails, create a new
      # residue and add it to that
      try:
         self.residues[len(self.residues)-1].add_atom(atom)
      except SpamAtomsWarning:
         newres = _Residue()
         newres.add_atom(atom)
         self.residues.append(newres)
      
      # Now add our atom to our last molecule. We already created a new one if
      # we hit a TER card above
      self.molecules[len(self.molecules)-1].add_atom(atom)

      return None

   def label_residue(self, resnum, index_from_zero=True):
      """ Label a specific residue """
      if not index_from_zero:
         resnum -= 1
      self.residues[resnum].label()

   def unlabel_residue(self, resnum=-1, index_from_zero=True):
      """ Unlabel certain residues. If resnum is -1, unlabel all of them """
      if resnum == -1:
         for res in self.residues: res.unlabel()
         return None
      if not index_from_zero:
         resnum -= 1
      self.residues[resnum].unlabel()
      return None

   def natom(self):
      """ 
      Return total number of atoms in this PdbSystem by adding up all of the
      atoms in all of the molecules (this is better than residues since
      there are fewer molecules in general)
      """
      return sum([len(mol.atoms) for mol in self.molecules])

   def write_to_pdb(self, pdbname):
      """ 
      Writes a PDB file of this system.  Do it by molecule to get the TER
      cards right
      """
      global overwrite
      close_after = False
      if type(pdbname).__name__ == 'str':
         if not overwrite and os.path.exists(pdbname):
            raise FileExists("%s exists.  Will not Overwrite" % pdbname)
         pdbfile = open(pdbname, 'w')
         close_after = True
      elif not hasattr(pdbname, 'write'):
         raise SpamTypeError('PDB object is not writeable!')
      else:
         pdbfile = pdbname

      # Write out the first N-1 molecules, then write out the last one with
      # an END tail
      for i in range(len(self.molecules)-1):
         self.molecules[i].write_to_pdb(pdbfile, 'TER')
      self.molecules[len(self.molecules)-1].write_to_pdb(pdbfile, 'END')
      
      # Now close if we opened in the beginning
      if close_after: pdbfile.close()

      return None

   # label and unlabel should be aliased to the above definitions, since
   # there is no "atoms" attribute to System. Also, add_atom is just
   # add_pdb_line
   label = label_residue
   unlabel = unlabel_residue
   add_atom = add_pdb_line
         
def test(args):
   from optparse import OptionParser, OptionGroup
   from spam.exceptions import UsageError

   global overwrite

   parser = OptionParser()
   parser.add_option('-O', '--overwrite', default=False, action='store_true',
                     dest='owrite', help='Overwrite existing output files')
   group = OptionGroup(parser, 'create_pdb_from_dcd', 
                       'These options test the PDB creation using cpptraj')
   group.add_option('-y', '--inptraj', dest='inptraj', default=None,
                    metavar='FILE', help='Input trajectory to extract PDB from')
   group.add_option('-p', '--prmtop', dest='prmtop', default=None,
                    metavar='FILE', help='Prmtop corresponding to -y/--inptraj')
   group.add_option('--pdb', dest='pdb', default=None, metavar='FILE',
                    help='Output PDB file to generate')
   parser.add_option_group(group)
   group = OptionGroup(parser, '_Atom class', '_Atom class test options')
   group.add_option('--run-atom-test', dest='_atest', default=False,
                    action='store_true', help='Run the test for _Atom class')
   parser.add_option_group(group)
   group = OptionGroup(parser, 'PDB File tests',
                       'Tests for the PDB file reading/writing routines')
   group.add_option('-i', '--input-pdb', dest='inpdb', metavar='FILE',
                    default=None, help='Input PDB file to analyze')
   group.add_option('-r', '--residue', dest='labres', metavar='INT',
                    default=1, type='int', help='Residue to label. ' +
                    '(Default %default)')
   group.add_option('-o', '--output-pdb', dest='outpdb', metavar='FILE',
                    default=None, help='PDB file to output')
   parser.add_option_group(group)

   opt, arg = parser.parse_args(args=args)

   overwrite = opt.owrite

   # Catch illegal options
   if opt.outpdb and not opt.inpdb:
      print "-o/--output-pdb must be used with -i/--input-pdb!"
      sys.exit(1)

   if opt.inptraj is not None or opt.prmtop is not None or opt.pdb is not None:
      if opt.inptraj is None or opt.prmtop is None or opt.pdb is None:
         raise UsageError("Bad command-line arguments! Need inptraj, ",
                          "prmtop, and PDB!")
      # Otherwise, execute it
      test_system = create_pdb_from_dcd(opt.inptraj, opt.prmtop, opt.pdb)

   if opt._atest:
      at = _Atom(1932, 'CZ', 'ARG', 128, -22.527, -11.698, 0.235, 0.00, 0.00)

      print 'The loaded atom PDB line is: \n'
      print "%-6s%5d %4s %3s  %4i    %8.3f%8.3f%8.3f%6.2f%6.2f" % ('ATOM',
            at.num, at.name.center(4, ' '), at.resname.center(3, ' '), 
            at.resnum, at.x, at.y, at.z, at.attributes[0], at.attributes[1])

   if opt.inpdb:
      # Pass in an unbuffered stderr to write errors to
      test_system = read_pdb(opt.inpdb, os.fdopen(sys.stderr.fileno(), 'w', 0))
      # Print some statistics about the test system
      if opt.labres:
         test_system.label_residue(opt.labres, index_from_zero=False)
      print '%s Statistics:' % opt.inpdb
      print '   %d atoms' % test_system.natom()
      print '   %d residues' % len(test_system.residues)
      print '   %d molecules' % len(test_system.molecules)
      if opt.outpdb:
         print 'Outputting a new PDB [%s]:' % opt.outpdb
         test_system.write_to_pdb(opt.outpdb)
