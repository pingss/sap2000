from sap2000 import variables
from sap2000.constants import EOBJECT_TYPES
import helpers

class Automaton:
  def __init__(self,program):
    self.__model = program.sap_com_object.SapModel
    self.__program = program

class Movable(Automaton):
  def __init__(self,structure,location,program):
    super(Movable, self).__init__(program)
    self.__structure = structure
    self.__step = variables.step_length
    self.__location = location
    self.beam = {}
    self.num_beams = variables.beam_capacity
    self.weight = variables.robot_load

  def __addload(beam,location,value):
    '''
    Adds a load of the specified value to the named beam at the specific location
    '''
    distance = helpers.distance(self.__location,location)
    self.__model.FrameObj.SetLoadPoint(beam['beam'],variables.robot_load_case, myType=1, dir=10, dist=distance, val=value, relDist=False)

  def __change_location_local(self,new_location, first_beam = {}):
    '''
    Moves the robot about locally (ie, without worrying about the structure, except 
    for when it moves onto the first beam)
    '''
    if first_beam != {}:
      self.beam = first_beam
      self.__addload(first_beam,new_location,self.weight)
    self.__location = new_location

  def __change_location(self,new_location, new_beam):
    '''
    Function that takes care of changing the location of the robot on the
    SAP2000 program. Removes the current load from the previous location (ie,
    the previous beam), and shifts it to the new beam (specified by the new location)
    It also updates the current beam. If the robot moves off the structure, this also
    takes care of it.
    '''
    def removeload(location):
      '''
      Removes the load assigned to a specific location based on where the robot existed (assumes the robot is on a beam)
      '''
      # obtain current values.
      # values are encapsulated in a list as follows: ret, number_items, frame_names, loadpat_names, types, coordinates, directions, rel_dists, dists, loads
      data = self.__model.FrameObj.GetLoadPoint(self.beam['beam'])
      assert data[0] == 0 # Making sure everything went okay

      # Find location of load
      i, j = self.beam['endpoints']
      curr_dist = helpers.distance(i,self.__location)

      # Loop through distances to find our load (the one in self.__location) and remove all reference to it
      # Additionally remove loads not related to our load patters
      indeces = []
      index = 0
      for ab_dist in data[8]  # this provides acces to the absolute_distance from the i-point of the beam
        if helpers.compare(ab_dist,curr_dist) or variables.robot_load_case != data[3][index]:
          indeces.append(index)
        index += 1

      # add the loads we want back to the frame (automatically deletes all previous loads)
      for i in range(data[1]):
        if i not in indeces:
          self.__model.FrameObj.SetLoadPoint(self.beam['beam'], variables.robot_load_case, myType=1, dir=10, dist=data[7][i], val=data[9][i])

    # Move the load off the current location and to the new one (if still on beam), then change the locations
    removeload(self.__location)

    if new_beam != {}:
      self.__addload(new_beam, new_location, self.weight)

    self.__change_location_local(new_location)
    self.beam = new_beam

  def __get_walkable(self,beams):
    '''
    Returns all of the beams in beams which intersect the robots location
    '''
    crawlable = {}
    for beam, (e1,e2) in beams:
      if helpers.on_line(e1,e2,self.__location):
        crawlable[beam] = (e1,e2)

    return crawlable

  def get_location(self):
    '''
    Provides easy access to the location
    '''
    return self.__location

  def wander(self):
    '''
    When a robot is not on a structure, it wanders around randomly. The wandering is
    restricted to the 1st octant in global coordinates. This function finds the nearest
    beam that is connected to the xy-place (ground), if there is one. If the location of
    the robot matches this beam, then the robot can randomly climb up it.
    '''
    random_direction = 

  def do_action(self):
    '''
    In movable, simply moves the robot to another location.
    '''
    # We are not on a beam, so wander about aimlessly
    if self.beam == {}:
      self.wander()

    else:
      move_info = self.get_direction()
      self.move(move_info['direction'], { 'beam'  : move_info['beam']
                                        'endpoints' : move_info['endpoints']})

  def move(self, direction, beam):
    '''
    Moves the robot in direction passed in and onto the beam specified
    '''
    length = helpers.length(direction)

    # The direction is smaller than the usual step, so move exactly by direction
    if length < self.__step:
      new_location = helpers.sum_vectors(self.__location, direction)
      self.__change_location(new_location, beam)

    # The direction is larger than the usual step, so move only the usual step in the specified direction
    else:
      movement = helpers.scale(self.__step, helpers.make_unit(direction))
      new_location = helper.sum_vectors(self.__location, movement)
      self.__change_location(new_location, beam)

  def get_directions_info(self):
    '''
    Returns a list of triplets with delta x, delta y, and delta z of the direction the robot can
    move in. These directions constitute the locations where beams currently exist. Additionally,
    it returns the "box of locality" to which the robot is restricted containing all of the beams
    nearby that the robot can detect (though, this should only be used for finding a connection,
    as the robot itself SHOULD only measure the stresses on its current beam)
    '''
    # Verify that the robot is on its beam and
    # correct if necessary. This is done so that floating-point arithmethic errors don't add up.
    (e1, e2) = self.beam['endpoints']
    if not (helpers.on_line (e1,e2,self.__location)):
      self.__change_location(helpers.correct (e1,e2,self.__location), self.beam)

    # Obtain all local objects
    box = self.__structure.get_box(self.__location)

    # Find beams in the box which intersect the robot's location (ie, where can he walk?)
    crawlable = self.__get_walkable(box)

    directions_info = []
      # Convert endpoints of beams into direction vectors
      for beam, (p1,p2) in crawlable:
        directions_info.append(beam,helpers.make_vector(self.__location,p1))
        directions_info.append(beam,helpers.make_vector(self.__location,p2))

    return {  'box'         : box,
              'directions'  : directions_info }

  def get_direction(directions):
    ''' 
    Figures out which direction to move in. In this class, it simply picks a random
    direction (eventually, it will have a tendency to move upwards when carrying a beam
    and downwards when needing material for the structure). The direction 
    is also returned with it's corresponding beam.
    '''
    from random import choice

    info = self.get_directions_info()
    beam, direction = choice(info['directions'])

    return {  'beam'      : beam,
              'endpoints' : info['box'][beam],
              'direction' : direction }

class Worker(Movable):
  def __init__(self,structure,location,program):
    super(Worker,self).__init__(structure,location,program)
    self.beams = variables.beam_capacity

  def move(self):
    '''
    Overwrite the move functionality of Movable to provide the chance to build in a timestep
    instead of moving to another space.
    '''
    if contruct() == None:
      super(Worker,self).move()
    else:
      self.build()

  def build(self):
    pass

  def construct(self):
    '''
    Decides whether the local conditions dictate we should build (in which case)
    It returns the two points that should be connected, or we should continue moving 
    (in which case, it returns None)
    ''' 
    None