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

	if ($_GET['format'] == "json") {
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

	}
?>

