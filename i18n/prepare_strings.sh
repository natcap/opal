# RUN THIS FROM THE ADEPT REPO ROOT
# Write the adept translation information to Adept.pot.

POT_FILE='Adept.pot'

find adept -name "*.py" | xargs xgettext -d Adept -o i18n/$POT_FILE --language=Python --package-name=OPAL/MAFE --msgid-bugs-address=jdouglass@stanford.edu --from-code=UTF-8

# Replace necessary fields with proper data.
sed -i 's/charset=CHARSET/charset=UTF-8/' i18n/$POT_FILE
sed -i 's/FULL NAME <EMAIL@ADDRESS>/James Douglass <jdouglass@stanford.edu>/' i18n/$POT_FILE

# Convert Adept.pot to the language-specific .po files, merging them with
# the older versions of the same file.
pushd i18n
mkdir merged_po

for locale in "es" "en"
do
    echo Processing locale=$locale
    # merge the new file with the existing one, saving to the merged_po folder
    msgmerge $locale.po $POT_FILE > merged_po/$locale.po

    # copy the merged_po file to the original location.
    cp merged_po/$locale.po $locale.po
done

rm -r merged_po
popd

