#! /usr/bin/python
############################################################################
#
# MODULE:       r.flexure
#
# AUTHOR(S):    Andrew Wickert
#
# PURPOSE:      Calculate flexure of the lithosphere under a specified
#               set of loads and with a given elastic thickness (scalar 
#               or array)
#
# COPYRIGHT:    (c) 2012, 2014 Andrew Wickert
#
#               This program is free software under the GNU General Public
#               License (>=v2). Read the file COPYING that comes with GRASS
#               for details.
#
#############################################################################
#
# REQUIREMENTS:
#      -  gFlex: http://csdms.colorado.edu/wiki/Flexure)
#         (should be downloaded automatically along with the module)
 
# More information
# Started 11 March 2012 as a GRASS interface for Flexure (now gFlex)
# Revised 15--?? November 2014 after significantly improving the model
# by Andy Wickert

#%module
#%  description: Lithospheric flexure
#% keywords: raster
#%end
#%flag
#%  key: l
#%  description: Allows running in lat/lon, assumes 1deg lat = 111.32 km, 1 deg lon is f(lat) at grid N-S midpoint
#%end
#%option
#%  key: method
#%  type: string
#%  description: Solution method: FD (finite difference) or SAS (superposition of analytical solutions)
#%  options: FD, SAS
#%  required : yes
#%end
#%option
#%  key: q
#%  type: string
#%  gisprompt: old,cell,raster
#%  description: Raster map of loads (thickness * density * g) [Pa]
#%  required : yes
#%end
#%option
#%  key: te
#%  type: string
#%  gisprompt: old,cell,raster
#%  description: Elastic thicnkess: constant value or raster map (~constant ) name [km or m: see "units" option]
#%  required : yes
#%end
#%option
#%  key: output
#%  type: string
#%  gisprompt: old,cell,raster
#%  description: Output raster map of vertical deflections [m]
#%  required : yes
#%end
#%option
#%  key: rho_fill
#%  type: double
#%  description: Density of material that fills flexural depressions [kg/m^3]
#%  answer: 0
#%  required : no
#%end
#%option
#%  key: te_units
#%  type: string
#%  description: Units for elastic thickness
#%  options: m, km
#%  required : yes
#%end
#%option
#%  key: northbc
#%  type: string
#%  description: Northern boundary condition
#%  options: Dirichlet0, 0Moment0Shear, 0Slope0Shear, Mirror, Periodic
#%  answer: NoOutsideLoads
#%  required : no
#%end
#%option
#%  key: southbc
#%  type: string
#%  description: Southern boundary condition
#%  options: Dirichlet0, 0Moment0Shear, 0Slope0Shear, Mirror, Periodic
#%  answer: NoOutsideLoads
#%  required : no
#%end
#%option
#%  key: westbc
#%  type: string
#%  description: Western boundary condition
#%  options: Dirichlet0, 0Moment0Shear, 0Slope0Shear, Mirror, Periodic
#%  answer: NoOutsideLoads
#%  required : no
#%end
#%option
#%  key: eastbc
#%  type: string
#%  description: Eastern boundary condition
#%  options: Dirichlet0, 0Moment0Shear, 0Slope0Shear, Mirror, Periodic
#%  answer: NoOutsideLoads
#%  required : no
#%end
#%option
#%  key: g
#%  type: double
#%  description: gravitational acceleration at surface [m/s^2]
#%  answer: 9.8
#%  required : no
#%end
#%option
#%  key: ym
#%  type: double
#%  description: Young's Modulus [Pa]
#%  answer: 65E9
#%  required : no
#%end
#%option
#%  key: nu
#%  type: double
#%  description: Poisson's ratio
#%  answer: 0.25
#%  required : no
#%end
#%option
#%  key: rho_m
#%  type: double
#%  description: Mantle density [kg/m^3]
#%  answer: 3300
#%  required : no
#%end


# PATH
import sys
# Path to Flexure model - hard-coded here
sys.path.append("/home/awickert/models/flexure") # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# OTHER POSSIBLE PROBLEM -- MAKEFILE NEEDS SPECIAL DIR !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# made "scriptstrings" b/c I had to in "locale", may be a problem in general in the future !!!!!!!!!!!!!!!

# FLEXURE
from base import *
from f1d import *
from f2d import *
from prattairy import *

# PYTHON
import numpy as np
import time

# GRASS
from grass.script import core as grass
from grass.script import mapcalc
from grass.script import db as db
import grass.script.array as garray

def main():

  # Flags
  latlon_override = flags['l']
  
  # Inputs
  # Solution selection
  method = options['method']
  # Parameters that are often changed for the solution
  q = options['q']
  Te = options['te']
  Te_units = options['te_units']
  rho_fill = float(options['rho_fill'])
  # Parameters that often stay at their default values
  GravAccel = float(options['g'])
  YoungsModulus = float(options['ym']) # Can't just use "E" because reserved for "east", I think
  PoissonsRatio = float(options['nu'])
  MantleDensity = float(options['rho_m'])
  # Boundary conditions
  bcn = options['northbc']
  bcs = options['southbc']
  bcw = options['westbc']
  bce = options['eastbc']
  # Output
  output = options['output']
  
  # Is Te raster or scalar?
  TeIsRast = False
  try:
    Te = float(Te)
  except:
    TeIsRast = True

  # This code is for 2D flexural isostasy
  obj = F2D()
  obj.set_value('model', 'flexure')
  obj.set_value('dimension', 2)
  
  obj.set_value('GravAccel', 9.8) # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
  if method == 'SAS':
    obj.set_value('method', 'SAS')
  elif method == 'FD':
    obj.set_value('method', 'FD')
    obj.set_value('Solver', 'direct')
    # Always use the van Wees and Cloetingh (1994) solution type.
    # It is the best.
    obj.set_value('PlateSolutionType', 'vWC1994')
    # will this automatically fail if the param is something else via parser?!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

  # No filename: getter/setter interface isn't totally worked out
  # FIX THIS!!!! # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
  obj.filename = None

  # Make a bunch of standard selections
  # CHANGE THESE INTO PARAMETERS THAT CAN BE CHOSEN!
  obj.set_value('GravAccel', GravAccel) # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
  obj.set_value('YoungsModulus', YoungsModulus)#70E6/(600/3300.))#
  obj.set_value('PoissonsRatio', PoissonsRatio)
  obj.set_value('MantleDensity', MantleDensity)

  # Set all boundary conditions
  obj.set_value('BoundaryCondition_East', bce)
  obj.set_value('BoundaryCondition_West', bcw)
  obj.set_value('BoundaryCondition_North', bcn)
  obj.set_value('BoundaryCondition_South', bcs)

  # Get grid spacing from GRASS
  # Check if lat/lon
  if grass.region_env()[6] == '3':
    if latlon_override:
      print "Latitude/longitude grid."
      if obj.get_value('Verbosity'):
        print "Based on r_Earth = 6371 km"
        print "Setting y-resolution [m] to 111,195 * [degrees]"
      obj.set_value('GridSpacing_y', grass.region()['ewres']*111195.)
      NSmid = (grass.region()['n'] + grass.region()['s'])/2.
      dx_at_mid_latitude = (3.14159/180.) * 6371000. * np.cos(np.deg2rad(NSmid))
      print "Setting x-resolution [m] to "+"%.2f" %dx_at_mid_latitude+" * [degrees]"
      obj.set_value('GridSpacing_y', grass.region()['nsres']*dx_at_mid_latitude)
    else:
      sys.exit("Need projected coordinates, or the '-l' flag to approximate.")
  else:
    obj.set_value('GridSpacing_x', grass.region()['ewres'])
    obj.set_value('GridSpacing_y', grass.region()['nsres'])

  # Get loads from GRASS
  q0rast = garray.array()
  q0rast.read(q)
  
  # Get elastic thickness from GRASS if it is not a scalar value
  if TeIsRast:
    FlexureTe = garray.array() # FlexureTe is the one that is used by Flexure
    FlexureTe.read('Teresamp')
    
  # Adjust elastic thickness if given in km
  if Te_units == 'km':
    FlexureTe * 1000 # for km --> m
    # meters are the only other option, so just do nothing otherwise

  # Values set by user -- set to np.array for flow control in main code
  obj.set_value('Loads', np.array(q0rast)) # Te needs to be 1 cell bigger on each edge
  obj.set_value('ElasticThickness', np.array(FlexureTe))# np.ones(Te.shape)*20000)#
  obj.set_value('InfillMaterialDensity', rho_fill) # defaults to 0

  # Calculated values
  obj.drho = obj.rho_m - obj.rho_fill

  # CALCULATE!
  #obj.initialize(None)
  obj.run()
  obj.finalize()

  # Write to GRASS
  # First, shrink the region by 1 cell so it accepts the flexural solution
  n = grass.region()['n'] - grass.region()['nsres']
  s = grass.region()['s'] + grass.region()['nsres']
  e = grass.region()['e'] - grass.region()['ewres']
  w = grass.region()['w'] + grass.region()['ewres']
  nrows = grass.region()['rows']-2
  ncols = grass.region()['cols']-2
  grass.run_command('g.region', n=n, s=s, w=w, e=e, rows=nrows, cols=ncols) 
  # Then create a new garray buffer and write to it
  outbuffer = garray.array() # Instantiate output buffer
  outbuffer[...] = obj.w
  outbuffer.write(output, overwrite=True) # Write it with the desired name
  # And create a nice colormap!
  grass.run_command('r.colors', map=output, color='rainbow', quiet=True)#, flags='e')
  # Then revert to the old region
  grass.run_command('g.region', n=n, s=s, w=w, e=e) 
  n = grass.region()['n'] + grass.region()['ewres']
  s = grass.region()['s'] - grass.region()['ewres']
  e = grass.region()['e'] + grass.region()['ewres']
  w = grass.region()['w'] - grass.region()['ewres']
  grass.run_command('g.region', n=n, s=s, w=w, e=e)

  # Finally, return to original resolution (overwrites previous region selection)
  grass.run_command('g.region', rast=Te)
  grass.run_command('r.resamp.interp', input=output, output=output + '_interp', method='lanczos', overwrite=True, quiet=True)
  grass.run_command('r.colors', map=output + '_interp', color='rainbow', quiet=True)#, flags='e')

  #imshow(obj.w, interpolation='nearest'), show()

if __name__ == "__main__":
  options, flags = grass.parser()
  main()

