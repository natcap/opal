for file in {adept,carbon_sm,generic_sm,nutrient_sm,sediment_sm}.json; do echo "UI FILE $file"; scripts/extract_text.sh $file; echo ""; echo ""; echo ""; done;
