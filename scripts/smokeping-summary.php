<!DOCTYPE html>
<html lang="en">
<style>
    table {
        display: block;
        max-width: 90%;
        overflow: auto; <!-- Available options: visible, hidden, scroll, auto -->
    {
    .center-tab {
        margin-left: auto;
        margin-right: auto;
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
<h1>DEfO ECH Smokeping-like summary</h1>

<p>This page displays the results from attempting
ECH with chromium, curl, firefox, golang, rustls and python
with each of the URLs shown, for the last 6
hours.  (Runs are done hourly via cron.) "Expected" means that we
saw the expected result, which, for some of these URLs, means we saw the
expected error. If everything goes entirely to plan, then you'll see the
same icons in the "expected" column as in the time-based columns. However,
for some error cases, we might not be able to tell if we got the expected
error or something else went wrong. In other words, we can spot problems
with this table, but can't be sure of fully-clean test runs. Where there
is more information about failures available, you can see that if you
hover over the client icon.</p>

<p>At the time of writing, there are a lot of unexpected results reported
below for firefox and chromium. These results are generated using selenium and
headless browsers, though desktop browsers seem to do better than indicated, as
you can see if you try our <a href="iframe_tests.html">iframe tests</a> in your
own browser, so it could be some issue with selenium or headless browser tests.
We're investigating.</p>

<?php

    $summaryfile="/var/extra/smokeping/summary.html";
    echo "<p>The time now is:".date(DATE_ATOM);
    echo " Table generated at:".date(DATE_ATOM,filemtime($summaryfile))."</p>";

    $cliarr=array("chromium", "curl", "firefox", "golang", "rustls", "python");

    echo '<table class="center-tab" border="0"><caption>Version Info (hover over icon for more)</caption>';
    foreach ($cliarr as $cli) {
        $subdirs=glob("/var/extra/smokeping/".$cli."-runs/*",GLOB_ONLYDIR);
        $newest=end($subdirs);
        $nb=basename($newest);
        $fullverinfo=file_get_contents($newest."/".$nb.".".$cli.".ver");
        $vfile=$newest."/".$nb.".".$cli.".ver";
        $verinfo=fgets(fopen($vfile,"r"));
        echo '<tr>';
        echo '<td align="right">'.$cli.': </td>';
        echo '<td align="left"><img width="20" height="20" src="'.$cli.'-logo.png" title="'.$fullverinfo.'" alt="'.$cli.'"/> '.$verinfo.'</td>';
        echo '</tr>';
    }
    echo "</table><br/>";

    # show run data
    $runtable=file_get_contents($summaryfile);
    echo $runtable;
?>

<br> This fine domain brought to you by <a href="https://defo.ie/">DEfO.ie</a> 
<br> a <a href="https://tolerantnetworks.com/">Tolerant Networks Limited</a> production.
<br> Last modified: 2024-12-02, but who cares?</font> 

</body>
</html>

