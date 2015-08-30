"""
expected insertion file structure:

* 1+ lines beginning with # indicating the json filename this string belongs to.
* On one line: The english string to replace
* On one line: The spanish equivalent of the english string.
* A blank line, signifying the end of the section.

Not adhering to this structure is an error.
"""

import json
import os
import collections

ERROR_STRINGS = []

def sanitize_punct(in_string):
    out_string = in_string[:]
    for char in [':', ',', '.']:
        out_string = out_string.replace(char, '')
    return out_string

def get_strings_for_file(string_filename, json_filename):
    """
    Extract strings from the string_file that need to be inserted into the
    json_file.
    """

    json_basename = os.path.basename(json_filename)

    translated_strings = {}
    with open(string_filename) as translation_file:
        queue = collections.deque([line.strip() for line in translation_file])
        while len(queue) > 0:
            current_line = queue.popleft()
            if current_line.strip() == '':
                continue

            include_translation = False
            while current_line.startswith('#'):
                if json_basename in current_line:
                    include_translation = True
                current_line = queue.popleft()

            # current line is the en translation,
            en_string = current_line
            if 'A raster file whose values indicate the level of species richness at a particular site' in en_string:
                print en_string
                ERROR_STRINGS.append(en_string)
            es_string = queue.popleft()

            if include_translation is True:
                # Remove commas and colons.  JSON text is better formatted.
                en_string = sanitize_punct(en_string)
                es_string = es_string.decode('latin-1').encode('utf-8')
                translated_strings[en_string] = es_string
            else:
                continue
    return translated_strings

def insert_strings(json_file, strings_dict):
    config_dict = json.load(open(json_file))

    def recurse(item):
        if isinstance(item, dict):
            new_item = {}
            if 'en' in item:
                try:
                    en_string = sanitize_punct(item['en'])
                    new_item['en'] = en_string
                    new_item['es'] = strings_dict[en_string]
                except KeyError:
                    print en_string
                    raise
            else:
                for item_key, item_value in item.iteritems():
                    new_item[item_key] = recurse(item_value)
            return new_item
        elif isinstance(item, list):
            new_item = []
            for list_elem in item:
                new_item.append(recurse(list_elem))
            return new_item
        else:
            return item

    replaced_strings = recurse(config_dict)
    json.dump(replaced_strings, open(json_file, 'w'), sort_keys=True, indent=4)

if __name__ == '__main__':
    opal_json = 'opal.json'
    translations = os.path.expanduser('~/Downloads/opal_unique_strings SP PAMV.txt')

    translated_strings = get_strings_for_file(translations, opal_json)
    with open('debug.txt', 'w') as debug_file:
        debug_file.write(json.dumps(translated_strings, sort_keys=True, indent=4))

    insert_strings(opal_json, translated_strings)

