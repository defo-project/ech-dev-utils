<html>

<head><title>Welcome to defo.ie</title>

<meta name="referrer" content="no-referrer">

</head>

<body bgcolor="#ffffff" width=600>
<center>
<TABLE BORDER=0 CELLSPACING=1 CELLPADDING=1>
<!-- First row -->
<TR>
   <!-- Embedded Table -->
   <TABLE BORDER=0 CELLSPACING=4 CELLPADDING=4> 
   <!-- First row -->
   <TR>
      <TD ALIGN=center>
         <IMG SRC="tnlogo.jpg" ALT="Tolerant Networks Logo " >
      </TD>
   </TR>
   </TABLE>
</TR>
</TABLE>
</center>
<hr width=600>
<br>
<!-- **************************************** -->
<!-- End header -->
<!-- **************************************** -->
<center><Table width=600 border=0><P><h1>defo.ie</h1>

    <p>This is the defo.ie ECH check page that tells you if ECH was used.</p>

    <p> PHP sez it's  <?php echo date('l jS \of F Y h:i:s A'); ?>(UTC)</p>

    <p><?php
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
        ?>
    </p>
</TD>
</TR>
<center>
</P>
</table>
 
<br> This fine domain brought to you by <a href="https://tolerantnetworks.com/">Tolerant Networks Limited</a>.
<br> Last modified: 2022-03-18, but who cares?</font> 

</body>
</html>

