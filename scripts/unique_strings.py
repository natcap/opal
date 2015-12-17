import sys

if __name__ == '__main__':
    # get the file from $arg1
    filename = sys.argv[1]
    found_strings = {}

    with open(filename) as source_file:
        current_file = 'unknown'
        for line in source_file:
            if line.startswith('UI FILE'):
                current_file = line.replace('UI FILE', '').strip()
            try:
                found_strings[line].add(current_file)
            except KeyError:
                found_strings[line] = set([current_file])
            if line not in found_strings:
                found_strings[line]
                print line

    for string, files_set in found_strings.iteritems():
        for filename in files_set:
            print '# %s ' % filename
        print string

