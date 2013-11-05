$(document).ready(function()
        {
            sum_constant_total();
        });
        
$(function(){
    
    $('[name="cb"]').change(function() {
        
        $table = $(this).closest('table');

        //$('.checkTot').html("0");
        $table.find('.checkTot').html("0");
        //$('[name="cb"]:checked').closest('tr').find('.rowDataSd').each(function() {
        $table.find('[name="cb"]:checked').closest('tr').find('.rowDataSd').each(function() {
            var $td = $(this);
            //var $sumColumn = $(this).find('tr.checkTotal td:eq(' + $td.index() + ')');
            var $sumColumn = $table.find('tr.checkTotal td:eq(' + $td.index() + ')');
            var currVal = $sumColumn.html() || 0;
            currVal = +currVal + +$td.html();
            $sumColumn.html(currVal);
            });
        
        });
});

function sum_constant_total() {
    
    $('table').each(function(){

        var totals_array = new Array();

        //var $dataRows=$("#my_table tr:not('.totalColumn')");
        var $dataRows=$(this).find("tr:not('.totalColumn')");

        $dataRows.each(function() {
            $(this).find('.rowDataSd').each(function(i){
                totals_array[i] = 0;
            });
        });
        
        $dataRows.each(function() {
            $(this).find('.rowDataSd').each(function(i){
                totals_array[i]+=parseInt( $(this).html());
            });
        });

        //$("#my_table td.totalCol").each(function(i){
        $(this).find("td.totalCol").each(function(i){
            $(this).html(totals_array[i]);
        });
    });
}
