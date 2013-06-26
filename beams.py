from collections import namedtuple
import helpers

Coord = namedtuple("Coordinates", ["x", "y", "z"])
EndPoints = namedtuple("Endpoints", ["i","j"])

class Beam:
  def __init__(self, name, endpoints):
    self.endpoints = EndPoints(i=endpoints[0], j=endpoints[1])
    self.joints = {}
    self.name = name
    self.weight = variables.beam_weight

  def addjoint(self, coord, beam):
    '''
    Adds a joint (at the specified coordinate), to the beam itself. The beam variable
    defines the name of the beam which crosses this one at the joint
    '''
    # Verify that the coordinate is on the beam based on endpoints
    if not helpers.on_line(self.endpoints.i, self.endpoints.j, coord):
      return False

    else:
      coord = Coord(x=coord[0],y=coord[1],z=coord[2])
      if coord in self.joints:
        # Make sure we only keep track of the beam once (no multiple same name beams per coord)
        if beam not in self.joints[coord]:
          self.joints[coord].append(beam)
      else:
        self.joints[coord] = [beam]

      return True

  def removejoint(self,coord, beam):
    '''
    Removes a specified joint from this beam. Returns whether or not the removal
    was successful.
    '''
    coord = Coord(x=coord[0],y=coord[1],z=coord[2])
    # The joint is not on the beam
    if not coord in self.joints:
      return False

    else:
      # The beam is not at this joint
      if not beam in self.joints[coord]:
        return False
      else:
        self.joints[coord].remove(beam)

        # remove the coordinate if there are no beams there
        if self.joints[coord] == []:
          self.joints.pop(coord, None)
        return True