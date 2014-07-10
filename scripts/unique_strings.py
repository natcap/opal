import sys

if __name__ == '__main__':
    # get the file from $arg1
    filename = sys.argv[1]
    found_strings = set()

    with open(filename) as source_file:
        for line in source_file:
            if line not in found_strings:
                found_strings.add(line)
                print line



