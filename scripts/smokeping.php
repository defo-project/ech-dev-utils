<!DOCTYPE html>
<html lang="en">
<style>
    table {
        display: block;
        max-width: 90%;
        overflow: scroll; <!-- Available options: visible, hidden, scroll, auto -->
    }
</style>
<head>
<meta charset="utf-8">
<title>DEfO ECH Smokeping-like Check</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
</head>

<body bgcolor="#ffffff" width=600>
<center> <IMG SRC="defologo.png" ALT="DEfO Logo " > </center>
<hr width=600>
<br>
<!-- **************************************** -->
<!-- End header -->
<!-- **************************************** -->
<center>
<h1>DEfO ECH Smokeping-like Check</h1>

<p>The (server-side) script on this page displays the results from attempting
ECH (via curl) with each of the URLs shown, on the date shown.</p>

<!--
<form method="POST">
<fieldset style="width:60%">
<legend align="center">DNS name and port (default: 443)</legend>
    name: <input name="domain2check" type="text" size="20"/>
    port: <input name="port2check" type="number" size="5" maxlength="5" value="443"/>
    <input type="submit" value="Submit">
</fieldset>
</form>
-->

<?php
    /*
     * General functions
     */

    $topdir="/var/extra/smokeping/runs";
    $thisone="";
    $runlist=glob($topdir . '/*' , GLOB_ONLYDIR);
    echo "<p>";
    var_dump($runlist);
    echo "</p><p>";
    $run=end($runlist);
    var_dump($run);
    echo "</p><p>";
    $runtime=basename($run);
    var_dump($runtime);
    echo "</p>";
    $runtable=file_get_contents($run."/".$runtime.".html");
    echo $runtable;
?>

<?php
    //echo "<p>".date(DATE_ATOM)."</p>";
    // Trim array values using this function "trim_value"
    function trim_value(&$value) {
        $value = trim($value);    // remove whitespace and related from beginning and end of the string
    }
    array_filter($_POST, 'trim_value');    // the data in $_POST is trimmed
    $postfilter =    // set up the filters to be used with the trimmed post array
        array(
            // we are using this in the url
            'run' => array('filter' => FILTER_SANITIZE_STRING, 'flags' => FILTER_FLAG_STRIP_LOW),    
        );
    // must be referenced via a variable which is now an array that takes the place of $_POST[]
    $rparr = filter_var_array($_POST, $postfilter);    
?>

<br> This fine domain brought to you by <a href="https://defo.ie/">DEfO.ie</a> 
<br> a <a href="https://tolerantnetworks.com/">Tolerant Networks Limited</a> production.
<br> Last modified: 2024-07-31, but who cares?</font> 

</body>
</html>

