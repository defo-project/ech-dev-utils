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
ECH (via curl) with each of the URLs shown, for the time of the run shown.
Currently, runs are done hourly via cron. Note that "expected" means that we
got the expected result, which, for some of these URLs, means we saw the
expected error.</p>

<?php

    //echo "<p>".date(DATE_ATOM)."</p>";
    // Trim array values using this function "trim_value"
    function trim_value(&$value) {
        $value = trim($value);    // remove whitespace and related from beginning and end of the string
    }
    array_filter($_GET, 'trim_value');    // the data in $_GET is trimmed
    $postfilter =    // set up the filters to be used with the trimmed post array
        array(
            // we are using this in the url
            'runtime' => array('filter' => FILTER_SANITIZE_STRING, 'flags' => FILTER_FLAG_STRIP_LOW),    
        );
    // must be referenced via a variable which is now an array that takes the place of $_POST[]
    $rparr = filter_var_array($_GET, $postfilter);    

    $topdir="/var/extra/smokeping/runs";
    $runlist=glob($topdir . '/*' , GLOB_ONLYDIR);

    $runind=0;
    $numruns=count($runlist);
    if ($numruns>0) {
        $runind=$numruns-1;
    }

    //var_dump($runlist);
    $first=reset($runlist);
    //var_dump($first);
    $last=end($runlist);
    //var_dump($last);

    $setfromurl=0;
    if (isset($rparr['runtime'])) {
	$trt=$topdir."/".$rparr['runtime'];
	// var_dump($trt);
	// sanity check
	if (strlen($trt) == strlen($last)
	    && (($key=array_search($trt,$runlist,true))!==false)) {
	    $thisrun=$trt;
	    //var_dump($thisrun);
    	    $setfromurl=1;
	    //var_dump($key);
	    $runind=$key;
	}
    }
    if ($setfromurl!=1) {
	$thisrun=$last;
    }
    $runtime=basename($thisrun);
    // present run
    //var_dump($runtime);
    $prevstr="<p>prev</p>";
    if ($runind>0) {
    	$prevtime=basename($runlist[$runind-1]);
    	//var_dump($prevtime);
    	$prevurl="https://test.defo.ie/smokeping.php?runtime=".$prevtime;
    	$prevstr="<p><a href=\"".$prevurl."\">prev</a></p>";
    }
    $nextstr="<p>next</a>";
    if ($thisrun!=$last) {
    	$nexttime=basename($runlist[$runind+1]);
    	//var_dump($nexttime);
    	$nexturl="https://test.defo.ie/smokeping.php?runtime=".$nexttime;
    	$nextstr="<p><a href=\"".$nexturl."\">next</a></p>";
    }
    echo "<table border=\"0\" style=\"width:80%\"><tr>";
    echo "<td align=\"left\">$prevstr</td>";
    echo "<td width=\"50%\"><h2>Run: ".$runtime."</h2></td>";
    echo "<td align=\"right\">$nextstr</td>";
    echo "</tr></table>";
    $runtable=file_get_contents($thisrun."/".$runtime.".html");
    echo $runtable;
?>

<br> This fine domain brought to you by <a href="https://defo.ie/">DEfO.ie</a> 
<br> a <a href="https://tolerantnetworks.com/">Tolerant Networks Limited</a> production.
<br> Last modified: 2024-07-31, but who cares?</font> 

</body>
</html>

