if [ -e 'out_file.txt' ]
then
    echo 'out_file.txt exists. Remove and re-run'
    exit 1
fi

for file in {opal,opal_carbon_sm,opal_generic_sm,opal_nutrient_sm,opal_sediment_sm}.json;
do 
    echo "UI FILE $file" >> out_file.txt
    scripts/extract_text.sh $file >> out_file.txt
done
python scripts/unique_strings.py out_file.txt > opal_unique_strings.txt
