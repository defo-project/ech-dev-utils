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
<title>DEfO ECH Domain Name Check</title>
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
<h1>DEfO ECH Domain Name Check</h1>

<p>The (server-side) script on this page checks whether an HTTPS resource
record (RR) is published for a given DNS domain and port (default port being
443), if so, whether there is an ECHConfigList published as part of that, and
whether or not ECH works with the web server at that name. That's done using
the `kdig` command on the server-side to check for HTTPS RRs, and `curl` with
our experimental ECH support enabled to test if ECH works.  (Note that `curl`
supports more ECH options than browsers, but does not support automated
re-tries via `retry-config` so the behaviour reported here will not quite match
what browsers exhibit.)</p>

<form method="POST">
<fieldset style="width:60%">
<legend align="center">DNS name and port (default: 443)</legend>
    name: <input name="domain2check" type="text" size="20"/>
    port: <input name="port2check" type="number" size="5" maxlength="5" value="443"/>
    <input type="submit" value="Submit">
</fieldset>
</form>

<!-- if the list gets too long we can just read in the last N lines of the flie-->

<?php
    /* number of entries in file */
    $file_entries = 0;

    /* General functions */
    function load_list() {
	global $file_entries;

        $filename="/var/extra/echdomains.csv";
        if (!file_exists($filename)) {
            print("<p>Error 982, Can't open file</p>\n");
            return FALSE;
        } else {
            $thelist=array();
            $row = 0;
            if (($handle = fopen($filename, "r")) !== FALSE) {
                while (($data = fgetcsv($handle, 1000, "|")) !== FALSE) {
                    $thelist[$row]=$data;
                    $row++;
                }
                fclose($handle);
		$file_entries = count($thelist);
                return array_slice($thelist, -50);
            } else {
                return FALSE;
            }
        }
    }

    function check_domain($d) {
        if (!filter_var($d, FILTER_VALIDATE_DOMAIN, FILTER_NULL_ON_FAILURE)) 
            return FALSE;
	/* strip trailing dots when checking, if present */
	$d=rtrim($d,'.');
        if (!preg_match("/^([a-z\d](-*[a-z\d])*)(.([a-z\d](-*[a-z\d])*))*$/i", $d) //valid characters check
            || !preg_match("/^.{1,253}$/", $d) //overall length check
            || !preg_match("/^[^.]{1,63}(.[^.]{1,63})*$/", $d)) //length of every label
            return FALSE;
        /* 
          * we need one of NS, A or AAAA to exist
          * note: clients that only have HTTPS RR ipv[46]hints won't pass
        $rtype=DNS_NS+DNS_A+DNS_AAAA;
        $res=dns_get_record($d,$rtype);
        if ($res===FALSE) return FALSE;
        if (count($res)==0) return FALSE;
          */
        return TRUE;
    }

    function get_https_rr($d,$p) {
        $astr="";
        /*
         * we use 1.1.1.1 here to be consistent with use of DoH
         * for curl below - without that we might get no HTTPS RR
         * from kdig but see ECH with curl work, if the HTTPS RR
         * has been published between a 1st and 2nd probe for
         * that name. (Because, our local stub might have an
         * negative answer cached for the name for an hour.)
         */
        if ($p==443) {
            $qn=$d;
        } else {
            $qn="_".$p."._https.".$d;
        }
        $cmd="kdig @1.1.1.1 +json https " . escapeshellcmd($qn);
        $rdata=shell_exec($cmd);
        //var_dump($rdata);
        $jrdata=json_decode($rdata, true);
        //echo "<p></p>\n";
        //var_dump($jrdata);
        if (isset($jrdata['answerRRs'])) {
            $crrds=count($jrdata['answerRRs']);
            if ($crrds==1) {
                $rrd=$jrdata['answerRRs'][0];
                if (isset($rrd['rdataHTTPS']))
                    $astr=$rrd['rdataHTTPS'];
                if (isset($rrd['rdataCNAME']))
                    return "cname";
            } else {
                $astr="[ ";
                for ($rrdi=0;$rrdi<$crrds;$rrdi++) {
                    $rrd=$jrdata['answerRRs'][$rrdi];
                    if (isset($rrd['rdataHTTPS']))
                        $astr.=$rrd['rdataHTTPS']." ]";
                    if (isset($rrd['rdataHTTPS']) && $rrdi<$crrds-1)
                        $astr.=" [";
                    if (isset($rrd['rdataCNAME']))
                        return "cname";
                }
            }
            //var_dump($astr);
            return $astr;
        }
        return "none";
    }

    function try_ech($u) {
        $doh_url="https://one.one.one.one/dns-query";
        // send an HTTP HEAD request - nicer but doesn't work everywhere...
        // $cmd="curl -I -H \"Connection: close\"-sv --ech hard --doh-url " .$doh_url . " " . escapeshellcmd($u) . " 2>&1";
        $cmd="curl -svo /dev/null --ech hard --doh-url " .$doh_url . " " . escapeshellcmd($u) . " 2>&1";
        //var_dump($cmd);
        $cdata=shell_exec($cmd);
        //var_dump($cdata);
        if (str_contains($cdata,"ECH: result: status is succeeded"))
            return 1;
        return 0;
    }

    function addone($date, $dom, $ech_stat, $has_ech, $https_rr) {
        $filename="/var/extra/echdomains.csv";
        $gotlock=false;
        $attempts=0;
        while ($attempts<5 && !$gotlock) {
            $fp=fopen($filename,"a");
            if ($fp!==false && flock($fp, LOCK_EX | LOCK_NB)) {
                $gotlock=true;
                // do your file writes here
                $rv=fwrite($fp,"$date|$dom|$ech_stat|$has_ech|$https_rr\n");
                fflush($fp);
                flock($fp, LOCK_UN); // unlock the file
                fclose($fp);
                if ($rv===FALSE) $gotlock=false;
            } else {
                // flock() returned false, no lock obtained
                print "Could not lock $filename!\n";
                $attempts++;
                if ($fp!==false) fclose($fp);
                if ($attempts<5) sleep(1);
            }
        }
        return $gotlock;
    }

    
    function startsWith($haystack, $needle) {
        return substr_compare($haystack, $needle, 0, strlen($needle)) === 0;
    }

    function stripleadingwww($name) {
        if (startsWith($name,"www.")) {
            $shorter=substr($name,4); 
            if ((strpos($shorter, ".") !== false) && (strlen($shorter)>=4) ) {
                return $shorter;
            } else {
                return FALSE;
            }
        } 
        return $name;
    }

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
            'domain2check' => array('filter' => FILTER_SANITIZE_STRING, 'flags' => FILTER_FLAG_STRIP_LOW),    
            'port2check' => array('filter' => FILTER_SANITIZE_NUMBER_INT, 'flags' => FILTER_FLAG_STRIP_LOW),    
        );
    // must be referenced via a variable which is now an array that takes the place of $_POST[]
    $rparr = filter_var_array($_POST, $postfilter);    
?>

<?php
    // load in our list
    $plist=load_list();
    if ($plist===FALSE || $plist==FALSE) {
        print("<p>Error 1982, Can't open file</p>\n");
        $entries=0;
    } else { 
        $entries=count($plist);
    }
    /*
     * If handling a POST... then handle the POST data...
     */
    $port=443;
    if ($entries<100 && isset($rparr["domain2check"])) {
        // overall check of goodness
        $good2go=true;
        // Stripping www. isn't right for this test.
        //$domorig=strtolower($rparr["domain2check"]);
        //$dom=stripleadingwww($domorig);
        $dom=strtolower($rparr["domain2check"]);
        if ($dom===FALSE || $dom==false) {
            echo "<h3>Error</h3><p>\"".$domorig."\" doesn't appear to be a good DNS name.</p>\n";
            $good2go=false;
        } else {
            $fakeemail=rtrim("foo@".$dom,'.');
            if (!filter_var($fakeemail, FILTER_VALIDATE_EMAIL)) {
                echo "<h3>Error</h3><p>\"".$dom."\" doesn't appear to be a DNS name.</p>\n";
                $good2go=false;
            }
        }
        if (isset($rparr['port2check'])) {
            $portchosen=(int)$rparr['port2check'];
            if (!is_int($portchosen) || $portchosen <= 0 || $portchosen > 65536) {
                echo "<h3>Error</h3><p>\"".$portchosen."\" is out of range (0,65535].</p>\n";
                $good2go=false;
            } else {
                $port=$portchosen;
            }
        }
        // check domain is real
        if ($good2go) {
            //var_dump($dom);
            $domcheck=check_domain($dom);
            if ($domcheck===FALSE || $domcheck==FALSE) {
                echo "<h3>Error</h3><p>".$dom." doesn't appear to be real.</p>\n";
                $good2go=false;
            }
            if ($good2go) {
                $has_https=get_https_rr($dom, $port);
                if (str_contains($has_https,"ech="))
                    $has_ech=1;
                else
                    $has_ech=0;
                $domstr=$dom;
                if ($port!=443)
                    $domstr=$dom.":".$port;
                $url="https://$domstr/";
                $ech_status=try_ech($url);
                $date=date(DATE_ATOM);
                if ($has_https!="none") {
                    $arv=addone($date, $domstr, $ech_status, $has_ech, $has_https);
                    // extend
                    $plist[$entries][0]=$date;
                    $plist[$entries][1]=$domstr;
                    $plist[$entries][2]=$ech_status;
                    $plist[$entries][3]=$has_ech;
                    $plist[$entries][4]=$has_https;
                    $entries++;
                    $file_entries++;
                }
		if ($has_https=="cname")
                    echo "<h3>$domstr seems to be a CNAME, we don't chase those for display</h3>";
		if ($ech_status==1)
                    echo "<h3>ECH success</h3><p>Added $domstr to list </p>";
                else if ($has_ech==1)
                    echo "<h3>ECH but failed</h3><p>Added $domstr to list </p>";
                else if ($has_https!="none")
                    echo "<h3>Has HTTPS but no ech=</h3><p>Added $domstr to list </p>";
                else
                    echo "<h3>$domstr doesn't seem to publish an HTTPS RR</h3>";
            }
        }
    } 
    
?>


<h1>Recent services tested, that have some HTTPS RR</h1>

<?php
    /* display the file content */
    if ($entries>1) {
        echo "<table border=\"1\" style=\"width:80%\">\n";
        echo "<tr>";
        echo "<th align=\"center\">Num</th>";
        echo "<th>Date</th>";
        echo "<th>Domain</th>";
        echo "<th align=center>ECH Status</th>";
        echo "<th>Has ECH?</th>";
        echo "<th align=left>HTTPS RR</th>";
        echo "</tr>\n";
        for ($row=$entries-1;$row>=0;$row--) {
            $num=count($plist[$row]);
            echo "<tr>";
            echo "<td>".($file_entries-$entries+$row+1)."</td>";
            echo "<td>".$plist[$row][0]."</td>";
            echo "<td>".$plist[$row][1]."</td>";
            echo "<td>".$plist[$row][2]."</td>";
            echo "<td>".$plist[$row][3]."</td>";
            echo "<td align=left>".$plist[$row][4]."</td>";
            echo "</tr>\n";
        }
        echo "</table>\n";
    }

    echo "<p>File entries: " . $file_entries . "</p>";
?>
 
<br> This fine domain brought to you by <a href="https://defo.ie/">DEfO.ie</a> 
<br> a <a href="https://tolerantnetworks.com/">Tolerant Networks Limited</a> production.
<br> Last modified: 2024-07-31, but who cares?</font> 

</body>
</html>

