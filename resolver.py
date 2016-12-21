#!/usr/bin/env python3

from rubikscolorresolver import RubiksColorSolver2x2x2, RubiksColorSolver3x3x3, RubiksColorSolver4x4x4
import argparse
import json
import logging
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--test', action='store_true', default=False)
parser.add_argument('--rgb', help='RGB json', default=None)
args = parser.parse_args()

# logging.basicConfig(filename='rubiks-rgb-solver.log',
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(levelname)5s: %(message)s')
log = logging.getLogger(__name__)

# Color the errors and warnings in red
logging.addLevelName(logging.ERROR, "\033[91m  %s\033[0m" % logging.getLevelName(logging.ERROR))
logging.addLevelName(logging.WARNING, "\033[91m%s\033[0m" % logging.getLevelName(logging.WARNING))

if args.test:
    results = []

    with open('test-data/2x2x2-solved.txt', 'r') as fh:
        scan_data_str_keys = json.load(fh)
        scan_data = {}

        for (key, value) in scan_data_str_keys.items():
            scan_data[int(key)] = value

        cube = RubiksColorSolver2x2x2()
        cube.enter_scan_data(scan_data)
        cube.crunch_colors()
        output = ''.join(cube.cube_for_kociemba_strict())
        if output == 'UUUULLLLFFFFRRRRBBBBDDDD':
            results.append("PASS: 2x2x2")
        else:
            results.append("FAIL: 2x2x2")

    with open('test-data/3x3x3-solved.txt', 'r') as fh:
        scan_data_str_keys = json.load(fh)
        scan_data = {}

        for (key, value) in scan_data_str_keys.items():
            scan_data[int(key)] = value

        cube = RubiksColorSolver3x3x3()
        cube.enter_scan_data(scan_data)
        cube.crunch_colors()
        output = ''.join(cube.cube_for_kociemba_strict())
        if output == 'UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB':
            results.append("PASS: 3x3x3")
        else:
            results.append("FAIL: 3x3x3")

    with open('test-data/4x4x4-solved.txt', 'r') as fh:
        scan_data_str_keys = json.load(fh)
        scan_data = {}

        for (key, value) in scan_data_str_keys.items():
            scan_data[int(key)] = value

        cube = RubiksColorSolver4x4x4()
        cube.enter_scan_data(scan_data)
        cube.crunch_colors()
        output = ''.join(cube.cube_for_kociemba_strict())
        if output == 'UUUUUUUUURRRRRRRRRFFFFFFFFFDDDDDDDDDLLLLLLLLLBBBBBBBBB':
            results.append("PASS: 4x4x4")
        else:
            results.append("FAIL: 4x4x4")

    print('\n'.join(results))

else:
    try:
        scan_data_str_keys = json.loads(args.rgb)
        scan_data = {}

        for (key, value) in scan_data_str_keys.items():
            scan_data[int(key)] = value

        square_count = len(scan_data.keys())

        # 2x2x2 cube
        if square_count == 24:
            cube = RubiksColorSolver2x2x2()

        # 3x3x3 cube
        elif square_count == 54:
            cube = RubiksColorSolver3x3x3()

        else:
            raise Exception("Only 2x2x2 and 3x3x3 cubes are supported, your cube has %s squares" % square_count)

        cube.enter_scan_data(scan_data)
        cube.crunch_colors()
        # print(json.dumps(cube.cube_for_json()))
        print(''.join(cube.cube_for_kociemba_strict()))

    except Exception as e:
        log.exception(e)
        sys.exit(1)
