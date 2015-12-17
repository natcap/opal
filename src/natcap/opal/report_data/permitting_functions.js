$(document).ready(function(){
    //Get a handle on the two JSON data objects set in the html json tags
    var globalMuniData = JSON.parse(document.getElementById('muni-data').innerHTML);
    var globalImpactData = JSON.parse(document.getElementById('impact-data').innerHTML);

    //State of current selected parcel_ids
    var jsonState = {};
    //State of current municipalities
    var muniState = {};
    //Handle on the 'last' table, municipality table
    var $tableLast = $('#muni_table');

    //Object that maps municipality column indices to municipality names
    var muniColMap = {};
    //Array of municipality table column indices
    var muniColIndexList = [];
    //Build up muniColMap and muniColIndexList
    $tableLast.find("th").each(function(){
        muniColMap[$(this).index()] = $(this).text();
        muniColIndexList.push($(this).index());
    });
    //Sort the indices
    muniColIndexList.sort();
    //console.log('muniColIndexList');
    //console.log(muniColIndexList);
    //Array to hold municipality column names in order
    var muniColList = [];
    //Build up muniColList
    for(var colIndex in muniColIndexList){
        muniColList.push(muniColMap[colIndex]);
    }
    //console.log('muniColList');
    //console.log(muniColList);

    //If any municipalities have starting impacts add them to the table
    initiateImpacts(muniState, muniColList, globalImpactData);
    //console.log('returned munistate');
    //console.log(muniState);

    //Get arrays of the column headers by class names
    var offsetList = getColClassDetail('offsets');
    var impactList = getColClass('impacts');
    var netList = getColClass('net');

    //Check to see if any formatting options have been indicated
    formatNumbers();
    //Check to see if any column headers have a class that
    //indicates rounding should be done on the numbers
    roundNumbers();
    //Comma separate values every three sig digits
    commaSeparateNumbers();
    //Style the net column values.
    formatNetColumns();

    //On a checkbox change event
    $('[name="cb"]').change(function() {
        //We need to manualy update the state of the checkbox 'value' attribute
        //So that it can be properly sorted
        if(this.value == "1"){
            //Now Checked
            this.value = "0";
            }
        else{
            //Now UnChecked
            this.value = "1";
            }

        //Get a handle on the table where the checkbox was made
        var $table = $(this).closest('table');
        //Only do certain operations if the table is muni table
        if($table.attr('id') == 'parcel_table'){
            //Get handle on the parcel_id column index
            var par_index = $table.find('th.parcel_id').index();
            //Get the parcel_id related to the changed checkbox
            var par_id = $(this).closest('tr').find('td:eq(' + par_index + ')').text();

            //ADD and update
            if(this.checked){
                //Add parcel_id to jsonState with data
                jsonState[par_id] = globalMuniData[par_id];
                //Get the munis from parcel_id data
                var munis = jsonState[par_id]['municipalities'];
                for(var muni in munis){
                    //Get the percentage as decimal to adjust values with
                    var perc = munis[muni];
                    //Update municipality if municipality is already tracked
                    if(muni in muniState){
                        var muniDict = muniState[muni];
                        //Update the count of parcel ids representing the
                        //municipality
                        if('count' in muniState[muni]){
                            muniDict['count'] = muniDict['count'] + 1;
                        }
                        else{
                            //In here because a municipality was added in initial impacts
                            //Set to 2 so that we never remove the row, keeping the impacts
                            muniDict['count'] = 2;
                        }
                        //Get handle on the row of the municipality we want to
                        //update
                        var $td = $tableLast.find('td:contains("' + muni + '")');
                        var $tr = $td.closest('tr');
                        //Get the offsets object
                        var muniOffsets = muniDict['offsets'];
                        //Get the nets object
                        var muniNets = muniDict['nets'];
                        //For each offset column update offset and net columns
                        $.each(offsetList, function(index, offset){
                            // Offset is the detailed classname.  Get the service we're dealing with
                            var offsetBase = offset.split('_')[2]

                            //Net column name
                            var netKey = $tableLast.find("th.services_net_" + offsetBase).text()
                            var netAdjKey = $tableLast.find("th.services_netadj_" + offsetBase).text()
                            //Get the adjusted offset value for the column from the

                            //parcel_id table
                            var adjustedVal = 0.0;
                            if(capitalize(offsetBase) in jsonState[par_id]){
                                adjustedVal = jsonState[par_id][capitalize(offsetBase)] * perc;
                            }
                            //Update the offsets / nets in the data structure
                            muniOffsets[offset] = muniOffsets[offset] + adjustedVal;
                            muniNets[netKey] = muniNets[netKey] + adjustedVal;
                            //Get index of corresponding offset and net column
                            var offsetIndex = $tableLast.find('th.' + offset).index();
                            var netIndex = $tableLast.find('th:contains("' + netKey + '")').index();
                            var popNetIndex = $tableLast.find('th:contains("' + netAdjKey + '")').index();
                            //Set new and update values in table for offset and net for column
                            $tr.find('td:eq(' + offsetIndex + ')').html(muniOffsets[offset]);
                            $tr.find('td:eq(' + netIndex + ')').html(muniNets[netKey]);
                            $tr.find('td:eq(' + popNetIndex + ')').html(muniNets[netKey] * muniDict['pop']);
                        });
                    }
                    //Add new municipality to the tracking data structure
                    //and to the municipality table
                    else{
                        muniState[muni] = {};
                        //Add a counter to track if the municipality is still
                        //represented by the parcel ids
                        muniState[muni]['count'] = 1;

                        var muniDict = muniState[muni];
                        //Add population data to the data structure
                        muniDict['pop'] = globalImpactData[muni]['pop'];
                        //Create objects in the current object that track
                        //table information
                        muniDict['offsets'] = {};
                        muniDict['nets'] = {};
                        muniDict['impacts'] = {};
                        //For each column name in offsets add offset, impact
                        //and net value
                        $.each(offsetList, function(index, offset){
                            // offset is the detailed offset classname.
                            // Get the service we're dealing with.
                            var offsetBase = offset.split('_')[2]
                            //var netColName = offsetBase + ' net';
                            //Net column name
                            var netKey = $tableLast.find("th.services_net_" + offsetBase).text()
                            var netAdjKey = $tableLast.find("th.services_netadj_" + offsetBase).text()

                            var impactColName = capitalize(offsetBase) + ' impact';

                            var adjustedVal = 0.0;
                            console.log('parcel id ' + par_id)
                            console.dir(jsonState[par_id])
                            if(capitalize(offsetBase) in jsonState[par_id]){
                                adjustedVal = jsonState[par_id][capitalize(offsetBase)] * perc;
                            }
                            //Set offset value from parcel data adjusted to percentage
                            muniDict['offsets'][offset] = adjustedVal;
                            //Set impact values to 0 since, if we are adding a new municipality
                            //it was not originally set with having impacts
                            muniDict['impacts'][impactColName] = 0.0;
                            //Set nets to the same as offsets since there is no initial impacts
                            muniDict['nets'][netKey] = adjustedVal;
                        });
                        //Adding a new row so build up some html
                        var rowString = "<tr>";
                        //Iterate over the column names in the municipality table
                        //building html row string appropriately
                        $.each(muniColList, function(index, colName){
                            var detailedClassName = $tableLast.find("th:contains('" + colName + "')").attr('class').split(' ')[0]
                            var col_category = detailedClassName.split('_')[1]
                            var service = capitalize(detailedClassName.split('_')[2])

                            console.dir(muniDict)
                            if(detailedClassName == 'services_pop_name'){
                                rowString = rowString + "<td>" + muni + "</td>";}
                            else if(detailedClassName == 'services_pop_count'){
                                rowString = rowString + "<td>" + muniDict['pop'] + "</td>";
                                }
                            else if(col_category == 'impact'){
                                rowString = rowString + "<td>" + muniDict['impacts'][service + ' impact'] + "</td>";
                                }
                            else if(col_category == 'offset'){
                                rowString = rowString + "<td>" + muniDict['offsets'][detailedClassName] + "</td>";
                                }
                            else if(col_category == 'net'){
                                rowString = rowString + "<td>" + muniDict['nets'][colName] + "</td>";
                                }
                            else if(col_category == 'netadj'){
                                var service = service.charAt(0).toUpperCase() + service.slice(1)
                                var impact_col = service + ' impact'
                                var offset_col = 'services_offset_' + service.toLowerCase()
                                var net = muniDict['offsets'][offset_col] - muniDict['impacts'][impact_col]
                                rowString = rowString + "<td>" + net * muniDict['pop'] + "</td>";
                                }
                            else {
                                console.log("ERROR handling column name for impact row : " + colName);
                            }
                        });

                        rowString = rowString + "</tr>";
                        //Add row to end of table
                        $tableLast.find('tr.totals').before(rowString);
                    }
                }
                //Get a handle on 'this', which is the checkbox element
                var $checkBox = $(this);
                //Handle updating the Biodiversity table based on parcel_id
                //being selected.
                updateBioTable($checkBox, true);
                updateCarbonTable($checkBox, true);
                roundNumbers();
            }
            //Parcel id is unchecked so update data / table
            else{
                //Get the munis from parcel_id data
                var munis = jsonState[par_id]['municipalities'];
                for(var muni in munis){
                    //Get the percentage as decimal to multiply values with
                    var perc = munis[muni];
                    //Decrease the count by 1 since a parcel_id was unchecked
                    muniState[muni]['count'] = muniState[muni]['count'] - 1;
                    //If the muni is no longer represented by a parcel check
                    //remove it
                    if(muniState[muni]['count'] == 0){
                        //Get handle on the row
                        var $td = $tableLast.find('td:contains("' + muni + '")');
                        var $tr = $td.closest('tr');
                        //Fade out effect, when removing row
                        $tr.fadeOut(200, function(){
                            $tr.remove();
                            });
                        //Delete muni from muniState object
                        delete muniState[muni];
                    }
                    //Municipality is still represented either by a parcel check
                    //or initial impact, so just update
                    else{
                        //Get handle on the row
                        var $td = $tableLast.find('td:contains("' + muni + '")');
                        var $tr = $td.closest('tr');

                        //Get handle on data objects for updating
                        var muniDict = muniState[muni];
                        var muniOffsets = muniDict['offsets'];
                        var muniNets = muniDict['nets'];

                        $.each(offsetList, function(index, offset){
                            // Offset is the detailed offset classname.
                            // Get the service we're dealing with.
                            var offsetBase = offset.split('_')[2]

                            //Net column name
                            var netKey = $tableLast.find("th.services_net_" + offsetBase).text()
                            var netAdjKey = $tableLast.find("th.services_netadj_" + offsetBase).text()

                            //Get the value that is being updated from parcel table
                            var adjustedVal = 0.0;
                            if(capitalize(offsetBase) in jsonState[par_id]){
                                adjustedVal = jsonState[par_id][capitalize(offsetBase)] * perc;
                            }
                            //Adjust the data structure with the update values of
                            //removing a checked parcel
                            muniOffsets[offset] = muniOffsets[offset] - adjustedVal;
                            muniNets[netKey] = muniNets[netKey] - adjustedVal;
                            //Get column index in table for offset and net column
                            var offsetIndex = $tableLast.find('th:contains("' + offset + '")').index();
                            var netIndex = $tableLast.find('th:contains("' + netKey + '")').index();
                            var popNetIndex = $tableLast.find('th:contains("' + netAdjKey + '")').index();
                            //Update the html in the table
                            $tr.find('td:eq(' + offsetIndex + ')').html(muniOffsets[offset]);
                            $tr.find('td:eq(' + netIndex + ')').html(muniNets[netKey]);
                            $tr.find('td:eq(' + popNetIndex + ')').html(muniNets[netKey] * muniState[muni]['pop']);
                        });
                        roundNumbers();
                    }
                }

                //Update jsonState by deleting the parcel id that was unchecked
                delete jsonState[par_id];
                //console.log(globalMuniData[par_id]);
                //Get a handle on 'this', which is the checkbox element
                var $checkBox = $(this);
                //Handle updating the Biodiversity table based on parcel_id
                //being un-selected.
                updateBioTable($checkBox, false);
                updateCarbonTable($checkBox, false);
                roundNumbers();
            }
        }
        //Since we just updated some values, check to see if they
        //need to be formatted, rounded, or comma separated
        formatNumbers();
        formatNetColumns();
        updateHydrologicalTotals();
        commaSeparateNumbers();
        roundNumbers();
    });
    //Functions that should always be called once table data is set up.
    centerColumns();

    $(".export").on('click', function (event) {
        exportToCSV.apply(this);
    });

    $('#TOC').toc({
            'selectors': 'h1,h2,h3', //elements to use as headings
            'container': 'body', //element to find all selectors in
            'smoothScrolling': true, //enable or disable smooth scrolling on click
            'prefix': 'toc', //prefix for anchor tags and class names
            'onHighlight': function(el) {}, //called when a new section is highlighted
            'highlightOnScroll': true, //add class to heading that is currently in focus
            'highlightOffset': 100, //offset to trigger the next headline
            'anchorName': function(i, heading, prefix) { //custom function for anchor name
                        return prefix+i;
                            },
            'headerText': function(i, heading, $heading) { //custom function building the header-item text
                        return $heading.text();
                            },
        'itemClass': function(i, heading, $heading, prefix) { // custom function for item class
              return $heading[0].tagName.toLowerCase();
        }
    });
});

function updateHydrologicalTotals(){
    // This function loops through all the net*pop columns in the
    // hydrological servicesheds table and sets the total values
    // at the bottom of the table appropriately.
    $hydroTable = $('#muni_table');
    var columns = getColClassDetail('population');
    console.log('COLUMNS');
    console.dir(columns);
    for (var column_index in columns){
        var table_col_index = $hydroTable.find('th.' + columns[column_index]).index() + 1;
        var class_category = columns[column_index].split('_')[1];
//        console.log(class_category);
//        console.log(table_col_index);
        if (class_category == 'netadj'){
            // get the values that need to be summed.
            var value_list = $hydroTable.find('tbody tr > :nth-child(' + table_col_index + ')').slice(0, -1);
            var value_sum = 0;
            $.each(value_list, function() {
                value_sum += parseFloat($(this).text().split(',').join(''));
            });
        }

        var table_cell = $hydroTable.find('tr.totals :nth-child(' + table_col_index + ')');
        table_cell.html(value_sum);
        table_cell.removeClass('negative');
        table_cell.removeClass('positive');
        // format the value sum.
        var classname = 'negative'
        if (value_sum >= 0){
            classname = 'positive'
        }
        table_cell.addClass(classname);
    }
}

function updateCarbonTable($checkBox, checked){
    //This function updates the Carbon table based on
    //parcel_id selection from the parcel table
    //
    // $checkBox - handle on html element for changed checkbox
    // checked - a boolean value indicated whether the checkbox
    //              was checked up un-checked

    //console.log("Update Carbon Table");
    //Get a handle on the table where the checkbox was made
    var $offsetTable = $checkBox.closest('table');
    //Get a handle on the Biodiversity table
    var $carbonTable = $('#global_benefits_table');

    // get a list of impact names
    $carbonTable.find('tbody:eq(0) tr').each(function(){
        // get the impact name.
        var serviceName = $(this).find('td:first').text();
        var serviceNameLower = serviceName.toLowerCase().split(' ').join('_');

        //Get the carbon offset column index from parcel table
        //var carbonIndex = $table.find('th.carbon').index();
        var selectedOffsetIndex = $offsetTable.find('th.' + serviceNameLower + ':first').index();
        //console.log(serviceNameLower + ' offset index ' + selectedOffsetIndex)

        //Get the value as a float from the carbon column in
        //the row the checkbox change occurred.
        var offsetValue = parseFloat(
            $checkBox.closest('tr').find('td:eq(' + selectedOffsetIndex + ')').text().split(',').join(''));
        //console.log(serviceNameLower + ' offset value ' + offsetValue)

        //Get the Net column index from carbon Table
        var netIndex = $offsetTable.find('th.net').index();
        //Get the Required Offset column index from carbon Table
        var serviceOffsetIndex = $offsetTable.find('th.required_offset').index();
        //console.log('Offset column index ' + serviceOffsetIndex)

        //Get a handle on the table row that we're interested in
        var $activeRow = $(this);
        //console.log('Active row ' + $activeRow.text());

        //Get the service impact column index from carbon table
        var currentImpactValue = parseFloat($activeRow.find('td:eq(1)').text().split(',').join(''));

        //Get a handle on the table data element for the carbon offset amount.
        var $tdOffsetAmt = $activeRow.find('td:eq(2)');
        //console.log(serviceNameLower + ' offset amount from table ' + $tdOffsetAmt.text())

        //Get amt Offset value, handling comma separated values
        var amtOffset = parseFloat($tdOffsetAmt.text().split(',').join(''));

        //Get a handle on the table data element for Net of eco type
        //we are interested in
        var $tdNetImpact = $activeRow.find('td:eq(3)');

        //Get Required Offset value, handling comma separated values
        var reqOffset = parseFloat($activeRow.find('td:eq(' + serviceOffsetIndex + ')').text().split(',').join(''));
        //console.log("Required offset " + reqOffset)

        //Initialize updated carbon Offset value
        var carbonOffset = 0.0;

        if(checked){
            //Add Area Offset value with new value from parcel table to get updated
            //value
            carbonOffset = amtOffset + offsetValue;
        }
        else{
            //Subtract Area Offset value with new value from parcel table to get updated
            //value
            carbonOffset = amtOffset - offsetValue;
        }
        //console.log('Impact value ' + currentImpactValue);
        //console.log('Offset value ' + carbonOffset);
        //Calculate net impact value from Area Offset minus Required Offset
        var netImpact = currentImpactValue + carbonOffset;
        //console.log('Writing net impact value ' + netImpact)
        //Set updated Area Offset
        $tdOffsetAmt.html(carbonOffset);
        //Set updated Net Impact
        $tdNetImpact.html(netImpact);
    });
}

function updateBioTable($checkBox, checked){
    //This function updates the Biodiversity table based on
    //parcel_id selection from the parcel table
    //
    // $checkBox - handle on html element for changed checkbox
    // checked - a boolean value indicated whether the checkbox
    //              was checked up un-checked

    //console.log("Update Bio Table");
    //Get a handle on the table where the checkbox was made
    var $table = $checkBox.closest('table');
    //Get a handle on the Biodiversity table
    var $bioTable = $('#bio_table');

    //Get the Area column index from parcel table
    var areaIndex = $table.find('th.area').index();
    //Get the Eco Type column index from parcel table
    var ecoIndex = $table.find('th.eco_type').index();
    //console.log(ecoIndex);
    //Get the value as a float from the Area column in
    //the row the checkbox change occurred.
    var areaValue = parseFloat(
        $checkBox.closest('tr').find('td:eq(' + areaIndex + ')').text().split(',').join(''));
    //Get the String value of Eco Type in the row the checkbox change occurred.
    //Value is wrapped in a <span> element under the 'title' attribute
    var ecoType = $checkBox.closest('tr').find('td:eq(' + ecoIndex + ')').text();
    //console.log(ecoType);
    //Get the Area Offset column index from Bio Table
    var bioAreaIndex = $bioTable.find('th.area_offset').index();
    //Get the Net column index from Bio Table
    var bioNetIndex = $bioTable.find('th.net').index();
    //Get the Required Offset column index from Bio Table
    var bioOffsetIndex = $bioTable.find('th.required_offset').index();

    //Get a handle on the table row that contains in a table data element
    //the ecosystem type we are interested in. The eco types will be unique.
    var $bioRow = $bioTable.find('td:contains("' + ecoType + '")').closest('tr');
    //Get a handle on the table data element for Area Offset of eco type
    //we are interested in
    var $tdAreaOffset = $bioRow.find('td:eq(' + bioAreaIndex + ')');
    //Get Area Offset value, handling comma separated values
    var areaOffset = parseFloat($tdAreaOffset.text().split(',').join(''));
    //Get a handle on the table data element for Net of eco type
    //we are interested in
    var $tdNetImpact = $bioRow.find('td:eq(' + bioNetIndex + ')');
    //Get Required Offset value, handling comma separated values
    var reqOffset = parseFloat($bioRow.find('td:eq(' + bioOffsetIndex + ')').text().split(',').join(''));

    //Initialize updated Area Offset value
    var newAreaOffset = 0.0;

    if(checked){
        //Add Area Offset value with new value from parcel table to get updated
        //value
        newAreaOffset = areaOffset + areaValue;
    }
    else{
        //Subtract Area Offset value with new value from parcel table to get updated
        //value
        newAreaOffset = areaOffset - areaValue;
    }
    //Calculate net impact value from Area Offset minus Required Offset
    var netImpact = newAreaOffset - reqOffset;
    //Set updated Area Offset
    $tdAreaOffset.html(newAreaOffset);
    //Set updated Net Impact
    $tdNetImpact.html(netImpact);
}

function capitalize(string){
    // Helper function to capitalize the first character of the string passed in.
    // Returns the capitalized (sentence-case) string.
    return string.charAt(0).toUpperCase() + string.slice(1)
}

function getColClassDetail(name){
    //Helper function that returns an array of column names
    //that have a certain class name, 'name'
    var classList = [];
    //Handle on the 'last' table, municipality table
    var $tableLast = $('#muni_table');
    $tableLast.find('th.' + name).each(function(){
        classList.push($(this).attr('class').split(' ')[0]);
    });

    return classList;
}

function getColClass(name){
    //Helper function that returns an array of column names
    //that have a certain class name, 'name'
    var classList = [];
    //Handle on the 'last' table, municipality table
    var $tableLast = $('#muni_table');
    $tableLast.find('th.' + name).each(function(){
        classList.push($(this).text());
    });

    return classList;
}

function initiateImpacts(muniState, muniColList, globalImpactData) {
    //This function initiates any municipalities that have initial impacts
    //muniState - an object that tracks the state / data of municipalities
    //    currently in the table
    //muniColList - an Array of the municipality column names in order
    //globalImpactData - an object of the municipality JSON data

    //Handle on the 'last' table, municipality table
    var $tableLast = $('#muni_table');

    //Get arrays of the column headers by class names
    var offsetList = getColClassDetail('offsets');
    var impactList = getColClassDetail('impacts');
    var netList = getColClassDetail('net');

    //console.log('offsetList');
    //console.log(offsetList);

    for(var muniKey in globalImpactData){
        //Iterating over each municipality and constructing a working
        //object that represents the municipalities with initial impacts
        if('impacts' in globalImpactData[muniKey]){
            //Get population and impacts data
            muniState[muniKey] = globalImpactData[muniKey];
            var muniDict = muniState[muniKey];
            //Initialize inner objects for offsets and nets
            muniDict['offsets'] = {};
            muniDict['nets'] = {};
            //Initialize offset column data to 0
            $.each(offsetList, function(index, offset){
                muniDict['offsets'][offset] = 0.0;
                });
            //Initialize net values to the negative of the impact
            $.each(netList, function(index, net){
                //var colBase = net.substr(0, net.indexOf(' ')).toLowerCase();
                var service = net.split('_')[2]
                service = service.charAt(0).toUpperCase() + service.slice(1)
                var netColName = $tableLast.find('th.' + net).text()

                var impactEqu = service + ' impact';
                muniDict['nets'][netColName] = muniDict['impacts'][impactEqu];
                });
        }
    }
    //console.log('muniSate');
    //console.log(muniState);
    var nets_times_pop = {
        Sediment: 0,
        Nitrogen: 0,
        Custom: 0
    }
    var total_row = []
    var build_total_row_template = true
    for(var muniKey in muniState){
        //For each municipality that has an initial impact
        //build up a proper html row string to add to table

        var muniDict = muniState[muniKey];
        var rowString = "<tr>";

        $.each(muniColList, function(index, colName){
            // get detailed classname from the MuniTable
            var detailedClassName = $tableLast.find("th:contains('" + colName + "')").attr('class').split(' ')[0]
            var col_category = detailedClassName.split('_')[1]
            var service = detailedClassName.split('_')[2]
            service = service.charAt(0).toUpperCase() + service.slice(1)
            console.log(service)

            if (build_total_row_template === true){
                console.log(service)
                if (service == 'Name'){
                    total_row.push('Total');
                }
                else if (col_category == 'netadj'){
                    total_row.push(service);
                }
                else {
                    total_row.push('--');
                    }
            }

            //console.dir(muniDict)
            //console.dir(nets_times_pop)
            if(detailedClassName == 'services_pop_name'){
                rowString = rowString + "<td>" + muniKey + "</td>";}
            else if(detailedClassName == 'services_pop_count'){
                rowString = rowString + "<td>" + muniDict['pop'] + "</td>";
                }
            else if(col_category == 'impact'){
                rowString = rowString + "<td>" + muniDict['impacts'][service + ' impact'] + "</td>";
                }
            else if(col_category == 'offset'){
                rowString = rowString + "<td>" + muniDict['offsets'][detailedClassName] + "</td>";
                }
            else if(col_category == 'net'){
                rowString = rowString + "<td>" + muniDict['nets'][colName] + "</td>";
                }
            else if(col_category == 'netadj'){
                var service = service.charAt(0).toUpperCase() + service.slice(1)
                var impact_col = service + ' impact'
                var offset_col = 'services_offset_' + service.toLowerCase()
                var net = muniDict['impacts'][impact_col] + muniDict['offsets'][offset_col]
                rowString = rowString + "<td>" + net * muniDict['pop'] + "</td>";

                // add the net * pop value here to the nets*pop object
                nets_times_pop[service] += net * muniDict['pop'];
                }
            else {
                console.log("ERROR handling column name for impact row : " + colName);
            }
        });

        build_total_row_template = false  // set to false so we only do one row
        rowString = rowString + "</tr>";
        $tableLast.append(rowString);
    }

    // add a 'total' row for the adjusted net columns.
    console.log(total_row)
    var total_row_html = '<tr class="totals">';
    for(var row_index in total_row){
        var row_key = total_row[row_index];
        console.log(row_key);
        var total_data = nets_times_pop[row_key];
        if (total_data != undefined){
            total_row_html += "<td>" + total_data + "</td>";
        }
        else {
            total_row_html += "<td>" + row_key + "</td>";
        }
    }
    total_row_html += "</tr>"
    $tableLast.append(total_row_html)
    updateHydrologicalTotals();
    roundNumbers();
}

function formatNetColumns(){
    //This function checks to see if any net columns have negative values.  If
    //so, we change the class of the cell to 'negative'.  Otherwise, we change
    //the class of the cell to 'positive'

    //Search for all net columns.  This is noted by the 'net' class.
    //Also search for population-adjusted net columns, which have the 'population' class
    $('.net, .population').each(function(){
        //Get the index for this column.
        var col_index = $(this).index() + 1;

        //Get the table associated with this specific .net class and get all of
        //the table data associated with this index.
        $(this).closest('table').find('td:nth-child(' + col_index + ')').each(function(){
            //get the numeric value frm the table data.
            var value = $(this).text().split(',').join('');
            $(this).removeClass('negative');
            $(this).removeClass('positive');
            if (value == '--'){
                // do nothing.  We' don't want to set a class.
            } else if (value < 0){
                $(this).addClass('negative');
            } else {
                $(this).addClass('positive');
            };
        });
    });
}

function formatNumbers() {
    //This function checks to see if any columns should have
    //numbers formatted in scientific notation

    //Search for class names of scientific which indicate the column
    //should be represented in scientific notation
    $('.scientific').each(function(){
        //console.log($(this).index());
        //Get the index for the column the class name is found at.
        //Add 1 because 'nth-child' below starts indexing at 1
        var col_index = $(this).index() + 1;
        //Get the table associated with class scientific, find all
        //table data with the same index and iterate over
        $(this).closest('table').find("td:nth-child("+col_index+")").each(function(){
            //Get html value from table data
            var value = $(this).text();
            //console.log(value);
            //Make sure the value is a number to operate properly on
            if ($.isNumeric(value)){
                //Cast and set html value to exponential format
                $(this).html(parseFloat(value).toExponential());
            }
        });
    });
}

function roundNumbers() {
    //This function checks to see if any columns should have
    //numbers rounded to a decimal place between 0 - 9

    //Search for class names of 'round' which indicate the column
    //data below that header should be rounded to a certain
    //decimal place
    $('th[class*=round]').each(function(){
        //Get the 'round' class name as a string in an array
        var class_dig = $(this).attr('class').match('round[0-9]');
        //Get the string from the array
        var round_str = class_dig[0];
        //The last character of the class name should be an integer
        //value between 0-9.
        var dig = round_str[round_str.length - 1];

        //console.log(round_str);
        //console.log(dig);

        //Get the index for the column the class name is found at.
        //Add 1 because 'nth-child' below starts indexing at 1
        var col_index = $(this).index() + 1;
        //Get the table associated with class round, find all
        //table data with the same index and iterate over
        $(this).closest('table').find("td:nth-child("+col_index+")").each(function(){
            //Get html value from table data
            var value = $(this).text();
            //console.log(value);
            //Make sure the value is a number to operate properly on
            if ($.isNumeric(value)){
                //Cast and set html value to fixed decimal
                $(this).html(parseFloat(value).toFixed(dig));
            }
        });
    });
}

function commaSeparateNumbers() {
    //Iterate over each table data element
    $('td').each(function(){
        //Get html value from table data
        var value = $(this).text();
        //Make sure the value is a number to operate properly on
        if ($.isNumeric(value)){
            //Convert value to string and split on a decimal if found
            var parts = value.toString().split(".");
            //Take the value left of the decimal and add commas in
            //every 3rd place
            parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ",");
            //Join the value right of the decimal back on
            var result = parts.join(".");
            //Set commas separated value
            $(this).html(result);
        }
    });
}

function centerColumns() {
    $('table tr th.tdcenter').each(function() {
        console.log(this);
        col_index = $(this).index() + 1;
        $(this).closest('table').find('tr td:nth-child(' + col_index + ')').each(function() {
            $(this).addClass('center');
        });
    });
}

function checkSomeBoxes(parcel_id_list) {
    var parcel_set = new Set(parcel_id_list);
    $("#parcel_table").find('tr').each(function(){
        var row_id = parseInt($(this).find('td:first').text());
        if (parcel_set.has(row_id)){
            $(this).find('td.checkbox').find('input').prop('checked', true);
        }
    });

}

function checkAllBoxes(enable) {
    $("#parcel_table").find('td.checkbox').find('input').each(function(){
        $(this).prop('checked', enable);
    });
}

function exportToCSV() {
    var $table = $('#parcel_table');
    var filename = 'parcels.csv';

    var $rows = $table.find('tr:has(th),tr:has(td)'),

    // Temporary delimiter characters unlikely to be typed by keyboard
    // This is to avoid accidentally splitting the actual contents
    tmpColDelim = String.fromCharCode(11), // vertical tab character
    tmpRowDelim = String.fromCharCode(0), // null character

    // actual delimiter characters for CSV format
    colDelim = '","',
    rowDelim = '"\r\n"',

    // Grab text from table into CSV formatted string
    csv = '"' + $rows.map(function (i, row) {
        var $row = $(row),
            $cols = $row.find('th,td');

        return $cols.map(function (j, col) {
            var $col = $(col);
            if ($col.has('input:checkbox') == true) {
                text = $($col.find("input")[0]).attr("value");
            } else {
                text = $col.text();
            }

            return text.replace('"', '""'); // escape double quotes

        }).get().join(tmpColDelim);

    }).get().join(tmpRowDelim)
        .split(tmpRowDelim).join(rowDelim)
        .split(tmpColDelim).join(colDelim) + '"',

    // Data URI
    csvData = 'data:application/csv;charset=utf-8,' + encodeURIComponent(csv);

    $(this)
        .attr({
        'download': filename,
            'href': csvData,
            'target': '_blank'
    });
}

function cleanESTables() {
    // remove all data rows from the ES tables.
    $('#muni_table,#global_benefits_table').each(function() {
        console.log(this);
        $(this).find('tbody tr').each(function() {
            console.log(this);
            $(this).remove();
        });
    });
}

function rebuildGlobalTable(){
    var $globalTable = $('#global_benefits_table');

}
