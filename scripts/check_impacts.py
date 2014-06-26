"""
$ python check_impacts.py filename

This script takes a CSV file as input, where the CSV is expected to be the
output of a run of the static map testing function in adept.static_maps.  This
script prints informative information to stdout if a watershed is found to have
an incomplete set of impact parcels.

sample output:
    Checking 54 watersheds
    watershed 46 missing 16 keys: [0, 5, 7, 8, 10, 11, 13, 20, 23, 26, 29, 30, 31, 33, 37, 47]
    watershed 44 missing 9 keys: [41, 42, 43, 44, 45, 46, 47, 48, 49]

NOTE: This function assumes that there are 50 impacts per
watershed.  This can of course be changed by modifying the source, below.

Arguments:
     filename - (required) a uri to a CSV logfile from a static map testing
         run.

"""

import sys

if __name__ == '__main__':
    filename = sys.argv[1]

    open_file = open(filename)

    # get rid of the header
    open_file.readline()

    rows_dict = {}
    for line in open_file:
        watershed, impact = line.split(',')[0:2]

        try:
            rows_dict[watershed].append(impact)
        except KeyError:
            rows_dict[watershed] = [impact]

    print 'Checking %s watersheds' % len(rows_dict)

    for ws_key, impact_keys in rows_dict.iteritems():
        if len(impact_keys) < 50:
            missing_keys = []
            current_keys = set(int(k) for k in impact_keys)
            for expected_key in range(50):
                if expected_key not in current_keys:
                    missing_keys.append(expected_key)

            print 'watershed %s missing %s keys: %s' % (ws_key,
                50 - len(impact_keys), missing_keys)



