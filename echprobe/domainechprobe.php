<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
    "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<title>DEfO ECH Domain Name Check</title>
</head>
<!-- Background white, links blue (unvisited), navy (visited), red
(active) -->
<body bgcolor="#FFFFFF" text="#000000" link="#0000FF"
vlink="#000080" alink="#FF0000">
<h1>DEfO ECH Domain Name Check</h1>

<?php
    /*
     * General functions
     */

    function load_list() {
        $filename="/var/extra/echdomains.csv";
        if (!file_exists($filename)) {
            print("<p>Error 982, Can't open file</p>\n");
            return FALSE;
        } else {
            $thelist=array();
            $row = 0;
            if (($handle = fopen($filename, "r")) !== FALSE) {
                while (($data = fgetcsv($handle, 1000, ",")) !== FALSE) {
                    $thelist[$row]=$data;
                    $row++;
                }
                fclose($handle);
                return $thelist;
            } else {
                return FALSE;
            }
        }
    }

    function check_domain($d) {
        if (!filter_var($d, FILTER_VALIDATE_DOMAIN, FILTER_NULL_ON_FAILURE)) 
            return FALSE;
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

    function get_domain_info($d) {
        $astr="";
        $cmd="kdig +json https " . escapeshellcmd($d);
        $rdata=shell_exec($cmd);
        //var_dump($rdata);
        $jrdata=json_decode($rdata, true);
        echo "<p></p>\n";
        //var_dump($jrdata);
        if (isset($jrdata['answerRRs'])) {
            $crrds=count($jrdata['answerRRs']);
            if ($crrds==1) {
            $rrd=$jrdata['answerRRs'][0];
            if (isset($rrd['rdataHTTPS']))
            $astr=$rrd['rdataHTTPS'];
            } else {
                $astr="[ ";
                for ($rrdi=0;$rrdi<$crrds;$rrdi++) {
                    $rrd=$jrdata['answerRRs'][$rrdi];
                    if (isset($rrd['rdataHTTPS']))
                        $astr.=$rrd['rdataHTTPS']." ]";
            if ($rrdi<$crrds-1)
                    $astr.=" [";
                }
            }
            //var_dump($astr);
            return $astr;
        }
        return "no";
    }

    function try_ech($u) {
	$doh_url="https://one.one.one.one/dns-query";
        $cmd="curl -vvv --ech hard --doh-url " .$doh_url . " " . escapeshellcmd($u) . " 2>&1";
	var_dump($cmd);
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
                $rv=fwrite($fp,"$date,$dom,$ech_stat,$has_ech,$https_rr\n");
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
    echo "<p>".date(DATE_ATOM)."</p>";
    // Trim array values using this function "trim_value"
    function trim_value(&$value) {
        $value = trim($value);    // remove whitespace and related from beginning and end of the string
    }
    array_filter($_POST, 'trim_value');    // the data in $_POST is trimmed
    $postfilter =    // set up the filters to be used with the trimmed post array
        array(
            // we are using this in the url
            'domain2check' => array('filter' => FILTER_SANITIZE_STRING, 'flags' => FILTER_FLAG_STRIP_LOW),    
        );
    // must be referenced via a variable which is now an array that takes the place of $_POST[]
    $rparr = filter_var_array($_POST, $postfilter);    
?>

<p>Please enter a DNS domain name to check for ECH.</p>

<?php
    // load in out list
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
    if ($entries<100 && isset($rparr["domain2check"])) {
        // overall check of goodness
        $good2go=true;
        $domorig=strtolower($rparr["domain2check"]);
        $dom=stripleadingwww($domorig);
        if ($dom===FALSE || $dom==false) {
            echo "<h3>Error</h3><p>\"".$domorig."\" doesn't appear to be a good DNS name.</p>\n";
            $good2go=false;
        } else {
            $fakeemail="foo@".$dom;
            if (!filter_var($fakeemail, FILTER_VALIDATE_EMAIL)) {
                echo "<h3>Error</h3><p>\"".$dom."\" doesn't appear to be a DNS name.</p>\n";
                $good2go=false;
            }
        }
        // check domain is real
        if ($good2go) {
            var_dump($dom);
            $domcheck=check_domain($dom);
            if ($domcheck===FALSE || $domcheck==FALSE) {
                echo "<h3>Error</h3><p>".$dom." doesn't appear to be real.</p>\n";
                $good2go=false;
            }
            if ($good2go) {
                $has_https=get_domain_info($dom);
                if (str_contains($has_https,"ech="))
                    $has_ech=1;
                else
                    $has_ech=0;
                $ech_status=try_ech("https://$dom/");
                $date=date(DATE_ATOM);
                $arv=addone($date, $dom, $ech_status, $has_ech, $has_https);
                if ($arv) {
                    echo "<h3>Success</h3><p>Added $dom to list </p>";
                    // extend
                    $plist[$entries][0]=$date;
                    $plist[$entries][1]=$dom;
                    $plist[$entries][2]=$ech_status;
                    $plist[$entries][3]=$has_ech;
                    $plist[$entries][4]=$has_https;
                    $entries++;
                } else {
                    echo "<h3>Error</h3><p>File write failed, try again in a bit.</p>";
                }
            }
        }
    } 
    
?>


<h3>Choose your target:</h3>

<form method="POST">
    DNS name: <input name="domain2check" type="text"/>
    <input type="submit" value="Submit">
</form>

<p>Here are the services already chosen:</p>


<?php
    /* display the file content */
    if ($entries>1) {
        echo "<table border=\"1\">\n";
        echo "<tr><th>Num</th><th>Date</th><th>Domain</th><th>ECH Status</th><th>Has ECH?</th><th>HTTPS RR</th></tr>\n";
        for ($row=1;$row<$entries;$row++) {
            $num=count($plist[$row]);
            echo "<tr>";
            echo "<td>".$row."</td>";
            echo "<td>".$plist[$row][0]."</td>";
            echo "<td>".$plist[$row][1]."</td>";
            echo "<td>".$plist[$row][2]."</td>";
            echo "<td>".$plist[$row][3]."</td>";
            echo "<td>".$plist[$row][4]."</td>";
            echo "</tr>\n";
        }
        echo "</table>\n";
    }

?>

</body>
</html>

