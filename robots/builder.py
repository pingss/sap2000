from helpers import helpers
from robots.movable import Movable
import construction, math, operator, pdb, random, variables

class Builder(Movable):
  def __init__(self,name,structure,location,program):
    super(Builder,self).__init__(name,structure,location,program)
    # The number of beams the robot is carrying
    self.num_beams = variables.beam_capacity

    # Whether or not we should start construction
    self.start_construction = False

    # Set the right weight
    self.weight = (variables.robot_load + variables.beam_load * 
      variables.beam_capacity)

    # Stores variables for construction algorithm (this is the robots memory)
    self.memory = {}

    # Climbing up or down
    self.memory['pos_z'] = None

    # Starting defaults
    self.memory['built'] = False
    self.memory['constructed'] = 0

    # Keeps track of the direction we last moved in.
    self.memory['previous_direction'] = None

    # Stores information on beams that need repairing
    self.memory['broken'] = []

  def __at_joint(self):
    '''
    Returns whether or not the robot is at a joint
    '''
    if self.beam is not None:
      for joint in self.beam.joints:
        # If we're at a joint
        if helpers.compare(helpers.distance(self.location,joint),0):
          return joint

    return False

  def current_state(self):
    state = super(Builder, self).current_state()
    state.update({  'num_beams'           : self.num_beams,
                    'start_construction'  : self.start_construction,
                    'next_direction_info' : self.next_direction_info,
                    'memory'              : self.memory})
    
    return state

  def climb_off(self,loc):
    if helpers.compare(loc[2],0) and self.num_beams == 0:
      self.ground_direction = helpers.make_vector(self.location,
        construction.home)
      return True
    else:
      self.ground_direction = None
      return False

  def pickup_beams(self,num = variables.beam_capacity):
    '''
    Pickup beams by adding weight to the robot and by adding num to number 
    carried
    '''
    self.num_beams = self.num_beams + num
    self.weight = self.weight + variables.beam_load * num

    # Set the direction towards the structure
    self.ground_direction = helpers.make_vector(self.location,
      construction.construction_location)

  def discard_beams(self,num = 1):
    '''
    Get rid of the specified number of beams by decresing the weight and the 
    number carried
    '''
    self.num_beams = self.num_beams - num
    self.weight = self.weight - variables.beam_load * num

  def at_home(self):
    '''
    True if the robot is in the area designated as home (on the ground)
    '''
    return helpers.within(construction.home, construction.home_size,
      self.location)

  def at_site(self):
    '''
    True if the robot is in the area designated as the construction site 
    (on the ground)
    '''
    return helpers.within(construction.construction_location, 
      construction.construction_size, self.location)

  # Model needs to have been analyzed before calling THIS function
  def decide(self):
    '''
    This functions decides what is going to be done next based on the analysis 
    results of the program. Therefore, this function should be the one that 
    decides whether to construct or move, based on the local conditions
    and then stores that information in the robot. The robot will then act 
    based on that information once the model has been unlocked. 
    '''
    # We build almost never.
    self.start_construction = False
    self.step = variables.step_length

    # If we decide to construct, then we store that fact in a bool so action 
    # knows to wiggle the beam
    if self.construct():
      self.start_construction = True

    # Otherwise, if we're not on a beam, then we will wander on the ground
    elif self.beam == None:
      # reset steps
      self.next_direction_info = None

    # Otherwise, we are not on the ground and we decided not to build, so pick 
    # a direction and store that
    else:
      self.next_direction_info = self.get_direction()

  # Model needs to be unlocked before running this function! 
  def do_action(self):
    '''
    Overwriting the do_action functionality in order to have the robot move up 
    or downward (depending on whether he is carrying a beam or not), and making 
    sure that he gets a chance to build part of the structure if the situation 
    is suitable. This is also to store the decion made based on the analysis 
    results, so that THEN the model can be unlocked and changed.
    '''
    # Check to see if the robot decided to construct based on analysys results
    if self.start_construction:
      self.build()
      self.start_construction = False

    # Otherwise, we're on a beam but decided not to build, so get direction we 
    # decided to move in, and move.
    elif self.beam is not None:
      assert self.next_direction_info != None
      assert (self.beam is not None)
      self.move(self.next_direction_info['direction'],
        self.next_direction_info['beam'])
      self.next_direction_info = None

    # We have climbed off, so wander about (set the step to 12)
    else:
      self.wander()

  def filter_dict(self,dirs,new_dirs,comp_functions):
    '''
    Filters a dictinary of directions, taking out all directions not in the 
    correct directions based on the list of comp_functions (x,y,z)
    '''
    # Access items
    for beam, vectors in dirs.items():
      # Access each directions
      for vector in vectors:
        coord_bool = True
        # Apply each function to the correct coordinates
        for function, coord in zip(comp_functions,vector):
          coord_bool = coord_bool and function(coord)
        if coord_bool:
          if beam not in new_dirs:
            new_dirs[beam] = [vector]
          else:
            new_dirs[beam].append(vector)
    return new_dirs

  def filter_directions(self,dirs):
    '''
    Filters the available directions and returns those that move us in the 
    desired direction. Should be overwritten to provide more robost 
    functionality
    '''
    directions = {}
    base = [lambda x : True, lambda y : True]
    # Still have beams, so move upwards
    if self.num_beams > 0:
      directions = self.filter_dict(dirs, directions,
        (base.append(lambda z : z > 0)))
    # No more beams, so move downwards
    else:
      directions = self.filter_dict(dirs, directions,
        (base.append(lambda z : z < 0)))

    return directions

  def no_available_direction(self):
    '''
    This specifies what the robot should do if there are no directions available
    for travel. This basically means that no beams are appropriate to climb on.
    We pass here, because we just pick the directio randomly later on.
    '''
    pass

  def pick_direction(self,directions):
    '''
    Functions to pick a new direction once it is determined that we either have 
    no previous direction, we are at a joint, or the previous direction is 
    unacceptable)
    '''
    beam_name = random.choice(list(directions.keys()))
    direction = random.choice(directions[beam_name])

    self.memory['previous_direction'] = beam_name, direction

    return beam_name, direction

  def elect_direction(self,directions):
    '''
    Takes the filtered directions and elects the appropriate one. This function
    takes care of continuing in a specific direction whenever possible.
    '''
    def next_dict(item,dictionary):
      '''
      Returns whether or not the value (a direction vector) is found inside of 
      dictionary (ie, looks for parallel directions)
      '''
      key, value = item
      temp = {}
      for test_key,test_values in dictionary.items():
        # Keys are the same, vectors are parallel (point in same dir too)
        if key == test_key:
          for test_value in test_values:
            if (helpers.parallel(value,test_value) and 
              helpers.dot(value,test_value) > 0):
              if test_key in temp:
                temp[test_key].append(test_value)
              else:
                temp[test_key] = [test_value]
      
      # No values are parallel, so return None
      if temp == {}:
        return None

      # Pick a direction randomly from those that are parallel
      else:
        self.pick_direction(temp)

    # We are not at a joint and we have a previous direction
    if not self.__at_joint() and self.memory['previous_direction'] is not None:

      # Pull a direction parallel to our current from the set of directions
      direction_info = next_dict(self.memory['previous_direction'],directions)

      if direction_info is not None:
        return direction_info

    # If we get to this point, either we are at a joint, we don't have a 
    # previous direction, or that previous direction is no longer acceptable
    return self.pick_direction(directions)

  def get_moment(self,name):
    '''
    Returns the moment for the beam specified by name at the point closest 
    to the robot itself
    '''
    # Format (ret[0], number_results[1], obj_names[2], i_end distances[3], 
    # load_cases[4], step_types[5], step_nums[6], Ps[7], V2s[8], V3s[9], 
    # Ts[10], M2s[11], M3s[12]
    results = self.model.Results.FrameForce(name,0)
    if results[0] != 0:
      helpers.check(ret,self,"getting frame forces",results=results,
        state=self.current_state())
      return 0

    # Find index of closest data_point
    close_index, i = 0, 0
    shortest_distance = None
    distances = results[3]
    for i_distance in distances:
      # Get beam endpoints to calculate global position of moment
      i_end,j_end = self.structure.get_endpoints(name,self.location)
      beam_direction = helpers.make_unit(helpers.make_vector(i_end,j_end))
      point = helpers.sum_vectors(i_end,helpers.scale(i_distance,
        beam_direction))
      distance = helpers.distance(self.location,point)

      # If closer than the current closes point, update information
      if shortest_distance is None or distance < shortest_distance:
        close_index = i
        shortest_distance = distance

      i += 1

    # Make sure index is indexiable
    assert close_index < results[1]

    # Now that we have the closest moment, calculate sqrt(m2^2+m3^2)
    return math.sqrt(results[11][close_index]**2 + results[12][close_index]**2)


  def filter_feasable(self,dirs):
    '''
    Filters the set of dirs passed in to check that the beam can support a robot
    + beam load if the robot were to walk in the specified direction to the
    very tip of the beam.
    This function is only ever called if an analysis model exists.

    Additionally, this function stores information on the beams that need to be 
    repaired. This is stored in self.memory['broken'], which is originally set
    to none.
    '''
    # Sanity check
    assert self.model.GetModelIsLocked()

    results = {}
    # If at a joint, cycle through possible directions and check that the beams
    # meet the joint_limit. If they do, keep them. If not, discard them.
    if self.__at_joint():
      for name, directions in dirs.items():
        moment = self.get_moment(name)
        # If the name is our beam, do a structural check instead of a joint check
        if ((self.beam.name == name and 
          moment < construction.beam['beam_limit']) or (moment < 
          construction.beam['joint_limit'])):
          results[name] = directions
        # Add beam to broken
        else:
          beam = self.structure.get_beam(name,self.location)
          self.memory['broken'].append((beam,moment))


    # Not at joint, so check own beam
    moment = self.get_moment(self.beam.name)
    if moment < construction.beam['beam_limit']:
      results = dirs
    # Add the beam to the broken
    else:
      self.memory['broken'].append((self.beam,moment))

    # For debugging purpose
    if dirs == {}:
      pdb.set_trace()

    return results

  def get_direction(self):
    ''' 
    Figures out which direction to move in. This means that if the robot is 
    carrying a beam, it wants to move upwards. If it is not, it wants to move 
    downwards. So basically the direction is picked by filtering by the 
    z-component
    '''
    # Get all the possible directions, as normal
    info = self.get_directions_info()

    # Filter out directions which are unfeasable
    if self.model.GetModelIsLocked():
      feasable_directions = self.filter_feasable(info['directions'])
    else:
      feasable_directions = info['directions']

    # Now filter on based where you want to go
    directions = self.filter_directions(feasable_directions)

    # This will only occur if no direction takes us where we want to go. If 
    # that's the case, then just a pick a random direction to go on and run the
    # routine for when no directions are available.
    if directions == {}:
      # No direction takes us exactly in the way we want to go, so check if we
      # might need to construct up or might want to repair
      self.no_available_direction()
      beam_name, direction = self.elect_direction(feasable_directions)

    # Otherwise we do have a set of directions taking us in the right place, so 
    # randomly pick any of them. We will change this later based on the analysis
    else:
      beam_name, direction = self.elect_direction(directions)

    return {  'beam'      : info['box'][beam_name],
              'direction' : direction }

  def wander(self):
    '''    
    When a robot is not on a structure, it wanders. The wandering in the working
    class works as follows. The robot moves around randomly with the following 
    restrictions:
      The robot moves towards the home location if it has no beams and 
        the home location is detected nearby.
      Otherwise, if it has beams for construction, it moves toward the base 
      specified construction site. If it finds another beam nearby, it has a 
      tendency to climb that beam instead.
    '''
    # Check to see if robot is at home location and has no beams
    if self.at_home() and self.num_beams == 0 :
      self.pickup_beams()

    # If we have no beams, set the ground direction to home
    if self.num_beams == 0:
      self.ground_direction = helpers.make_vector(self.location,
        construction.home)

    # Find nearby beams to climb on
    result = self.ground()
    if result == None:
      direction = self.get_ground_direction()
      new_location = helpers.sum_vectors(self.location,helpers.scale(self.step,
        helpers.make_unit(direction)))
      self.change_location_local(new_location)
    else:
      dist, close_beam, direction = (result['distance'], result['beam'],
        result['direction'])
      # If the beam is within steping distance, just jump on it
      if self.num_beams > 0 and dist <= self.step:
        # Set the ground direction to None (so we walk randomly if we do get off
        # the beam again)
        self.ground_direction = None

        # Then move on the beam
        self.move(direction, close_beam)

      # If we can "detect" a beam, change the ground direction to approach it
      elif self.num_beams > 0 and dist <= variables.local_radius:
        self.ground_direction = direction
        new_location = helpers.sum_vectors(self.location, helpers.scale(
          self.step,helpers.make_unit(direction)))
        self.change_location_local(new_location)
      else:
        direction = self.get_ground_direction()
        new_location = helpers.sum_vectors(self.location,helpers.scale(
          self.step,helpers.make_unit(direction)))
        self.change_location_local(new_location)

  def addbeam(self,p1,p2):
    '''
    Adds the beam to the SAP program and to the Python Structure. Might have to 
    add joints for the intersections here in the future too. Removes the beam 
    from the robot.
    '''
    def addpoint(p): 
      '''
      Adds a point object to our model. The object is retrained in all 
      directions if on the ground (including rotational and translational 
      motion. Returns the name of the added point.
      '''
      # Add to SAP Program
      name = self.program.point_objects.addcartesian(p)
      # Check Coordinates
      if helpers.compare(p[2], 0):
        DOF = (True,True,True,True,True,True)
        if self.program.point_objects.restraint(name,DOF):
          return name
        else:
          print("Something went wrong adding ground point {}.".format(str(p)))
      else:
        return name

    # Add points to SAP Program
    p1_name, p2_name = addpoint(p1), addpoint(p2)
    name = self.program.frame_objects.add(p1_name,p2_name,
      propName=variables.frame_property_name)

    # Get rid of one beam
    self.discard_beams()

    # Successfully added to at least one box
    if self.structure.add_beam(p1,p2,name) > 0:
      box = self.structure.get_box(self.location)
      try:
        beam = box[name]
      except IndexError:
        print("Failed in addbeam. Adding beam {} at points {} and {} didn't \
          work.".format(name,str(p1),str(p2)))
        return False
      # Cycle through the joints and add the necessary points
      for coord in beam.joints:
        if coord != p1 and coord != p2:
          added = addpoint(coord)
      return True
    else:
      return False

  def build(self):
    '''
    This functions sets down a beam. This means it "wiggles" it around in the 
    air until it finds a connection (programatically, it just finds the 
    connection which makes the smallest angle). Returns false if something went 
    wrong, true otherwise.
    '''
    # Sanitiy check
    assert (self.num_beams > 0)

    # This is the i-end of the beam being placed. We pivot about this
    pivot = self.location

    # This is the j-end of the beam (if directly vertical)
    vertical_point = helpers.sum_vectors(self.location,(0,0,
      variables.beam_length))

    def check(i,j):
      '''
      Checks the endpoints and returns two that don't already exist in the 
      structure. If they do already exist, then it returns two endpoints that 
      don't. It does this by changing the j-endpoint. This function also takes 
      into account making sure that the returned value is still within the 
      robot's tendency to build up. (ie, it does not return a beam which would 
      build below the limit angle_constraint)
      '''
      # There is already a beam here, so let's move our current beam slightly to
      # some side
      if not self.structure.available(i,j):
        limit = (math.tan(math.radians(construction.beam['angle_constraint'])) *
         construction.beam['length'] / 3)
        return check(i,(random.uniform(-1* limit, limit),random.uniform(
          -1 * limit,limit), j[2]))
      else:
        # Calculate the actual endpoint of the beam (now that we now direction 
        # vector)
        unit_direction = helpers.make_unit(helpers.make_vector(i,j))
        j = helpers.sum_vectors(i,helpers.scale(variables.beam_length,
          unit_direction))
        return i,j


    # We place it here in order to have access to the pivot and to the vertical 
    # point
    def add_ratios(box,dictionary):
      '''
      Returns the 'verticality' that the beams in the box allow according to 
      distance. It also calculates the ratio according to the intersection 
      points of the beam with the sphere. 
      '''
      for name in box:
        # Ignore the beam you're on.
        if self.beam == None or self.beam.name != name:
          beam = box[name]
          # Get the closest points between the vertical and the beam
          points = helpers.closest_points(beam.endpoints,(pivot,vertical_point))
          if points != None:
            # Endpoints
            e1,e2 = points
            # Let's do a sanity check. The shortest distance should have no 
            # change in z
            assert helpers.compare(e1[2],e2[2])
            # If we can actually reach the second point from vertical
            if helpers.distance(pivot,e2) <= variables.beam_length:
              # Distance between the two endpoints
              dist = helpers.distance(e1,e2)
              if dist != 0:
                # Change in z from vertical to one of the two poitns (we already
                # asserted their z value to be equal)
                delta_z = abs(e1[2] - vertical_point[2])
                ratio = dist / delta_z
                # Check to see if in the dictionary. If it is, associate point 
                # with ratio
                if e2 in dictionary:
                  assert helpers.compare(dictionary[e2],ratio)
                else:
                  dictionary[e2] = ratio

          # Get the points at which the beam intersects the sphere created by 
          # the vertical beam      
          sphere_points = helpers.sphere_intersection(beam.endpoints,pivot,
            variables.beam_length)
          if sphere_points != None:
            # Cycle through intersection points (really, should be two, though 
            # it is possible for it to be one, in
            # which case, we would have already taken care of this). Either way,
            # we just cycle
            for point in sphere_points:
              # The point is higher above.This way the robot only ever builds up
              if point[2] >= pivot[2]:
                projection = helpers.correct(pivot,vertical_point,point)
                # Sanity check
                assert helpers.compare(projection[2],point[2])

                dist = helpers.distance(projection,point)
                delta_z = abs(point[2] - vertical_point[2])
                ratio = dist / delta_z
                if point in dictionary:
                  assert hlpers.compare(dictionary[point],ratio)
                else:
                  dictionary[point] = ratio

      return dictionary

    # get all beams nearby (ie, all the beams in the current box and possible 
    # those further above)
    local_box = self.structure.get_box(self.location)
    top_box = self.structure.get_box(vertical_point)
    constraining_ratio = math.tan(math.radians(
      construction.beam['angle_constraint']))
    ratios = {}

    '''
    Ratios contains the ratio dist / delta_z where dist is the shortest distance
    from the vertical beam segment to a beam nearby and delta_z is the 
    z-component change from the pivot point to the intersection point. Here, we 
    add to ratios those that arise from the intersection points of the beams 
    with the sphere. The dictionary is indexed by the point, and each point is 
    associated with one ratio
    '''
    ratios = add_ratios(local_box,add_ratios(top_box,ratios))
    default_endpoint = helpers.sum_vectors(pivot,helpers.scale(
      variables.beam_length,
      helpers.make_unit(construction.beam['vertical_dir_set'])))

    # Sort the ratios we have so we can cycle through them
    sorted_ratios = sorted(ratios.items(), key = operator.itemgetter(1))

    # Cycle through the sorted ratios until we find one which we haven't 
    # constructed or we run out of suitable ones.
    for coord, ratio in sorted_ratios:

      # If the smallest ratio is larger than what we've specified as the limit, 
      # then build as the default endpoint
      if ratio > constraining_ratio:
        i,j = check(pivot, coord)
        return self.addbeam(i,j)

      # The beam doesn't exist, so build it
      elif self.structure.available(pivot,coord):
        unit_direction = helpers.make_unit(helpers.make_vector(pivot,coord))
        endpoint = helpers.sum_vectors(pivot,helpers.scale(
          variables.beam_length,unit_direction))
        return self.addbeam(pivot,endpoint)
      # Beam exist, so pass it
      else:
        pass

    # If we get to this point, we have already built all possible ratios, so 
    # just stick something up
    disturbance = helpers.make_unit((random.uniform(-12,12),
      random.uniform(-12,12),random.uniform(-12,12)))
    default_endpoint = default_endpoint if random.randint(0,10) == 1 else (
      helpers.sum_vectors(default_endpoint,disturbance))
    i, j = check(pivot, default_endpoint)

    return self.addbeam(i,j)

  def construct(self):
    '''
    Decides whether the local conditions dictate we should build (in which case)
    ''' 
    if ((self.at_site()) and not self.memory['built'] and 
      self.num_beams > 0):
      self.memory['built'] = True
      self.memory['constructed'] += 1
      return True
    else:
      self.memory['built'] = False
      return False