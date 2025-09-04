<?php
    function getRequestHeaders() {
        $headers = array();
        foreach($_SERVER as $key => $value) {
            if (substr($key, 0, 8) <> 'SSL_ECH_') {
                continue;
            }
            $headers[$key] = $value;
        }
        return $headers;
    }

    $headers = getRequestHeaders();

    /*
     * Log: time, HMAC(client IP), URL, ech-status, user-agent
     * We'll store a keyed-hash of the client IP. We could
     * till locally find the IP from other logs if we wanted,
     * but this'll mean we can just publish this log.
     */
    function do_hmac($plain) {
        $keyfile="/var/extra/client-ip.key";
        $key=file_get_contents($keyfile);
        if ($key===FALSE) {
            return "no-key";
        }
        $hmac = hash_hmac('sha256', $plain, $key, $as_binary=false);
        return $hmac;
    }
    function client_ip() {
        if (!empty($_SERVER['HTTP_X_FORWARDED_FOR'])) {
            return $_SERVER['HTTP_X_FORWARDED_FOR'];
    } else if (!empty($_SERVER['HTTP_CLIENT_IP'])) {
            return $_SERVER['HTTP_CLIENT_IP'];
        } else {
            return $_SERVER['REMOTE_ADDR'];
        }
    }
    /* we don't expect to be v. busy but just in case */
    function addone($logline) {
        $filename="/var/extra/echstat.csv";
        $gotlock=false;
        $attempts=0;
        while ($attempts<5 && !$gotlock) {
            $fp=fopen($filename,"a");
            if ($fp!==false && flock($fp, LOCK_EX | LOCK_NB)) {
                $gotlock=true;
                $rv=fwrite($fp,$logline . "\n");
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
    function ua_string() {
        if (!empty($_SERVER["HTTP_USER_AGENT"])) {
            return $_SERVER["HTTP_USER_AGENT"];
	} else {
            return "no-user-agent";
	}
    }
    $logstring = "";
    $logstring = $logstring . "|" . date(DATE_RFC3339);
    $logstring = $logstring . "|" . do_hmac(client_ip());
    $logstring = $logstring . "|" . "https://$_SERVER[HTTP_HOST]$_SERVER[REQUEST_URI]";
    $logstring = $logstring . "|" . $_SERVER["SSL_ECH_STATUS"];
    $logstring = $logstring . "|" . $_SERVER["SSL_ECH_INNER_SNI"];
    $logstring = $logstring . "|" . $_SERVER["SSL_ECH_OUTER_SNI"];
    $logstring = $logstring . "|" . ua_string();
    addone($logstring);

    if (!empty($_GET['format']) && $_GET['format'] == "json") {
        header('Content-Type: application/json; charset=utf-8');
        echo "{";
        foreach ($headers as $header => $value) {
            if ($header=="SSL_ECH_STATUS" && ($value=="success" || $value=="SSL_ECH_STATUS_SUCCESS")) {
                echo "\"$header\": \"$value\", ";
            } else if ($header=="SSL_ECH_STATUS" && $value!="success" && $value!="SSL_ECH_STATUS_SUCCESS") {
                echo "\"$header\": \"$value\",";
            } else { 
                echo "\"$header\": \"$value\",";
            }
        }
        echo "\"date\": \"" . date(DATE_ATOM) . "\",";
        echo "\"config\": \"". $_SERVER['SERVER_NAME'] . "\"" ;
        echo "}";

    } else {

        foreach ($headers as $header => $value) {
            if ($header=="SSL_ECH_STATUS" && ($value=="success" || $value=="SSL_ECH_STATUS_SUCCESS")) {
                echo "$header: $value \n";
            } else if ($header=="SSL_ECH_STATUS" && $value!="success" && $value!="SSL_ECH_STATUS_SUCCESS") {
                echo "$header: $value \n";
            } else { 
                echo "$header: $value\n";
            }
        }
        echo "date: " . date(DATE_ATOM) . "\n";
        echo "config: ". $_SERVER['SERVER_NAME'] . "\n";

	//$arr = get_defined_vars();
	//print($arr);
	//var_dump($_SERVER);
	///foreach (getallheaders() as $name => $value) {
	//echo "$name => $value \n";
	//}

    }

?>

