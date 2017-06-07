#!/usr/bin/env python3

from collections import OrderedDict
from sklearn.cluster import KMeans
from copy import deepcopy, copy
from itertools import permutations
from math import atan2, cos, degrees, exp, factorial, radians, sin, sqrt, ceil
from pprint import pformat
import colorsys
import json
import logging
import sys

log = logging.getLogger(__name__)

# Calculating color distances is expensive in terms of CPU so
# cache the results
dcache = {}
SIDES_COUNT = 6


# Not used, I experimented with this for kmeans clustering distance
def get_euclidean_rgb_distance(rgb1, rgb2):
    return sqrt(sum([(a - b) ** 2 for a, b in zip(rgb1, rgb2)]))


# Not used, I experimented with this for kmeans clustering distance
def get_euclidean_lab_distance(rgb1, rgb2):
    """
    http://www.w3resource.com/python-exercises/math/python-math-exercise-79.php

    In mathematics, the Euclidean distance or Euclidean metric is the "ordinary"
    (i.e. straight-line) distance between two points in Euclidean space. With this
    distance, Euclidean space becomes a metric space. The associated norm is called
    the Euclidean norm.
    """
    lab1 = rgb2lab(rgb1)
    lab2 = rgb2lab(rgb2)
    lab1_tuple = (lab1.L, lab1.a, lab1.b)
    lab2_tuple = (lab2.L, lab2.a, lab2.b)
    return sqrt(sum([(a - b) ** 2 for a, b in zip(lab1_tuple, lab2_tuple)]))


class ClusterSquare(object):

    def __init__(self, index, rgb):
        self.index = index
        self.rgb = rgb
        self.distance_to_anchor = 0

    def __str__(self):
        if self.index:
            return str(self.index)
        else:
            return str(self.rgb)

    def __lt__(self, other):
        return self.index < other.index


class Cluster(object):

    def __init__(self, anchor):
        self.anchor = anchor
        self.members = []
        self.empty_count = 0

    def __str__(self):
        return "cluster %s" % self.anchor

    def calculate_distances(self, data_points, use_sort):
        self.distances = []
        has_143 = False

        for square in data_points:
            lab1 = rgb2lab(square.rgb)
            lab2 = rgb2lab(self.anchor.rgb)
            distance = delta_e_cie2000(lab1, lab2)
            self.distances.append((distance, square))

            if square.index == 143:
                has_143 = True

        if use_sort:
            self.distances = sorted(self.distances)
            # dwalton
            if self.anchor.index in (63, 13) and has_143:
                for (distance, square) in self.distances:
                    log.warning("%s to %s is %d" % (self, square, distance))


def assign_points(data_points, anchors, squares_per_side):
    """
    For each anchor color find the squares_per_side-1 entries in data_points with the lowest distance
    """
    clusters = {}
    all_distances = []

    for anchor in anchors:
        clusters[anchor] = Cluster(anchor)
        cluster = clusters[anchor]
        cluster.calculate_distances(data_points, True)

        for (distance, square) in cluster.distances:
            all_distances.append((distance, square, cluster))

    all_distances = sorted(all_distances)
    used = []

    for (distance, square, cluster) in all_distances:
        if len(cluster.members) < squares_per_side and square not in used:
            cluster.members.append(square)
            used.append(square)

    assignments = []
    for anchor in anchors:
        assigments_for_cluster = []
        cluster = clusters[anchor]

        for cluster_square in cluster.members:
            assigments_for_cluster.append(cluster_square)
        assignments.append(assigments_for_cluster)

    return assignments


def kmeans_sort_colors_static_anchors(colors):
    """
    colors is an OrderedDict where the key is the square index and the value a RGB tuple
    Started from https://github.com/stuntgoat/kmeans/blob/master/kmeans.py
    """
    #assert len(anchor_square_indexes) == SIDES_COUNT, "The are %d anchor_square_indexes, there must be %s" % (len(anchor_square_indexes), SIDES_COUNT)
    #assert len(colors.keys()) % SIDES_COUNT == 0, "The are %d color entries, must be divisible by %s" % (len(colors.keys()), SIDES_COUNT)

    dataset = []
    anchors = []
    squares_per_side = int(len(colors.keys())/SIDES_COUNT)

    for (index, (square_index, rgb)) in enumerate(colors.items()):
        square = ClusterSquare(square_index, rgb)
        dataset.append(square)

        if index < SIDES_COUNT:
            anchors.append(square)

    #assert len(anchors) == SIDES_COUNT, "The are %d anchors, there must be %s" % (len(anchors), SIDES_COUNT)
    return assign_points(dataset, anchors, squares_per_side)


def kmeans_sort_colors_dynamic_anchors(colors):
    """
    'colors is a list of RGB tuples, sort them into SIDES_COUNT buckets
    """
    clt = KMeans(n_clusters=SIDES_COUNT)
    clt.fit(copy(colors))

    # all_buckets will be a list of list
    all_buckets = []

    for target_cluster in range(SIDES_COUNT):
        current_bucket = []

        for (index, cluster) in enumerate(clt.labels_):
            if cluster == target_cluster:
                current_bucket.append(colors[index])
        all_buckets.append(current_bucket)

    return all_buckets


def get_cube_layout(size):
    """
    Example: size is 3, return the following string:

              01 02 03
              04 05 06
              07 08 09

    10 11 12  19 20 21  28 29 30  37 38 39
    13 14 15  22 23 24  31 32 33  40 41 42
    16 17 18  25 26 27  34 35 36  43 44 45

              46 47 48
              49 50 51
              52 53 54
    """
    result = []

    squares = (size * size) * 6
    square_index = 1

    if squares >= 1000:
        digits_size = 4
        digits_format = "%04d "
    elif squares >= 100:
        digits_size = 3
        digits_format = "%03d "
    else:
        digits_size = 2
        digits_format = "%02d "

    indent = ((digits_size * size) + size + 1) * ' '
    rows = size * 3

    for row in range(1, rows + 1):
        line = []

        if row <= size:
            line.append(indent)
            for col in range(1, size + 1):
                line.append(digits_format % square_index)
                square_index += 1

        elif row > rows - size:
            line.append(indent)
            for col in range(1, size + 1):
                line.append(digits_format % square_index)
                square_index += 1

        else:
            init_square_index = square_index
            last_col = size * 4
            for col in range(1, last_col + 1):
                line.append(digits_format % square_index)

                if col == last_col:
                    square_index += 1
                elif col % size == 0:
                    square_index += (size * size) - size + 1
                    line.append(' ')
                else:
                    square_index += 1

            if row % size:
                square_index = init_square_index + size

        result.append(''.join(line))

        if row == size or row == rows - size:
            result.append('')
    return '\n'.join(result)


def get_important_square_indexes(size):
    squares_per_side = size * size
    min_square = 1
    max_square = squares_per_side * 6
    first_squares = []
    last_squares = []

    for index in range(1, max_square + 1):
        if (index - 1) % squares_per_side == 0:
            first_squares.append(index)
        elif index % squares_per_side == 0:
            last_squares.append(index)

    last_UBD_squares = (last_squares[0], last_squares[4], last_squares[5])
    #log.info("first    squares: %s" % pformat(first_squares))
    #log.info("last     squares: %s" % pformat(last_squares))
    #log.info("last UBD squares: %s" % pformat(last_UBD_squares))
    return (first_squares, last_squares, last_UBD_squares)


class LabColor(object):

    def __init__(self, L, a, b, red, green, blue):
        self.L = L
        self.a = a
        self.b = b
        self.red = red
        self.green = green
        self.blue = blue
        self.name = None

    def __str__(self):
        return ("Lab (%s, %s, %s)" % (self.L, self.a, self.b))

    def __lt__(self, other):
        return self.name < other.name


def rgb2lab(inputColor):
    """
    http://stackoverflow.com/questions/13405956/convert-an-image-rgb-lab-with-python
    """
    RGB = [0, 0, 0]
    XYZ = [0, 0, 0]

    for (num, value) in enumerate(inputColor):
        if value > 0.04045:
            value = pow(((value + 0.055) / 1.055), 2.4)
        else:
            value = value / 12.92

        RGB[num] = value * 100.0

    # http://www.brucelindbloom.com/index.html?Eqn_RGB_XYZ_Matrix.html
    # sRGB
    # 0.4124564  0.3575761  0.1804375
    # 0.2126729  0.7151522  0.0721750
    # 0.0193339  0.1191920  0.9503041
    X = (RGB[0] * 0.4124564) + (RGB[1] * 0.3575761) + (RGB[2] * 0.1804375)
    Y = (RGB[0] * 0.2126729) + (RGB[1] * 0.7151522) + (RGB[2] * 0.0721750)
    Z = (RGB[0] * 0.0193339) + (RGB[1] * 0.1191920) + (RGB[2] * 0.9503041)

    XYZ[0] = X / 95.047   # ref_X =  95.047
    XYZ[1] = Y / 100.0    # ref_Y = 100.000
    XYZ[2] = Z / 108.883  # ref_Z = 108.883

    for (num, value) in enumerate(XYZ):
        if value > 0.008856:
            value = pow(value, (1.0 / 3.0))
        else:
            value = (7.787 * value) + (16 / 116.0)

        XYZ[num] = value

    L = (116.0 * XYZ[1]) - 16
    a = 500.0 * (XYZ[0] - XYZ[1])
    b = 200.0 * (XYZ[1] - XYZ[2])

    L = round(L, 4)
    a = round(a, 4)
    b = round(b, 4)

    (red, green, blue) = inputColor
    return LabColor(L, a, b, red, green, blue)


def delta_e_cie2000(lab1, lab2):
    """
    Ported from this php implementation
    https://github.com/renasboy/php-color-difference/blob/master/lib/color_difference.class.php
    """
    l1 = lab1.L
    a1 = lab1.a
    b1 = lab1.b

    l2 = lab2.L
    a2 = lab2.a
    b2 = lab2.b

    avg_lp = (l1 + l2) / 2.0
    c1 = sqrt(pow(a1, 2) + pow(b1, 2))
    c2 = sqrt(pow(a2, 2) + pow(b2, 2))
    avg_c = (c1 + c2) / 2.0
    g = (1 - sqrt(pow(avg_c, 7) / (pow(avg_c, 7) + pow(25, 7)))) / 2.0
    a1p = a1 * (1 + g)
    a2p = a2 * (1 + g)
    c1p = sqrt(pow(a1p, 2) + pow(b1, 2))
    c2p = sqrt(pow(a2p, 2) + pow(b2, 2))
    avg_cp = (c1p + c2p) / 2.0
    h1p = degrees(atan2(b1, a1p))

    if h1p < 0:
        h1p += 360

    h2p = degrees(atan2(b2, a2p))

    if h2p < 0:
        h2p += 360

    if abs(h1p - h2p) > 180:
        avg_hp = (h1p + h2p + 360) / 2.0
    else:
        avg_hp = (h1p + h2p) / 2.0

    t = (1 - 0.17 * cos(radians(avg_hp - 30)) +
         0.24 * cos(radians(2 * avg_hp)) +
         0.32 * cos(radians(3 * avg_hp + 6)) - 0.2 * cos(radians(4 * avg_hp - 63)))
    delta_hp = h2p - h1p

    if abs(delta_hp) > 180:
        if h2p <= h1p:
            delta_hp += 360
        else:
            delta_hp -= 360

    delta_lp = l2 - l1
    delta_cp = c2p - c1p
    delta_hp = 2 * sqrt(c1p * c2p) * sin(radians(delta_hp) / 2.0)
    s_l = 1 + ((0.015 * pow(avg_lp - 50, 2)) / sqrt(20 + pow(avg_lp - 50, 2)))
    s_c = 1 + 0.045 * avg_cp
    s_h = 1 + 0.015 * avg_cp * t

    delta_ro = 30 * exp(-(pow((avg_hp - 275) / 25.0, 2)))
    r_c = 2 * sqrt(pow(avg_cp, 7) / (pow(avg_cp, 7) + pow(25, 7)))
    r_t = -r_c * sin(2 * radians(delta_ro))
    kl = 1.0
    kc = 1.0
    kh = 1.0
    delta_e = sqrt(pow(delta_lp / (s_l * kl), 2) +
                   pow(delta_cp / (s_c * kc), 2) +
                   pow(delta_hp / (s_h * kh), 2) +
                   r_t * (delta_cp / (s_c * kc)) * (delta_hp / (s_h * kh)))

    return delta_e


def get_color_distance(c1, c2):
    try:
        return dcache[(c1, c2)]
    except KeyError:
        try:
            return dcache[(c2, c1)]
        except KeyError:
            distance = delta_e_cie2000(c1, c2)
            dcache[(c1, c2)] = distance
            return distance


def hex_to_rgb(rgb_string):
    """
    Takes #112233 and returns the RGB values in decimal
    """
    if rgb_string.startswith('#'):
        rgb_string = rgb_string[1:]

    red = int(rgb_string[0:2], 16)
    green = int(rgb_string[2:4], 16)
    blue = int(rgb_string[4:6], 16)
    return (red, green, blue)


def hashtag_rgb_to_labcolor(rgb_string):
    (red, green, blue) = hex_to_rgb(rgb_string)
    return rgb2lab((red, green, blue))


class Square(object):

    def __init__(self, side, cube, position, red, green, blue):
        self.cube = cube
        self.side = side
        self.position = position
        self.rgb = (red, green, blue)
        self.red = red
        self.green = green
        self.blue = blue
        self.rawcolor = rgb2lab((red, green, blue))
        self.color = None
        self.color_name = None
        self.anchor_square = None

    def __str__(self):
        return "%s%d" % (self.side, self.position)

    def __lt__(self, other):
        return self.position < other.position

    def find_closest_match(self, crayon_box, debug=False, set_color=True):
        cie_data = []

        for (color_name, color_obj) in crayon_box.items():
            distance = get_color_distance(self.rawcolor, color_obj)
            cie_data.append((distance, color_name, color_obj))
        cie_data = sorted(cie_data)

        distance = cie_data[0][0]
        color_name = cie_data[0][1]
        color_obj = cie_data[0][2]

        if set_color:
            self.distance = distance
            self.color_name = color_name
            self.color = color_obj

        if debug:
            log.info("%s is %s" % (self, color_obj))

        return (color_obj, distance)


def get_orbit_id(cube_size, edge_index):
    orbit = None

    if cube_size == 3 or cube_size == 4:
        orbit = 0

    elif cube_size == 5:

        if edge_index == 0 or edge_index == 2:
            orbit = 0
        else:
            orbit = 1

    elif cube_size == 6:

        if edge_index == 0 or edge_index == 3:
            orbit = 0
        else:
            orbit = 1

    else:
        raise Exception("Add orbit support for %dx%dx%d cubes" % (cube_size, cube_size, cube_size))

    return orbit


class Edge(object):

    def __init__(self, cube, pos1, pos2, edge_index):
        self.valid = False
        self.square1 = cube.get_square(pos1)
        self.square2 = cube.get_square(pos2)
        self.cube = cube
        self.dcache = {}
        self.orbit_id = get_orbit_id(self.cube.width, edge_index)

    def __str__(self):
        result = "%s%d/%s%d" %\
            (self.square1.side, self.square1.position,
             self.square2.side, self.square2.position)

        if self.square1.color and self.square2.color:
            result += " %s/%s" % (self.square1.color.name, self.square2.color.name)
        elif self.square1.color and not self.square2.color:
            result += " %s/None" % self.square1.color.name
        elif not self.square1.color and self.square2.color:
            result += " None/%s" % self.square2.color.name

        return result

    def __lt__(self, other):
        return 0

    def colors_match(self, colorA, colorB):
        if (colorA in (self.square1.color, self.square2.color) and
            colorB in (self.square1.color, self.square2.color)):
            return True
        return False

    def _get_color_distances(self, colorA, colorB):
        distanceAB = (get_color_distance(self.square1.rawcolor, colorA) +
                      get_color_distance(self.square2.rawcolor, colorB))

        distanceBA = (get_color_distance(self.square1.rawcolor, colorB) +
                      get_color_distance(self.square2.rawcolor, colorA))

        return (distanceAB, distanceBA)

    def color_distance(self, colorA, colorB):
        """
        Given two colors, return our total color distance
        """
        try:
            return self.dcache[(colorA, colorB)]
        except KeyError:
            value = min(self._get_color_distances(colorA, colorB))
            self.dcache[(colorA, colorB)] = value
            return value

    def update_colors(self, colorA, colorB):
        (distanceAB, distanceBA) = self._get_color_distances(colorA, colorB)

        if distanceAB < distanceBA:
            self.square1.color = colorA
            self.square1.color_name = colorA.name
            self.square2.color = colorB
            self.square2.color_name = colorB.name
        else:
            self.square1.color = colorB
            self.square1.color_name = colorB.name
            self.square2.color = colorA
            self.square2.color_name = colorA.name

    def validate(self):

        if self.square1.color == self.square2.color:
            self.valid = False
            log.info("%s is an invalid edge (duplicate colors)" % self)
        elif ((self.square1.color, self.square2.color) in self.cube.valid_edges or
              (self.square2.color, self.square1.color) in self.cube.valid_edges):
            self.valid = True
        else:
            self.valid = False
            log.info("%s is an invalid edge" % self)


class Corner(object):

    def __init__(self, cube, pos1, pos2, pos3):
        self.valid = False
        self.square1 = cube.get_square(pos1)
        self.square2 = cube.get_square(pos2)
        self.square3 = cube.get_square(pos3)
        self.cube = cube
        self.dcache = {}

    def __str__(self):
        if self.square1.color and self.square2.color and self.square3.color:
            return "%s%d/%s%d/%s%d %s/%s/%s" %\
                (self.square1.side, self.square1.position,
                 self.square2.side, self.square2.position,
                 self.square3.side, self.square3.position,
                 self.square1.color.name, self.square2.color.name, self.square3.color.name)
        else:
            return "%s%d/%s%d/%s%d" %\
                (self.square1.side, self.square1.position,
                 self.square2.side, self.square2.position,
                 self.square3.side, self.square3.position)

    def __lt__(self, other):
        return 0

    def colors_match(self, colorA, colorB, colorC):
        if (colorA in (self.square1.color, self.square2.color, self.square3.color) and
            colorB in (self.square1.color, self.square2.color, self.square3.color) and
            colorC in (self.square1.color, self.square2.color, self.square3.color)):
            return True
        return False

    def _get_color_distances(self, colorA, colorB, colorC):
        distanceABC = (get_color_distance(self.square1.rawcolor, colorA) +
                       get_color_distance(self.square2.rawcolor, colorB) +
                       get_color_distance(self.square3.rawcolor, colorC))

        distanceACB = (get_color_distance(self.square1.rawcolor, colorA) +
                       get_color_distance(self.square2.rawcolor, colorC) +
                       get_color_distance(self.square3.rawcolor, colorB))

        distanceCAB = (get_color_distance(self.square1.rawcolor, colorC) +
                       get_color_distance(self.square2.rawcolor, colorA) +
                       get_color_distance(self.square3.rawcolor, colorB))

        distanceCBA = (get_color_distance(self.square1.rawcolor, colorC) +
                       get_color_distance(self.square2.rawcolor, colorB) +
                       get_color_distance(self.square3.rawcolor, colorA))

        distanceBCA = (get_color_distance(self.square1.rawcolor, colorB) +
                       get_color_distance(self.square2.rawcolor, colorC) +
                       get_color_distance(self.square3.rawcolor, colorA))

        distanceBAC = (get_color_distance(self.square1.rawcolor, colorB) +
                       get_color_distance(self.square2.rawcolor, colorA) +
                       get_color_distance(self.square3.rawcolor, colorC))

        return (distanceABC, distanceACB, distanceCAB, distanceCBA, distanceBCA, distanceBAC)

    def color_distance(self, colorA, colorB, colorC):
        """
        Given three colors, return our total color distance
        """
        try:
            return self.dcache[(colorA, colorB, colorC)]
        except KeyError:
            value = min(self._get_color_distances(colorA, colorB, colorC))
            self.dcache[(colorA, colorB, colorC)] = value
            return value

    def update_colors(self, colorA, colorB, colorC):
        (distanceABC, distanceACB, distanceCAB, distanceCBA, distanceBCA, distanceBAC) = self._get_color_distances(colorA, colorB, colorC)
        min_distance = min(distanceABC, distanceACB, distanceCAB, distanceCBA, distanceBCA, distanceBAC)

        log.debug("%s vs %s/%s/%s, distanceABC %s, distanceACB %s, distanceCAB %s, distanceCBA %s, distanceBCA %s, distanceBAC %s, min %s" %
                    (self, colorA.name, colorB.name, colorC.name,
                    distanceABC, distanceACB,
                    distanceCAB, distanceCBA,
                    distanceBCA, distanceBAC, min_distance))

        if min_distance == distanceABC:
            self.square1.color = colorA
            self.square1.color_name = colorA.name
            self.square2.color = colorB
            self.square2.color_name = colorB.name
            self.square3.color = colorC
            self.square3.color_name = colorC.name

        elif min_distance == distanceACB:
            self.square1.color = colorA
            self.square1.color_name = colorA.name
            self.square2.color = colorC
            self.square2.color_name = colorC.name
            self.square3.color = colorB
            self.square3.color_name = colorB.name

        elif min_distance == distanceCAB:
            self.square1.color = colorC
            self.square1.color_name = colorC.name
            self.square2.color = colorA
            self.square2.color_name = colorA.name
            self.square3.color = colorB
            self.square3.color_name = colorB.name

        elif min_distance == distanceCBA:
            self.square1.color = colorC
            self.square1.color_name = colorC.name
            self.square2.color = colorB
            self.square2.color_name = colorB.name
            self.square3.color = colorA
            self.square3.color_name = colorA.name

        elif min_distance == distanceBCA:
            self.square1.color = colorB
            self.square1.color_name = colorB.name
            self.square2.color = colorC
            self.square2.color_name = colorC.name
            self.square3.color = colorA
            self.square3.color_name = colorA.name

        elif min_distance == distanceBAC:
            self.square1.color = colorB
            self.square1.color_name = colorB.name
            self.square2.color = colorA
            self.square2.color_name = colorA.name
            self.square3.color = colorC
            self.square3.color_name = colorC.name

        else:
            raise Exception("We should not be here")

    def validate(self):

        if (self.square1.color == self.square2.color or
            self.square1.color == self.square3.color or
                self.square2.color == self.square3.color):
            self.valid = False
            log.info("%s is an invalid edge (duplicate colors)" % self)
        elif ((self.square1.color, self.square2.color, self.square3.color) in self.cube.valid_corners or
              (self.square1.color, self.square3.color, self.square2.color) in self.cube.valid_corners or
              (self.square2.color, self.square1.color, self.square3.color) in self.cube.valid_corners or
              (self.square2.color, self.square3.color, self.square1.color) in self.cube.valid_corners or
              (self.square3.color, self.square1.color, self.square2.color) in self.cube.valid_corners or
              (self.square3.color, self.square2.color, self.square1.color) in self.cube.valid_corners):
            self.valid = True
        else:
            self.valid = False
            log.info("%s (%s, %s, %s) is an invalid corner" %
                     (self, self.square1.color, self.square2.color, self.square3.color))



class CubeSide(object):

    def __init__(self, cube, width, name):
        self.cube = cube
        self.name = name  # U, L, etc
        self.color = None  # Will be the color of the anchor square
        self.squares = {}
        self.width = width
        self.squares_per_side = width * width
        self.center_squares = []
        self.edge_squares = []
        self.corner_squares = []

        if self.name == 'U':
            index = 0
        elif self.name == 'L':
            index = 1
        elif self.name == 'F':
            index = 2
        elif self.name == 'R':
            index = 3
        elif self.name == 'B':
            index = 4
        elif self.name == 'D':
            index = 5

        self.min_pos = (index * self.squares_per_side) + 1
        self.max_pos = (index * self.squares_per_side) + self.squares_per_side

        # If this is a cube of odd width (3x3x3) then define a mid_pos
        if self.width % 2 == 0:
            self.mid_pos = None
        else:
            self.mid_pos = (self.min_pos + self.max_pos) / 2

        self.corner_pos = (self.min_pos,
                           self.min_pos + self.width - 1,
                           self.max_pos - self.width + 1,
                           self.max_pos)
        self.edge_pos = []
        self.edge_north_pos = []
        self.edge_west_pos = []
        self.edge_south_pos = []
        self.edge_east_pos = []
        self.center_pos = []

        for position in range(self.min_pos, self.max_pos):
            if position in self.corner_pos:
                pass

            # Edges at the north
            elif position > self.corner_pos[0] and position < self.corner_pos[1]:
                self.edge_pos.append(position)
                self.edge_north_pos.append(position)

            # Edges at the south
            elif position > self.corner_pos[2] and position < self.corner_pos[3]:
                self.edge_pos.append(position)
                self.edge_south_pos.append(position)

            elif (position - 1) % self.width == 0:
                west_edge = position
                east_edge = west_edge + self.width - 1

                # Edges on the west
                self.edge_pos.append(west_edge)
                self.edge_west_pos.append(west_edge)

                # Edges on the east
                self.edge_pos.append(east_edge)
                self.edge_east_pos.append(east_edge)

                # Center squares
                for x in range(west_edge + 1, east_edge):
                    self.center_pos.append(x)

        log.info("Side %s, min/max %d/%d, edges %s, corners %s, centers %s" %
            (self.name, self.min_pos, self.max_pos,
             pformat(self.edge_pos),
             pformat(self.corner_pos),
             pformat(self.center_pos)))

    def __str__(self):
        return self.name

    def set_square(self, position, red, green, blue):
        self.squares[position] = Square(self, self.cube, position, red, green, blue)

        if position in self.center_pos:
            self.center_squares.append(self.squares[position])

        elif position in self.edge_pos:
            self.edge_squares.append(self.squares[position])

        elif position in self.corner_pos:
            self.corner_squares.append(self.squares[position])

        else:
            raise Exception('Could not determine egde vs corner vs center')


class RubiksColorSolverGeneric(object):

    def __init__(self, width):
        self.width = width
        self.height = width
        self.squares_per_side = self.width * self.width
        self.scan_data = {}
        self.orbits = int(ceil((self.width - 2) / 2.0))

        if self.width % 2 == 0:
            self.even = True
            self.odd = False
        else:
            self.even = False
            self.odd = True

        self.sides = {
            'U': CubeSide(self, self.width, 'U'),
            'L': CubeSide(self, self.width, 'L'),
            'F': CubeSide(self, self.width, 'F'),
            'R': CubeSide(self, self.width, 'R'),
            'B': CubeSide(self, self.width, 'B'),
            'D': CubeSide(self, self.width, 'D')
        }

        self.sideU = self.sides['U']
        self.sideL = self.sides['L']
        self.sideF = self.sides['F']
        self.sideR = self.sides['R']
        self.sideB = self.sides['B']
        self.sideD = self.sides['D']
        self.side_order = ('U', 'L', 'F', 'R', 'B', 'D')

        self.crayola_colors = {
            # Handy website for converting RGB tuples to hex
            # http://www.w3schools.com/colors/colors_converter.asp
            #
            # These are the RGB values as seen via a webcam
            #   white = (235, 254, 250)
            #   green = (20, 105, 74)
            #   yellow = (210, 208, 2)
            #   orange = (148, 53, 9)
            #   blue = (3, 40, 146)
            #   red = (104, 4, 2)
            #
            'Wh': hashtag_rgb_to_labcolor('#ebfefa'),
            'Gr': hashtag_rgb_to_labcolor('#14694a'),
            'Ye': hashtag_rgb_to_labcolor('#d2d002'),
            'OR': hashtag_rgb_to_labcolor('#943509'),
            'Bu': hashtag_rgb_to_labcolor('#032892'),
            'Rd': hashtag_rgb_to_labcolor('#680402')
        }
        self.crayon_box = deepcopy(self.crayola_colors)
        self.www_header()

    def www_header(self):
        """
        Write the <head> including css
        """
        side_margin = 10
        square_size = 40
        size = self.width # 3 for 3x3x3, etc

        with open('/tmp/rubiks-color-resolver.html', 'w') as fh:
            fh.write("""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<style>
div.clear {
    clear: both;
}

div.clear_left {
    clear: left;
}

div.side {
    margin: %dpx;
    float: left;
}

""" % side_margin)

            for x in range(1, size-1):
                fh.write("div.col%d,\n" % x)

            fh.write("""div.col%d {
    float: left;
}

div.col%d {
    margin-left: %dpx;
}
div#upper,
div#down {
    margin-left: %dpx;
}
""" % (size-1,
       size,
       (size - 1) * square_size,
       (size * square_size) + (size * side_margin)))

            fh.write("""
span.square {
    width: %dpx;
    height: %dpx;
    white-space-collapsing: discard;
    display: inline-block;
    color: black;
    font-weight: bold;
    line-height: %dpx;
    text-align: center;
}

div.square {
    width: %dpx;
    height: %dpx;
    color: black;
    font-weight: bold;
    line-height: %dpx;
    text-align: center;
}

div.square span {
  display:        inline-block;
  vertical-align: middle;
  line-height:    normal;
}

</style>
<title>CraneCuber</title>
</head>
<body>
""" % (square_size, square_size, square_size, square_size, square_size, square_size))

    def write_cube(self, desc, cube):
        """
        'cube' is a list of (R,G,B) tuples
        """
        col = 1
        squares_per_side = self.width * self.width
        min_square = 1
        max_square = squares_per_side * 6

        sides = ('upper', 'left', 'front', 'right', 'back', 'down')
        side_index = -1
        (first_squares, last_squares, last_UBD_squares) = get_important_square_indexes(self.width)

        with open('/tmp/rubiks-color-resolver.html', 'a') as fh:
            fh.write("<h1>%s</h1>\n" % desc)
            for index in range(1, max_square + 1):
                if index in first_squares:
                    side_index += 1
                    fh.write("<div class='side' id='%s'>\n" % sides[side_index])

                (red, green, blue) = cube[index]
                (H, S, V) = colorsys.rgb_to_hsv(float(red/255), float(green/255), float(blue/255))
                H = int(H * 360)
                S = int(S * 100)
                V = int(V * 100)
                lab = rgb2lab((red, green, blue))

                fh.write("    <div class='square col%d' title='RGB (%d, %d, %d) HSV (%d, %d, %d), Lab (%s, %s, %s)' style='background-color: #%02x%02x%02x;'><span>%02d</span></div>\n" %
                    (col,
                     red, green, blue,
                     H, S, V,
                     lab.L, lab.a, lab.b,
                     red, green, blue,
                     index))

                if index in last_squares:
                    fh.write("</div>\n")

                    if index in last_UBD_squares:
                        fh.write("<div class='clear'></div>\n")

                col += 1

                if col == self.width + 1:
                    col = 1

    def write_colors(self, desc, colors):
        with open('/tmp/rubiks-color-resolver.html', 'a') as fh:
            squares_per_side = int(len(colors)/6)
            fh.write("<h2>%s</h2>\n" % desc)
            fh.write("<div class='clear colors'>\n")

            for cluster_square_list in colors:
                for cluster_square in cluster_square_list:
                    (red, green, blue) = cluster_square.rgb

                    # to use python coloursys convertion we have to rescale to range 0-1
                    (H, S, V) = colorsys.rgb_to_hsv(float(red/255), float(green/255), float(blue/255))

                    # rescale H to 360 degrees and S, V to percent of 100%
                    H = int(H * 360)
                    S = int(S * 100)
                    V = int(V * 100)
                    lab = rgb2lab((red, green, blue))

                    fh.write("<span class='square' style='background-color:#%02x%02x%02x' title='RGB (%s, %s, %s), HSV (%s, %s, %s), Lab (%s, %s, %s) Distance %d'>%d</span>\n" %
                        (red, green, blue,
                         red, green, blue,
                         H, S, V,
                         lab.L, lab.a, lab.b,
                         cluster_square.distance_to_anchor,
                         cluster_square.index))

                fh.write("<br>")

            fh.write("</div>\n")
            log.info('\n\n')

    def www_footer(self):
        with open('/tmp/rubiks-color-resolver.html', 'a') as fh:
            fh.write("""
</body>
</html>
""")

    def get_side(self, position):
        """
        Given a position on the cube return the CubeSide object
        that contians that position
        """
        for side in self.sides.values():
            if position >= side.min_pos and position <= side.max_pos:
                return side
        raise Exception("Could not find side for %d" % position)

    def get_square(self, position):
        side = self.get_side(position)
        return side.squares[position]

    def enter_scan_data(self, scan_data):
        self.scan_data = scan_data
        cube = ['dummy',]

        for (position, (red, green, blue)) in sorted(self.scan_data.items()):
            position = int(position)
            side = self.get_side(position)
            side.set_square(position, red, green, blue)
            cube.append((red, green, blue))

        # write the input to the web page so we can reproduce bugs, etc just from the web page
        with open('/tmp/rubiks-color-resolver.html', 'a') as fh:
            fh.write("<h1>JSON Input</h1>\n")
            fh.write("<pre>%s</pre>\n" % json.dumps(scan_data))

        self.write_cube('Input RGB values', cube)

    def print_layout(self):
        log.info('\n' + get_cube_layout(self.width) + '\n')

    def print_cube(self):
        data = []
        for x in range(3 * self.height):
            data.append([])

        color_codes = {
          'OR': 90,
          'Rd': 91,
          'Gr': 92,
          'Ye': 93,
          'Bu': 94,
          'Wh': 97
        }

        for side_name in self.side_order:
            side = self.sides[side_name]

            if side_name == 'U':
                line_number = 0
                prefix = (' ' * self.width * 3) +  ' '
            elif side_name in ('L', 'F', 'R', 'B'):
                line_number = self.width
                prefix = ''
            else:
                line_number = self.width * 2
                prefix = (' ' * self.width * 3) +  ' '

            # rows
            for y in range(self.width):
                data[line_number].append(prefix)

                # cols
                for x in range(self.width):
                    color_name = side.squares[side.min_pos + (y * self.width) + x].color_name
                    color_code = color_codes.get(color_name)

                    if color_name is None:
                        color_code = 97
                        data[line_number].append('\033[%dmFo\033[0m' % color_code)
                    else:
                        data[line_number].append('\033[%dm%s\033[0m' % (color_code, color_name))
                line_number += 1

        output = []
        for row in data:
            output.append(' '.join(row))

        log.info("Cube\n\n%s\n" % '\n'.join(output))

    def cube_for_kociemba_strict(self):

        if self.sideU.mid_pos is not None:
            color_to_side_name = {}

            for side_name in self.side_order:
                side = self.sides[side_name]
                mid_square = side.squares[side.mid_pos]

                if mid_square.color_name in color_to_side_name:
                    log.info("color_to_side_name:\n%s" % pformat(color_to_side_name))
                    raise Exception("side %s with color %s, %s is already in color_to_side_name" %\
                        (side, mid_square.color_name, mid_square.color_name))
                color_to_side_name[mid_square.color_name] = side.name

        else:
            color_to_side_name = {
                'Wh' : 'U',
                'OR' : 'B',
                'Gr' : 'L',
                'Rd' : 'F',
                'Ye' : 'D',
                'Bu' : 'R'
            }

        data = []
        for side in (self.sideU, self.sideR, self.sideF, self.sideD, self.sideL, self.sideB):
            for x in range(side.min_pos, side.max_pos + 1):
                color_name = side.squares[x].color_name
                data.append(color_to_side_name[color_name])

        return data

    def cube_for_json(self):
        """
        Return a dictionary of the cube data so that we can json dump it
        """
        data = {}
        data['kociemba'] = ''.join(self.cube_for_kociemba_strict())
        data['sides'] = {}
        data['squares'] = {}
        color_to_side = {}

        html_color = {
            'Gr' : {'red' :   0, 'green' : 102, 'blue' : 0},
            'Bu' : {'red' :   0, 'green' :   0, 'blue' : 153},
            'OR' : {'red' : 255, 'green' : 102, 'blue' : 0},
            'Rd' : {'red' : 204, 'green' :   0, 'blue' : 0},
            'Wh' : {'red' : 255, 'green' : 255, 'blue' : 255},
            'Ye' : {'red' : 255, 'green' : 204, 'blue' : 0},
        }

        for side in self.sides.values():
            color_to_side[side.color] = side
            data['sides'][side.name] = {
                'colorName' : side.color_name,
                'colorScan' : {
                    'red'   : side.red,
                    'green' : side.green,
                    'blue'  : side.blue,
                },
                'colorHTML' : html_color[side.color_name]
            }

        for side in (self.sideU, self.sideR, self.sideF, self.sideD, self.sideL, self.sideB):
            for x in range(side.min_pos, side.max_pos + 1):
                square = side.squares[x]
                color = square.color
                final_side = color_to_side[color]
                data['squares'][square.position] = {
                    'colorScan' : {
                        'red'   : square.red,
                        'green' : square.green,
                        'blue'  : square.blue,
                    },
                    'finalSide' : color_to_side[color].name
                }

        return data

    def sort_squares(self, target_square, squares_to_sort):
        rank = []
        for square in squares_to_sort:
            distance = get_color_distance(target_square.rawcolor, square.rawcolor)
            rank.append((distance, square))
        rank = list(sorted(rank))

        result = []
        for (distance, square) in rank:
            log.info("%s vs %s distance %s (%s vs %s)" % (target_square, square, distance, pformat(target_square.rgb), pformat(square.rgb)))
            result.append(square)
        return result

    def bind_center_squares_to_anchor(self, square_indexes, desc):
        center_colors = OrderedDict()

        # We must add the anchor squares first
        for anchor_square in self.anchor_squares:
            center_colors[anchor_square.position] = anchor_square.rgb

        for side_name in self.side_order:
            side = self.sides[side_name]

            for square_index in square_indexes:
                square = side.center_squares[square_index]
                if square not in self.anchor_squares:
                    center_colors[square.position] = square.rgb

        sorted_center_colors = kmeans_sort_colors_static_anchors(center_colors)
        self.write_colors(desc, sorted_center_colors)

        # The first entry on each list is the anchor square
        for cluster_square_list in sorted_center_colors:
            anchor_square_index = cluster_square_list[0].index
            anchor_square = self.get_square(anchor_square_index)

            for cluster_square in cluster_square_list[1:]:
                square = self.get_square(cluster_square.index)
                square.anchor_square = anchor_square
                log.info("%s: square %s anchor square is %s" % (desc, square, anchor_square))

    def identify_anchor_squares(self):

        # Odd cube, use the centers
        if self.width % 2 == 1:

            for side_name in self.side_order:
                side = self.sides[side_name]
                anchor_square = side.squares[side.mid_pos]
                self.anchor_squares.append(anchor_square)
                log.info("center anchor square %s (odd) with color %s" % (anchor_square, anchor_square.color_name))

        # Even cube, use corners
        else:

            # Start with the LFU corner, that corner will give us the first three anchor squares
            self.anchor_squares.append(self.sideL.corner_squares[1])
            self.anchor_squares.append(self.sideF.corner_squares[0])
            self.anchor_squares.append(self.sideU.corner_squares[2])
            anchor1 = self.sideL.corner_squares[1]
            anchor2 = self.sideF.corner_squares[0]
            anchor3 = self.sideU.corner_squares[2]
            anchor1_rgb = (anchor1.red, anchor1.green, anchor1.blue)
            anchor2_rgb = (anchor2.red, anchor2.green, anchor2.blue)
            anchor3_rgb = (anchor3.red, anchor3.green, anchor3.blue)
            #log.info("anchor1_rgb %s" % pformat(anchor1_rgb))
            #log.info("anchor2_rgb %s" % pformat(anchor2_rgb))
            #log.info("anchor3_rgb %s" % pformat(anchor3_rgb))

            # Find the other three anchor squares...first group all corner squares via kmeans
            corner_colors = []
            for corner in self.corners:
                corner_colors.append((corner.square1.red, corner.square1.green, corner.square1.blue))
                corner_colors.append((corner.square2.red, corner.square2.green, corner.square2.blue))
                corner_colors.append((corner.square3.red, corner.square3.green, corner.square3.blue))
            sorted_corner_colors = kmeans_sort_colors_dynamic_anchors(corner_colors)

            anchor4_list = None
            anchor5_list = None
            anchor6_list = None

            # Find the "buckets" that contain the 4th, 5th and 6th anchor squares, these are the
            # buckets that do not contain the 1st, 2nd or 3rd anchor squares.
            for rgb_list in sorted_corner_colors:
                # Ignore the three groups that contain our first three anchor squares
                if anchor1_rgb in rgb_list or anchor2_rgb in rgb_list or anchor3_rgb in rgb_list:
                    continue

                if anchor4_list is None:
                    anchor4_list = rgb_list

                elif anchor5_list is None:
                    anchor5_list = rgb_list

                elif anchor6_list is None:
                    anchor6_list = rgb_list

            #log.info("anchor4_list %s" % pformat(anchor4_list))
            #log.info("anchor5_list %s" % pformat(anchor5_list))
            #log.info("anchor6_list %s" % pformat(anchor6_list))

            # Now find the other corner that has a square in anchor4_list,
            # anchor5_list, and anchor6_list
            for corner in self.corners:
                square1_rgb = (corner.square1.red, corner.square1.green, corner.square1.blue)
                square2_rgb = (corner.square2.red, corner.square2.green, corner.square2.blue)
                square3_rgb = (corner.square3.red, corner.square3.green, corner.square3.blue)

                if ((square1_rgb in anchor4_list or square1_rgb in anchor5_list or square1_rgb in anchor6_list) and
                    (square2_rgb in anchor4_list or square2_rgb in anchor5_list or square2_rgb in anchor6_list) and
                    (square3_rgb in anchor4_list or square3_rgb in anchor5_list or square3_rgb in anchor6_list)):

                    self.anchor_squares.append(corner.square1)
                    self.anchor_squares.append(corner.square2)
                    self.anchor_squares.append(corner.square3)
                    break
            else:
                raise Exception("Unable to ID the final three anchor squares")

        # No center squares
        if self.width == 2:
            pass

        # The only center squares are the anchors
        elif self.width == 3:
            pass

        elif self.width == 4:
            self.bind_center_squares_to_anchor((0, 1, 2, 3), '4x4x4 centers')

        elif self.width == 5:
            # t-centers
            self.bind_center_squares_to_anchor((1, 3, 5, 7), '5x5x5 t-centers')

            # x-centers
            self.bind_center_squares_to_anchor((0, 2, 6, 8), '5x5x5 x-centers')

        elif self.width == 6:

            # inside centers
            self.bind_center_squares_to_anchor((5, 6, 9, 10), '6x6x6 inside centers')

            # outside centers
            self.bind_center_squares_to_anchor((0, 3, 12, 15), '6x6x6 outside centers')

            # left oblique edges
            self.bind_center_squares_to_anchor((1, 7, 8, 14), '6x6x6 left oblique edges')

            # right oblique edges
            self.bind_center_squares_to_anchor((2, 4, 11, 13), '6x6x6 right oblique edges')

        else:
            raise Exception("Add anchor/center support for %dx%dx%d cubes" % (self.width, self.width, self.width))

        # Assign color names to each anchor_square. We compute which naming
        # scheme results in the least total color distance in terms of the anchor
        # square colors vs the colors in crayola_colors
        min_distance = None
        min_distance_permutation = None

        for permutation in permutations(self.crayola_colors.keys()):
            distance = 0

            for (anchor_square, color_name) in zip(self.anchor_squares, permutation):
                color_obj = self.crayola_colors[color_name]
                distance += get_color_distance(anchor_square.rawcolor, color_obj)

            if min_distance is None or distance < min_distance:
                min_distance = distance
                min_distance_permutation = permutation

        log.info('assign color names to anchor squares and sides')
        for (anchor_square, color_name) in zip(self.anchor_squares, min_distance_permutation):
            color_obj = self.crayola_colors[color_name]
            # I used to set this to the crayola_color object but I don't think
            # that buys us anything, it is better to use our rawcolor as our color
            # since other squares will be comparing themselves to our 'color'.  They
            # will line up more closely with it than they will the crayola_color object.
            # anchor_square.color = color_obj
            anchor_square.color = anchor_square.rawcolor
            anchor_square.color.name = color_name
            anchor_square.color_name = color_name

        for anchor_square in self.anchor_squares:
            log.info("anchor square %s with color %s" % (anchor_square, anchor_square.color_name))

        # Now that our anchor squares have been assigned a color/color_name, go back and
        # assign the same color/color_name to all of the other center_squares. This ends
        # up being a no-op for 2x2x2 and 3x3x3 but for 4x4x4 and up larger this does something.
        for side_name in self.side_order:
            side = self.sides[side_name]

            for square in side.center_squares:
                if square.anchor_square:
                    square.color = square.anchor_square.color
                    square.color_name = square.anchor_square.color_name
                    square.color.name = square.anchor_square.color.name

        # Assign each Side a color
        if self.sideU.mid_pos:
            for side_name in self.side_order:
                side = self.sides[side_name]
                side.red = side.squares[side.mid_pos].red
                side.green = side.squares[side.mid_pos].green
                side.blue = side.squares[side.mid_pos].blue
                side.color = side.squares[side.mid_pos].color
                side.color_name = side.squares[side.mid_pos].color_name

        else:
            '''
            color_to_side_name = {
                'Ye' : 'U',
                'Gr' : 'L',
                'OR' : 'F',
                'Bu' : 'R',
                'Wh' : 'D',
                'Rd' : 'B'
            }
            '''
            all_squares = []
            for side_name in self.side_order:
                side = self.sides[side_name]
                all_squares.extend(side.squares.values())

            for side_name in self.side_order:
                side = self.sides[side_name]

                if side_name == 'U':
                    target_color_name = 'Wh'
                elif side_name == 'L':
                    target_color_name = 'OR'
                elif side_name == 'F':
                    target_color_name = 'Gr'
                elif side_name == 'R':
                    target_color_name = 'Rd'
                elif side_name == 'D':
                    target_color_name = 'Ye'
                elif side_name == 'B':
                    target_color_name = 'Bu'

                for square in all_squares:
                    if square.color_name == target_color_name:
                        side.red = square.red
                        side.green = square.green
                        side.blue = square.blue
                        side.color = square.color
                        side.color_name = square.color_name
                        break
                else:
                    raise Exception("%s: could not determine color, target %s" % (side, target_color_name))

        with open('/tmp/rubiks-color-resolver.html', 'a') as fh:
            fh.write('<h1>Side -> Color Mapping</h1>\n')
            fh.write('<ul>\n')
            for side_name in self.side_order:
                side = self.sides[side_name]
                fh.write('<li>%s -> %s</li>\n' % (side_name, side.color_name))
            fh.write('</ul>\n')

            fh.write('<h1>Anchor Squares</h1>\n')
            for anchor_square in self.anchor_squares:
                fh.write("<div class='square' title='RGB (%d, %d, %d)' style='background-color: #%02x%02x%02x;'><span>%02d/%s</span></div>\n" %
                         (anchor_square.color.red, anchor_square.color.green, anchor_square.color.blue,
                          anchor_square.color.red, anchor_square.color.green, anchor_square.color.blue,
                          anchor_square.position, anchor_square.color_name))

    def create_corner_objects(self):
        # Corners
        self.corners = []

        # U
        self.corners.append(Corner(self, self.sideU.corner_pos[0], self.sideL.corner_pos[0], self.sideB.corner_pos[1]))
        self.corners.append(Corner(self, self.sideU.corner_pos[1], self.sideB.corner_pos[0], self.sideR.corner_pos[1]))
        self.corners.append(Corner(self, self.sideU.corner_pos[2], self.sideF.corner_pos[0], self.sideL.corner_pos[1]))
        self.corners.append(Corner(self, self.sideU.corner_pos[3], self.sideR.corner_pos[0], self.sideF.corner_pos[1]))

        # D
        self.corners.append(Corner(self, self.sideD.corner_pos[0], self.sideL.corner_pos[3], self.sideF.corner_pos[2]))
        self.corners.append(Corner(self, self.sideD.corner_pos[1], self.sideF.corner_pos[3], self.sideR.corner_pos[2]))
        self.corners.append(Corner(self, self.sideD.corner_pos[2], self.sideB.corner_pos[3], self.sideL.corner_pos[2]))
        self.corners.append(Corner(self, self.sideD.corner_pos[3], self.sideR.corner_pos[3], self.sideB.corner_pos[2]))

    def identify_corner_squares(self):
        self.valid_corners = []
        self.valid_corners.append((self.sideU.color, self.sideF.color, self.sideL.color))
        self.valid_corners.append((self.sideU.color, self.sideR.color, self.sideF.color))
        self.valid_corners.append((self.sideU.color, self.sideL.color, self.sideB.color))
        self.valid_corners.append((self.sideU.color, self.sideB.color, self.sideR.color))

        self.valid_corners.append((self.sideD.color, self.sideL.color, self.sideF.color))
        self.valid_corners.append((self.sideD.color, self.sideF.color, self.sideR.color))
        self.valid_corners.append((self.sideD.color, self.sideB.color, self.sideL.color))
        self.valid_corners.append((self.sideD.color, self.sideR.color, self.sideB.color))
        self.valid_corners = sorted(self.valid_corners)

    def identify_edge_squares(self):

        # valid_edges are the color combos that we need to look for. edges are Edge
        # objects, eventually we try to fill in the colors for each Edge object with
        # a color tuple from valid_edges
        self.valid_edges = []
        self.edges = []

        num_of_edge_squares_per_side = len(self.sideU.edge_squares)

        # A 2x2x2 has no edges
        if not num_of_edge_squares_per_side:
            return

        # For a 3x3x3 there is only one edge between F and U but for a 4x4x4
        # there are 2 of them and for a 5x5x5 there are 3 of them...loop to
        # add the correct number
        for (edge_index, x) in enumerate(range(int(num_of_edge_squares_per_side/4))):
            orbit_id = get_orbit_id(self.width, edge_index)
            self.valid_edges.append((self.sideU.color, self.sideB.color, orbit_id))
            self.valid_edges.append((self.sideU.color, self.sideL.color, orbit_id))
            self.valid_edges.append((self.sideU.color, self.sideF.color, orbit_id))
            self.valid_edges.append((self.sideU.color, self.sideR.color, orbit_id))

            self.valid_edges.append((self.sideF.color, self.sideL.color, orbit_id))
            self.valid_edges.append((self.sideF.color, self.sideR.color, orbit_id))

            self.valid_edges.append((self.sideB.color, self.sideL.color, orbit_id))
            self.valid_edges.append((self.sideB.color, self.sideR.color, orbit_id))

            self.valid_edges.append((self.sideD.color, self.sideF.color, orbit_id))
            self.valid_edges.append((self.sideD.color, self.sideL.color, orbit_id))
            self.valid_edges.append((self.sideD.color, self.sideR.color, orbit_id))
            self.valid_edges.append((self.sideD.color, self.sideB.color, orbit_id))
        self.valid_edges = sorted(self.valid_edges)

        # U and B
        for (edge_index, (pos1, pos2)) in enumerate(zip(self.sideU.edge_north_pos, reversed(self.sideB.edge_north_pos))):
            self.edges.append(Edge(self, pos1, pos2, edge_index))

        # U and L
        for (edge_index, (pos1, pos2)) in enumerate(zip(self.sideU.edge_west_pos, self.sideL.edge_north_pos)):
            self.edges.append(Edge(self, pos1, pos2, edge_index))

        # U and F
        for (edge_index, (pos1, pos2)) in enumerate(zip(self.sideU.edge_south_pos, self.sideF.edge_north_pos)):
            self.edges.append(Edge(self, pos1, pos2, edge_index))

        # U and R
        for (edge_index, (pos1, pos2)) in enumerate(zip(self.sideU.edge_east_pos, reversed(self.sideR.edge_north_pos))):
            self.edges.append(Edge(self, pos1, pos2, edge_index))

        # F and L
        for (edge_index, (pos1, pos2)) in enumerate(zip(self.sideF.edge_west_pos, self.sideL.edge_east_pos)):
            self.edges.append(Edge(self, pos1, pos2, edge_index))

        # F and R
        for (edge_index, (pos1, pos2)) in enumerate(zip(self.sideF.edge_east_pos, self.sideR.edge_west_pos)):
            self.edges.append(Edge(self, pos1, pos2, edge_index))

        # F and D
        for (edge_index, (pos1, pos2)) in enumerate(zip(self.sideF.edge_south_pos, self.sideD.edge_north_pos)):
            self.edges.append(Edge(self, pos1, pos2, edge_index))

        # L and B
        for (edge_index, (pos1, pos2)) in enumerate(zip(self.sideL.edge_west_pos, self.sideB.edge_east_pos)):
            self.edges.append(Edge(self, pos1, pos2, edge_index))

        # L and D
        for (edge_index, (pos1, pos2)) in enumerate(zip(self.sideL.edge_south_pos, reversed(self.sideD.edge_west_pos))):
            self.edges.append(Edge(self, pos1, pos2, edge_index))

        # R and D
        for (edge_index, (pos1, pos2)) in enumerate(zip(self.sideR.edge_south_pos, self.sideD.edge_east_pos)):
            self.edges.append(Edge(self, pos1, pos2, edge_index))

        # R and B
        for (edge_index, (pos1, pos2)) in enumerate(zip(self.sideR.edge_east_pos, self.sideB.edge_west_pos)):
            self.edges.append(Edge(self, pos1, pos2, edge_index))

        # B and D
        for (edge_index, (pos1, pos2)) in enumerate(zip(reversed(self.sideB.edge_south_pos), self.sideD.edge_south_pos)):
            self.edges.append(Edge(self, pos1, pos2, edge_index))

    def resolve_edge_squares(self):

        # A 2x2x2 will not have edges
        if not self.edges:
            return

        # Initially we flag all of our Edge objects as invalid
        for edge in self.edges:
            edge.valid = False

        for target_orbit_id in range(self.orbits):
            log.info('Resolve edges for orbit %d' % target_orbit_id)

            unresolved_edges = []
            for edge in self.edges:
                if edge.orbit_id == target_orbit_id:
                    unresolved_edges.append(edge)

            # And our 'needed' list of colors will hold the colors of every edge color pair
            needed_edge_color_tuple = []

            for (edge1, edge2, orbit_id) in sorted(self.valid_edges):
                if orbit_id == target_orbit_id:
                    needed_edge_color_tuple.append((edge1, edge2, orbit_id))
                assert edge1.name != edge2.name,\
                    "Both sides of an edge cannot be the same color, edge1 %s and edge2 %s are both %s" %\
                    (edge1, edge2, edge1.name)

            while unresolved_edges:

                # Calculate the color distance for each edge vs each of the needed color tuples
                for edge in unresolved_edges:
                    edge.first_vs_second_delta = 0
                    foo = []
                    colors_checked = []

                    for (colorA, colorB, orbit) in needed_edge_color_tuple:

                        # For 4x4x4 and larger there are multiple edges with the
                        # same pair of colors so if we've already calculated the
                        # distance for one of the edges with this color tuple
                        # don't calculate it again
                        if (colorA, colorB) in colors_checked:
                            continue

                        distance = edge.color_distance(colorA, colorB)
                        foo.append((distance, (colorA, colorB)))
                        colors_checked.append((colorA, colorB))

                    # Now sort the distance...
                    foo = sorted(foo)

                    if len(foo) >= 2:
                        (first_distance, (first_colorA, first_colorB)) = foo[0]
                        (second_distance, (second_colorA, second_colorB)) = foo[1]

                        # ...and note the delta from the color pair this edge is the closest
                        # match with vs the color pair this edge is the second closest match with
                        edge.first_vs_second_delta = second_distance - first_distance
                        edge.first_place_colors = (first_colorA, first_colorB)
                        edge.first_distance = first_distance
                        log.debug("%s 1st vs 2nd delta %d (%d - %d)" % (edge, edge.first_vs_second_delta, second_distance, first_distance))
                    else:
                        (first_distance, (first_colorA, first_colorB)) = foo[0]
                        edge.first_vs_second_delta = first_distance
                        edge.first_place_colors = (first_colorA, first_colorB)
                        edge.first_distance = first_distance
                        log.debug("%s 1st vs 2nd delta %d" % (edge, edge.first_vs_second_delta))

                # Now look at all of the edges and resolve the one whose 1st vs 2nd color
                # tuple distance is the greatest.  Think of it as the higher this delta
                # is the more important it is that we resolve this edge to the color tuple
                # that came in first place.
                max_delta = None
                max_delta_edge = None
                max_delta_distance = None

                for edge in unresolved_edges:
                    if max_delta is None or edge.first_vs_second_delta > max_delta:
                        max_delta = edge.first_vs_second_delta
                        max_delta_edge = edge
                        max_delta_distance = edge.first_distance

                distance = max_delta_distance
                edge = max_delta_edge
                (colorA, colorB) = edge.first_place_colors

                edge.update_colors(colorA, colorB)
                edge.valid = True
                edge.first_vs_second_delta = None
                edge.first_place_colors = None
                edge.first_distance = None
                needed_edge_color_tuple.remove((colorA, colorB, target_orbit_id))
                unresolved_edges.remove(edge)
                log.info("edge %s 1st vs 2nd delta of %d was the highest" % (edge, max_delta))

    def resolve_corner_squares(self):
        log.info('Resolve corners')

        # Initially we flag all of our Edge objects as invalid
        for corner in self.corners:
            corner.valid = False

        # And our 'needed' list will hold the colors of all 8 corners
        needed_corner_color_tuple = self.valid_corners

        unresolved_corners = [corner for corner in self.corners if corner.valid is False]

        while unresolved_corners:

            for corner in unresolved_corners:
                corner.first_vs_second_delta = 0
                foo = []

                for (colorA, colorB, colorC) in needed_corner_color_tuple:
                    distance = corner.color_distance(colorA, colorB, colorC)
                    foo.append((distance, (colorA, colorB, colorC)))

                # Now sort the distances...
                foo = sorted(foo)

                if len(foo) >= 2:
                    (first_distance, (first_colorA, first_colorB, first_colorC)) = foo[0]
                    (second_distance, (second_colorA, second_colorB, second_colorC)) = foo[1]

                    # ...and note the delta from the color pair this corner is the closest
                    # match with vs the color pair this corner is the second closest match with
                    corner.first_vs_second_delta = second_distance - first_distance
                    corner.first_place_colors = (first_colorA, first_colorB, first_colorC)
                    corner.first_distance = first_distance
                    log.debug("%s 1st vs 2nd delta %d (%d - %d)" % (corner, corner.first_vs_second_delta, second_distance, first_distance))
                else:
                    (first_distance, (first_colorA, first_colorB, first_colorC)) = foo[0]
                    corner.first_vs_second_delta = first_distance
                    corner.first_place_colors = (first_colorA, first_colorB, first_colorC)
                    corner.first_distance = first_distance
                    log.debug("%s 1st vs 2nd delta %d" % (corner, corner.first_vs_second_delta))

            # Now look at all of the corners and resolve the one whose 1st vs 2nd color
            # tuple distance is the greatest.  Think of it as the higher this delta
            # is the more important it is that we resolve this corner to the color tuple
            # that came in first place.
            max_delta = None
            max_delta_corner = None
            max_delta_distance = None

            for corner in unresolved_corners:
                if max_delta is None or corner.first_vs_second_delta > max_delta:
                    max_delta = corner.first_vs_second_delta
                    max_delta_corner = corner
                    max_delta_distance = corner.first_distance

            distance = max_delta_distance
            corner = max_delta_corner
            (colorA, colorB, colorC) = corner.first_place_colors

            corner.update_colors(colorA, colorB, colorC)
            corner.valid = True
            corner.first_vs_second_delta = None
            corner.first_place_colors = None
            corner.first_distance = None
            needed_corner_color_tuple.remove((colorA, colorB, colorC))
            unresolved_corners.remove(corner)
            log.info("corner %s 1st vs 2nd delta of %d was the highest" % (corner, max_delta))

    def write_final_cube(self):
        data = self.cube_for_json()
        cube = ['dummy', ]
        for (square_index, value) in data['squares'].items():
            html_colors = data['sides'][value['finalSide']]['colorHTML']
            cube.append((html_colors['red'], html_colors['green'], html_colors['blue']))

        self.write_cube('Final Cube', cube)

    def crunch_colors(self):
        self.anchor_squares = []

        self.create_corner_objects()
        self.identify_anchor_squares()
        self.identify_corner_squares()
        self.identify_edge_squares()
        self.print_cube()

        self.resolve_edge_squares()
        self.resolve_corner_squares()
        self.print_cube()
        self.print_layout()
        self.write_final_cube()
        self.www_footer()
