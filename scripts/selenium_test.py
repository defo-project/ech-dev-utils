#!/usr/bin/env python3

# Check what happens with our test URLs and expected outcomes
# using a headless browser via selenium

# Install/prep instructions for debian/ubuntu - we need to run
# this in a python virtual environment, to set that up and do
# the installs:
# 
#    $ mkdir <somedir>
#    $ cd <somedir>
#    $ python3 -m venv venv
#    $ # the next command creates the environment to use, i.e., stick with that
#    $ # shell that says "(venv)" to do selenium stuff...
#    $ source venv/bin/activate 
#    (venv) $ pip install selenium webdriver-manager 
#    (venv) $ cp $HOME/code/ech-dev-utils/scripts/selenium_test.py .
#    (venv) $ python selemium-test.py
#
# We'll check that's been done before we start

import os, sys, time, csv, re, json, traceback
from datetime import datetime, timezone
from argparse import ArgumentParser
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.firefox_profile import FirefoxProfile
from selenium.webdriver.chrome.options import Options as chrome_Options 
from selenium.webdriver.chrome.service import Service as chrome_Service
from selenium.webdriver.firefox.options import Options as firefox_Options
from selenium.webdriver.firefox.service import Service as firefox_Service

# check result from an expected echstat JSON result
def echstat_check(result, expected):
    try:
        jres=json.loads(result)
    except:
        return "fail"
    jstat=jres['SSL_ECH_STATUS']
    if expected==0 and (jstat=="success" or jstat=="SSL_ECH_STATUS_SUCCES"):
        return "expected"
    # no distinguishing GREASE and fail here, nor retry-configs
    if expected!=0 and (jstat=="success" or jstat=="SSL_ECH_STATUS_SUCCES"):
        return "fail"
    return "fail"

def s_server_check(result, expected):
    # if it reports success we're good
    if 'ECH success:' in result:
        return "expected"
    return "fail"

def check_php_check(result, expected):
    # react to image file name for green check mark
    if 'greentick-small.png' in result:
        return "expected"
    return "fail"

def cf_check(result, expected):
    # react to image file name for green check mark
    if 'sni=encrypted' in result:
        return "expected"
    return "fail"

def bs_check(result, expected):
    # react to image file name for green check mark
    if 'You are using ECH' in result:
        return "expected"
    return "fail"

def gen_check(result, expected):
    return "unknown"

# add a record to the results file
def write_res(html_fp, csv_fp, num, url, res):
    if csv_fp is not None:
        # csv output
        print(str(num)+","+url+","+ res, file=csv_fp)
    if html_fp is not None:
        tab_row="<tr><td>"+str(num)+"</td><td>"+url+"</td><td>"+res+"</td></tr>"
        print(tab_row, file=html_fp)

# result handling table - we check the de-reff'd url vs. the url field
# then call the handler with the result if we get a match
# this requires knowledge of expected results and of course would break
# if server changes it's resopnses too much
result_handlers = [
    # our main test case...
    { 'url': '^https://.*/echstat.php[?]format=json$', 'handler': echstat_check },
    # openssl s_server tests
    { 'url': "^https://ss.test.defo.ie/stats$", 'handler': s_server_check },
    { 'url': "^https://sshrr.test.defo.ie/stats$", 'handler': s_server_check },
    { 'url': "^https://draft-13.esni.defo.ie:8413/stats$", 'handler': s_server_check },
    { 'url': "^https://draft-13.esni.defo.ie:8414/stats$", 'handler': s_server_check },
    # stuff using ech-check.php
    { 'url': "^https://.*/ech-check.php$", 'handler': check_php_check },
    { 'url': "^https://hidden.hoba.ie/$", 'handler': check_php_check },
    # non-s_server instances of draft-13.esni.defo.ie
    # lighttpd
    { 'url': "^https://draft-13.esni.defo.ie:9413/$", 'handler': check_php_check },
    # nginx
    { 'url': "^https://draft-13.esni.defo.ie:10413/$", 'handler': check_php_check },
    # apache
    { 'url': "^https://draft-13.esni.defo.ie:11413/$", 'handler': check_php_check },
    # haproxy shared-mode
    { 'url': "^https://draft-13.esni.defo.ie:12413/$", 'handler': check_php_check },
    # haproxy split-mode
    { 'url': "^https://draft-13.esni.defo.ie:12414/$", 'handler': check_php_check },
    # cloudflare's test server
    { 'url': "^https://crypto.cloudflare.com/cdn-cgi/trace$", 'handler': cf_check },
    # boringssl-driven test server
    { 'url': "^https://tls-ech.dev/$", 'handler': bs_check },
]

def get_handler(url):
    for rh in result_handlers:
        if re.match(str(rh['url']),url):
            return rh['handler']
    return None

def known_exception(browser, url, exc_value):
    # ff case for noaddr
    if "noaddr" in url and browser=="firefox" and "dnsNotFound" in str(exc_value):
        return True
    if "noaddr" in url and browser=="chrome" and "ERR_NAME_NOT_RESOLVED" in str(exc_value):
        return True
    if "noaddr" in url and browser=="chromium" and "ERR_NAME_NOT_RESOLVED" in str(exc_value):
        return True
    # a badly encoded ECHConfigList that causes chrome to barf
    if "bk2-ng" in url and browser=="chrome" and "ERR_INVALID_ECH_CONFIG_LIST" in str(exc_value):
        return True
    if "bk2-ng" in url and browser=="chromium" and "ERR_INVALID_ECH_CONFIG_LIST" in str(exc_value):
        return True
    return False

if __name__ == "__main__":
    parser = ArgumentParser(description="test ECH for a set of URLs via headless browser")
    parser.add_argument('--browser', default='firefox',
                        help="one of chrome, firefox, or safari")
    parser.add_argument('--urls_to_test', default='/var/extra/urls_to_test.csv',
                        help="CSV with URLs to test and expected outcomes")
    parser.add_argument('--results_dir', default='/var/extra/smokeping/browser-runs',
                        help='place to put time-based result files')
    parser.add_argument("-v", "--verbose", action="store_true",  help="additional output")
    parser.add_argument("-V", "--superverbose", action="store_true",  help="extra additional output")
    args = parser.parse_args()

    runtime=datetime.now(timezone.utc)
    runstr=runtime.strftime('%Y%m%d-%H%M%S')

    if args.superverbose:
        args.verbose=True

    myresults=args.results_dir+"/"+runstr
    if args.verbose:
        print("URLs:", args.urls_to_test)
        print("Browser:", args.browser)
        print("Run dir:",myresults)

    if not os.path.isdir(args.results_dir):
        print("Results dir doesn't exist - exiting")
        sys.exit(1)
    os.makedirs(myresults)
    if not os.path.isdir(myresults):
        print("Can't make results dir - exiting")
        sys.exit(1)

    html_fp=open(myresults+"/"+runstr+".html",'w')
    # table header
    print("<table border=\"1\" style=\"width:80%\">", file=html_fp)
    print("<tr>", file=html_fp)
    print("<th align=\"center\">Num</th>", file=html_fp)
    print("<th aligh=\"center\">URL</th>", file=html_fp)
    print("<th aligh=\"center\">Result</th>", file=html_fp)
    print("</tr>", file=html_fp)
    csv_fp=open(myresults+"/"+runstr+".csv",'w')
    # csv header
    print("num,url,result", file=csv_fp)
    # browser version
    bv_fp=open(myresults+"/"+runstr+"."+args.browser+".ver",'w')

    match args.browser:
        case 'safari':
            print("Safari has no ECH support yet - exiting")
            sys.exit(1)
        case 'firefox':
            from webdriver_manager.firefox import GeckoDriverManager
            firefox_profile = FirefoxProfile()
            firefox_profile.set_preference("network.trr.custom_uri", "https://one.one.one.one/dns-query")
            firefox_profile.set_preference("network.trr.mode", 3)
            options = firefox_Options()
            options.profile = firefox_profile
            options.add_argument('--headless')
            driver = webdriver.Firefox(service=firefox_Service(GeckoDriverManager().install()), options=options)
            # print version on line 1 and all caps after
            print(driver.capabilities['browserVersion'], file=bv_fp)
            print(driver.capabilities, file=bv_fp)
            # and whack out the FF special ECH enabling options too
            print("Custom ECH option:", "network.trr.custom_uri", "https://one.one.one.one/dns-query", file=bv_fp)
            print("Custom ECH option:", "network.trr.mode", "3", file=bv_fp)
        case 'chrome':
            from webdriver_manager.chrome import ChromeDriverManager
            options = chrome_Options()
            options.add_argument('--headless=new')
            driver = webdriver.Chrome(service=chrome_Service(ChromeDriverManager().install()), options=options)
            # print version on line 1 and all caps after
            print(driver.capabilities['browserVersion'], file=bv_fp)
            print(driver.capabilities, file=bv_fp)
            # currently no special ECH enabling options
        case 'chromium':
            from selenium.webdriver.chrome.service import Service as ChromeService
            options = chrome_Options()
            options.add_argument('--headless=new')
            service = ChromeService(executable_path="/usr/bin/chromedriver")
            driver = webdriver.Chrome(options = options, service = service)
            # print version on line 1 and all caps after
            print(driver.capabilities['browserVersion'], file=bv_fp)
            print(driver.capabilities, file=bv_fp)
            # currently no special ECH enabling options
        case _:
            print("unknown browser - exiting")
            sys.exit(1)

    # not sure if needed
    # wait = 0.75
    # print("Setting implicit wait period to", wait)
    # driver.implicitly_wait(wait)

    with open(args.urls_to_test) as csvfile:
        readCSV = csv.reader(csvfile, delimiter=',')
        urlnum=0
        for row in readCSV:
            gotexception=False
            # skip heading row
            if urlnum==0:
                urlnum=1
                continue
            theurl=row[0]
            if args.verbose:
                print("***********")
                print(str(urlnum), theurl)
            # FF default
            expected=int(row[3])
            if args.browser=='chrome' or args.browser=='chromium':
                expected=int(row[3])
            try:
                driver.get(theurl)
            except:
                gotexception=True
                exc_type, exc_value, exc_traceback = sys.exc_info()
                if args.verbose:
                    print(exc_type)
                    print(exc_value)
                    print(exc_traceback)
                # we know to expect some exceptions, e.g. for noaddr cases
                exc_str=str(exc_value).partition('\n')[0]
                if known_exception(args.browser, theurl, exc_value):
                    write_res(html_fp, csv_fp, urlnum-1, theurl, "expected exception: " + exc_str)
                else:
                    write_res(html_fp, csv_fp, urlnum-1, theurl, "unexpected exception: " + exc_str)
            result=driver.find_element(By.XPATH,"/*").text
            if args.superverbose:
                print(result)
            handler=get_handler(theurl)
            if args.verbose:
                print(handler)
            # record result if we didn't get an exception earlier
            if gotexception==False:
                if handler==None:
                    write_res(html_fp, csv_fp, urlnum-1, theurl, "no handler")
                else:
                    write_res(html_fp, csv_fp, urlnum-1, theurl, handler(result, expected))

            urlnum=urlnum+1

    driver.quit()
    # close off table
    print("</table>", file=html_fp)
