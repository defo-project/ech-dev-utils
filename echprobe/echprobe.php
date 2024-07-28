#!/usr/bin/php
<?php

$doh_url="https://one.one.one.one/dns-query";

function is_url($u) {
    if (!filter_var($u, FILTER_VALIDATE_URL, FILTER_NULL_ON_FAILURE))
        return FALSE;
    $pattern = '/^(https?:\/\/)?([\da-z.-]+)\.([a-z.]{2,6})([\/\w.-]*)*\/?$/';
    if (!preg_match($pattern, $u))
        return FALSE;
    return TRUE;
}

function is_domain($d) {
    /* we only care about https */
    if (!filter_var($d, FILTER_VALIDATE_DOMAIN, FILTER_NULL_ON_FAILURE)) 
        return FALSE;
    if (!preg_match("/^([a-zd](-*[a-zd])*)(.([a-zd](-*[a-zd])*))*$/i", $d) //valid characters check
        || !preg_match("/^.{1,253}$/", $d) //overall length check
        || !preg_match("/^[^.]{1,63}(.[^.]{1,63})*$/", $d)) //length of every label
        return FALSE;
    return TRUE;
}

function get_domain_info($d) {
    /* // simple/quick check for existence, but fails sometimes
    $out=dns_get_record($d);
    if ($out === FALSE || $out == FALSE)
        return;
     */
    $cmd="kdig +json https " . escapeshellcmd($d);
    $rdata=shell_exec($cmd);
    return $rdata;
}

function try_ech($u) {
    $cmd="curl --ech hard --doh-url=" .$doh_url . " " . escapeshellcmd($u);
    $cdata=shell_exec($cmd);
    return $cdata;
}

if ($argc != 2)
    return;

$v=filter_var($argv[1], FILTER_SANITIZE_URL);
if ($v === FALSE || $v == "") {
    echo "Nothing left\n";
} else if (is_url($v)) {
    echo "url: " . $v . "\n";
    $pu=parse_url($v);
    var_dump($pu);
    if ($pu['scheme'] != 'https') {
        echo "Error only HTTPS URls handled (not " . $pu['scheme'] . ")";
        return;
    }
    $d=$pu['host'];
} else {
    $d=$v;
    $v="https://" . $d . "/";
}

if (is_domain($d)) {
    echo "domain: " . $d . "\n";
    $rdata = get_domain_info($d);
    var_dump($rdata);
} else {
    echo "Unknown\n";
    return;
}

echo "trying ech\n";
$cdata=try_ech($v);
var_dump($cdata);


/*
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

        foreach ($headers as $header => $value) {
            if ($header=="SSL_ECH_STATUS" && $value=="success") {
                echo "$header: $value <img src=\"greentick-small.png\" alt=\"good\" /> <br/>\n";
            } else if ($header=="SSL_ECH_STATUS" && $value!="success") {
                echo "$header: $value <img src=\"redx-small.png\" alt=\"bummer\" /> <br/>\n";
            } else { 
                echo "$header: $value <br />\n";
            }
        }
*/

?>
