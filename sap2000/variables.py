# Units for starting the program
program_units = "kN_m_C"

# Radius of "locality" (how far can a robot obtain information about 
# the structure from where it is located. In units specified by program_units
local_radius = 1

# The size of a step that the robot can take. This is expressed in the specified
# program units.
step_length = .5

# Length of each beam (in the units specified by program_units)
beam_length = 1

# The number of beams that each robot carries (ie, how many elements can
# construct before travelling off the structure)
beam_capacity = 1

# The size of the division of space into blocks. 
# x,y,z gives the number of blocks along the x axix, the y axis, and the z axis
# dim_var gives the limit of the structure on the axis indicated by var. 
# Keep in mind that the origin is the bottom-left part of this structure
num_x = 25
num_y = 25
num_z = 25
dim_x = 50
dim_y = 50
dim_z = 50

# This defines how sensitive the program is to accepting errors within the beam structure
epsilon = 0.01

# This defines the mass of each robot in the units specified by program_units
robot_load = 0.1 # This is around twentyfive pounds in kN

# This defines the load of each beam carried by the robots
beam_load = 0.05 # This is around twelve pounds in kN

# Name of the load case for the robots
robot_load_case = "ROBOTS"

# Name of the material property defined for the beams
material_name = "PIPE"

# Location where construction is to begin
contruction_location = (dim_x / 2, dim_y / 2, dim_z / 2)