for file in {adept,carbon_sm,generic_sm,nutrient_sm,sediment_sm}.json;
do 
    echo "UI FILE $file"
    scripts/extract_text.sh $file >> out_file.txt
done
python scripts/unique_strings.py out_file.txt
