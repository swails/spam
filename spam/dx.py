"""
This module contains classes/methods for manipulating DX files
"""
from __future__ import division
import os
import re
import numpy as np
from spam.exceptions import (DxFileError, NoFileExists, SpamGridError, 
                             InternalError, FileExists, SpamTypeError,
                             OutOfBoundsWarning)

overwrite = False

class ThreeDGrid(np.ndarray):
   """ The base DX class """

   def __new__(subtype, shape, dtype=float, buffer=None, offset=0,
               strides=None, order=None, origin=None, resolution=None,
               description=None):
      """ Constructor for ndarray -- called before __init__ """
      if len(shape) != 3:
         raise SpamGridError("ThreeDGrid must be a 3-D array!")
      newobj = np.ndarray.__new__(subtype, shape, dtype, buffer, offset,
                                  strides, order)
      newobj.xsize = shape[0]
      newobj.ysize = shape[1]
      newobj.zsize = shape[2]
      newobj.gridsize = shape[0] * shape[1] * shape[2]
      
      if newobj.gridsize == 0:
         raise SpamGridError("No grid points! Make sure all dimensions are " +
                             "non-zero")

      try:
         if origin is not None and len(origin) != 3:
            raise InternalError("Origin must have only X,Y,Z elements!")
         if origin is not None:
            newobj.xorigin = float(origin[0])
            newobj.yorigin = float(origin[1])
            newobj.zorigin = float(origin[2])
         else:
            newobj.xorigin = None
            newobj.yorigin = None
            newobj.zorigin = None
      except TypeError:
         raise InternalError("Illegal 'origin' argument to ThreeDGrid!")
      except ValueError:
         raise InternalError("Illegal 'origin' argument to ThreeDGrid! " +
                             "I require 3 floating point values!")

      try:
         if resolution is not None and len(resolution) != 3:
            raise InternalError("Resolution must have only X,Y,Z elements!")
         if resolution is not None:
            newobj.xres = float(resolution[0])
            newobj.yres = float(resolution[1])
            newobj.zres = float(resolution[2])
         else:
            newobj.xres = None
            newobj.yres = None
            newobj.zres = None
      except TypeError:
         raise InternalError("Illegal 'resolution' argument to ThreeDGrid!")
      except ValueError:
         raise InternalError("Illegal 'resolution' argument to ThreeDGrid! " +
                             "I require 3 floating point values!")
      
      newobj.description = description

      return newobj

   def __array_finalize__(self, obj):
      """
      Our array should have already been initialized, so now we just add our
      extra attributes to ndarray
      """
      # There are 3 ways to call __array_finalize__ -- if obj is None, we did
      # everything we had to do in __new__ above.  If obj is of type ndarray,
      # we are trying to cast it (i.e., via ndarrayinstance.view(ThreeDGrid))
      # If obj is of type ThreeDGrid, that means we're trying to take some kind
      # of slice, which we will disallow until we have a better way of adjusting
      # the attributes properly for such a slice
      if obj is None: return

      if type(obj).__name__ == 'ndarray':
         # We are casting, so set some dummy attributes
         self.xorigin = self.yorigin = self.zorigin = None
         self.xres = self.yres = self.zres = None
         self.description = None

   def set_origin(self, x, y, z):
      """ Sets the origin of the density plot """
      self.xorigin = float(x)
      self.yorigin = float(y)
      self.zorigin = float(z)

   def set_resolution(self, x, y, z):
      """ Sets the resolution of the density plot """
      self.xres = float(x)
      self.yres = float(y)
      self.zres = float(z)

   def set_description(self, desc_str):
      """ Sets the description string (last line of the DX file) """
      self.description = desc_str

   def get_density_cartesian(self, x, y, z):
      """
      Gets the density at a set of given cartesian coordinates.  That is, it
      will determine which grid point the value is closest to (no interpoloation
      or anything like that) and return the value of the density at that point
      """
      if (x > self.xorigin + (self.xsize+1) * self.xres or
          x < self.xorigin - self.xres or
          y > self.yorigin + (self.ysize+1) * self.yres or
          y < self.yorigin - self.yres or
          z > self.zorigin + (self.zsize+1) * self.zres or
          z < self.zorigin - self.zres):
         raise OutOfBoundsWarning("Point {%f, %f, %f} is outside the grid!" % 
                                  (x,y,z))
      xcoor = int(round((x - self.xorigin) / self.xres))
      ycoor = int(round((y - self.yorigin) / self.yres))
      zcoor = int(round((z - self.zorigin) / self.zres))

      return self[xcoor][ycoor][zcoor]

   def write_dx(self, dxfile):
      """ Writes a DX file from the density information """
      global overwrite
      if type(dxfile).__name__ == 'str':
         if os.path.exists(dxfile) and not overwrite:
            raise FileExists("%s exists. Not overwriting." % dxfile)
         outfile = open(dxfile, 'w')
         close_after = True
      elif hasattr(dxfile, 'write'):
         outfile = dxfile
         close_after = False
      else:
         raise SpamTypeError("Unrecognized type in write_dx: %s" % 
                             type(dxfile).__name__)
      
      # Write out the header
      outfile.write("object 1 class gridpositions counts %d %d %d\n" %
                    (self.xsize, self.ysize, self.zsize))
      outfile.write("origin %g %g %g\n" % (self.xorigin, self.yorigin,
                                           self.zorigin))
      outfile.write("delta %g 0 0\n" % self.xres)
      outfile.write("delta 0 %g 0\n" % self.yres)
      outfile.write("delta 0 0 %g\n" % self.zres)
      outfile.write("object 2 class gridconnections counts %d %d %d\n" %
                    (self.xsize, self.ysize, self.zsize))
      outfile.write(("object 3 class array type double rank 0 items %d data " +
                     "follows\n") % self.gridsize)
      ndata = 0
      # Now it's time to write the data
      for i in range(self.shape[0]):
         for j in range(self.shape[1]):
            for k in range(self.shape[2]):
               outfile.write("%g " % self[i][j][k])
               ndata += 1
               if not ndata % 3: outfile.write("\n")
      
      if ndata % 3: outfile.write('\n')
      # Now write the tail
      outfile.write('\n')
      outfile.write("object %s class field\n" % self.description)
      if close_after: outfile.close()

def read_dx(fname):
   """ Reads a DX file and returns the data in a ThreeDGrid object """
   # Define the regular expressions we will use to parse the DX file
   line1re = re.compile(r'object 1 class gridpositions counts *(\d+) *(\d+) *(\d+)')
   originre = re.compile(r'origin ([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][+-]?\d+)?) *([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][+-]?\d+)?) *([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][+-]?\d+)?)')
   deltare = re.compile(r'delta *([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][+-]?\d+)?) *([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][+-]?\d+)?) *([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][+-]?\d+)?)')
   line2re = re.compile(r'object 2 class gridconnections counts *(\d+) *(\d+) *(\d+)')
   line3re = re.compile(r'object 3 class array type double rank 0 items *(\d+) *data follows')
   datalinere = re.compile(' *([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][+-]?\d+)?) +([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][+-]?\d+)?) +([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][+-]?\d+)?)')
   descre = re.compile(r"""object ((?:"?.*"?)|(?:'?.*'?)) class field""")

   # Function to increment x/y/z indices into a 3-D array assuming Z changes
   # fastest
   def increment(x, y, z, sizes):
      z += 1
      if (z == sizes[2]):
         z = 0
         y += 1
         if (y == sizes[1]):
            y = 0
            x += 1
      return (x, y, z)

   if not os.path.exists(str(fname)):
      raise NoFileExists("%s cannot be found!")
   
   infile = open(str(fname), 'r')

   # Find the first line, which enumerates the grid dimensions, the instantiate
   # the ThreeDGrid return object and initialize it to 0
   rematch = line1re.match(infile.readline())
   while not rematch:
      line = infile.readline()
      if not line:
         raise DxFileError("Bad DX Format. Could not find first object")
      rematch = line1re.match(line)
   x, y, z = rematch.groups()
   gridshape = (int(x), int(y), int(z))

   # Find the second line, which identifies the origin
   rematch = originre.match(infile.readline())
   if not rematch:
      raise DxFileError("Bad DX Format. Could not find the origin")
   x, y, z = rematch.groups()
   gridorigin = (float(x), float(y), float(z))

   # The next 3 lines should be the resolution.  The DX file allows arbitrary
   # cartesian coordinate systems, but here I will limit what this class can
   # handle by insisting that two of the three grid spacings be 0 in every
   # dimension -- i.e., it's the canonical grid system defined by xres, yres,
   # zres (rather than non-trivial linear combinations of the 'unit' vectors).

   # X-coordinate
   rematch = deltare.match(infile.readline())
   if not rematch:
      raise DxFileError("Bad DX Format. Could not find X resolution")
   x = float(rematch.groups()[0])
   if float(rematch.groups()[1]) != 0 or float(rematch.groups()[2]) != 0:
      raise DxFileError("Unsupported DX file. Non-canonical coordinates!")

   # Y-coordinate
   rematch = deltare.match(infile.readline())
   if not rematch:
      raise DxFileError("Bad DX Format. Could not find Y resolution")
   y = float(rematch.groups()[1])
   if float(rematch.groups()[0]) != 0 or float(rematch.groups()[2]) != 0:
      raise DxFileError("Unsupported DX file. Non-canonical coordinates!")

   # Z-coordinate
   rematch = deltare.match(infile.readline())
   if not rematch:
      raise DxFileError("Bad DX Format. Could not find Z resolution")
   z = float(rematch.groups()[2])
   if float(rematch.groups()[0]) != 0 or float(rematch.groups()[1]) != 0:
      raise DxFileError("Unsupported DX file. Non-canonical coordinates!")

   gridres = (x, y, z)

   # Grab the next 2 objects and just check for consistency
   rematch = line2re.match(infile.readline())
   if not rematch:
      raise DxFileError("Bad DX Format. Could not find gridconnections")
   x, y, z = rematch.groups()
   if (int(x) != gridshape[0] or int(y) != gridshape[1] or 
       int(z) != gridshape[2]):
      raise DxFileError("Bad DX File. Grid counts are inconsistent!")

   rematch = line3re.match(infile.readline())
   if not rematch:
      raise DxFileError("Bad DX Format. Could not find array description")
   n = int(rematch.groups()[0])
   if gridshape[0] * gridshape[1] * gridshape[2] != n:
      raise DxFileError("Bad DX Dfile. Unexpected number of data points")

   # Instantiate the ThreeDGrid
   return_obj = ThreeDGrid(gridshape, origin=gridorigin, resolution=gridres)

   # Now it's time to loop through all of the data
   xpt = ypt = zpt = 0
   for line in infile:
      rematch = datalinere.match(line)
      try:
         x, y, z = rematch.groups()
         return_obj[xpt][ypt][zpt] = float(x)
         xpt, ypt, zpt = increment(xpt, ypt, zpt, return_obj.shape)
         return_obj[xpt][ypt][zpt] = float(y)
         xpt, ypt, zpt = increment(xpt, ypt, zpt, return_obj.shape)
         return_obj[xpt][ypt][zpt] = float(z)
         xpt, ypt, zpt = increment(xpt, ypt, zpt, return_obj.shape)
      except AttributeError:
         # We hit this on our last line -- check if we have 1 or 2 values
         # on our last data line
         last_data = line.split()
         if not last_data:
            break
         elif len(last_data) == 1:
            x = float(last_data[0])
            return_obj[xpt][ypt][zpt] = x
         elif len(rematch.groups()) == 2:
            x, y = float(last_data[0]), float(last_data[1])
            return_obj[xpt][ypt][zpt] = x
            xpt, ypt, zpt = increment(xpt, ypt, zpt, return_obj.shape)
            return_obj[xpt][ypt][zpt] = y
         break

   # Now we have all of our data
   for line in infile:
      rematch = descre.match(line)
      if rematch:
         return_obj.set_description(rematch.groups()[0])
         return return_obj

   # We should have returned before this if we found the last descriptor
   raise DxFileError("Bad DX Format. Could not find the class field")

def test(args):
   from optparse import OptionParser, OptionGroup
   import sys

   parser = OptionParser()
   parser.add_option('-O', '--overwrite', dest='owrite', default=False,
                     action='store_true', help='Allow overwriting files')
   group = OptionGroup(parser, 'ThreeDGrid', 'Test the ThreeDGrid Class')
   group.add_option('-d', '--dx', dest='indx', default=None,
                    help='Input DX file.', metavar='FILE')
   group.add_option('-o', '--out-dx', dest='outdx', default=None,
                    help='Output DX file. Will just be a copy of the input.',
                    metavar='FILE')
   parser.add_option_group(group)
   group = OptionGroup(parser, 'Density Queries', 'Test some of the querying ' +
                       'functionality of the ThreeDGrid class')
   group.add_option('-x', '--x', dest='x', metavar='X_COORDINATE', default=None,
                    type='float', help='X-coordinate to find the density from')
   group.add_option('-y', '--y', dest='y', metavar='Y_COORDINATE', default=None,
                    type='float', help='Y-coordinate to find the density from')
   group.add_option('-z', '--z', dest='z', metavar='Z_COORDINATE', default=None,
                    type='float', help='Z-coordinate to find the density from')
   parser.add_option_group(group)

   opt, arg = parser.parse_args(args=args)

   global overwrite
   overwrite = opt.owrite

   if opt.outdx and not opt.indx:
      print("I cannot output a DX file without an input!")
      sys.exit(1)

   if opt.indx:
      test_dx = read_dx(opt.indx)
      print "%s read successfully" % opt.indx
      print "Grid Statistics:"
      print "  Origin:     (%g, %g, %g)" % (test_dx.xorigin, test_dx.yorigin,
                                        test_dx.zorigin)
      print "  Resolution:  %g [%g, %g]" % (test_dx.xres, test_dx.yres, 
                                           test_dx.zres)
      print "  Grid points: %d x %d x %d" % test_dx.shape
      print "  Grid desc: [ %s ]" % test_dx.description

      if opt.outdx:
         print "\nWriting output DX file %s" % opt.outdx
         test_dx.write_dx(opt.outdx)

   if (opt.x is None or opt.y is None or opt.z is None) and (
       opt.x is not None or opt.y is not None or opt.z is not None):
      print 'You must specify -x, -y, and -z all together!'
      sys.exit(1)

   if opt.x is not None and opt.indx is None:
      print 'You must give me an input DX file to analyze...'
      sys.exit(1)

   if opt.x is not None:
      print "The density at {%f, %f, %f} is %g" % (opt.x, opt.y, opt.z,
         test_dx.get_density_cartesian(opt.x, opt.y, opt.z))
