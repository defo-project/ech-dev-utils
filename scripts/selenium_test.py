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

import os, sys, time, csv, re, json
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
def write_res(fp, num, url, res):
    print(str(num)+","+url+","+ res, file=fp)

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

if __name__ == "__main__":
    parser = ArgumentParser(description="test ECH for a set of URLs via headless browser")
    parser.add_argument('--browser', default='firefox',
                        help="one of chrome, firefox, or safari")
    parser.add_argument('--urls_to_test', default='/var/extra/urls_to_test.csv',
                        help="CSV with URLs to test and expected outcomes")
    parser.add_argument('--results_dir', default='/var/extra/selenium/runs',
                        help='place to put time-based result fils')
    args = parser.parse_args()

    runtime=datetime.now(timezone.utc)
    runstr=runtime.strftime('%Y%m%d-%H%M%S')

    print("URLs:", args.urls_to_test)
    print("Browser:", args.browser)
    myresults=args.results_dir+"/"+runstr
    print("Run dir:",myresults)

    if not os.path.isdir(args.results_dir):
        print("Results dir doesn't exist - exiting")
        sys.exit(1)
    os.makedirs(myresults)
    if not os.path.isdir(myresults):
        print("Can't make results dir - exiting")
        sys.exit(1)
    fp=open(myresults+"/"+runstr+".html",'w')

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
        case 'chrome':
            from webdriver_manager.chrome import ChromeDriverManager
            options = chrome_Options()
            options.add_argument('--headless=new')
            driver = webdriver.Chrome(service=chrome_Service(ChromeDriverManager().install()), options=options)
        case 'chromium':
            from selenium.webdriver.chrome.service import Service as ChromeService
            options = chrome_Options()
            options.add_argument('--headless=new')
            service = ChromeService(executable_path="/usr/bin/chromedriver")
            driver = webdriver.Chrome(options = options, service = service)
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
            # skip heading row
            if urlnum==0:
                urlnum=1
                continue
            theurl=row[0]
            print("***********")
            print(str(urlnum), theurl)
            # FF default
            expected=int(row[1])
            if args.browser=='chrome' or args.browser=='chromium':
                expected=int(row[2])
            try:
                driver.get(theurl)
            except:
                # TODO: probably want to check HTTP response codes here
                write_res(fp, urlnum-1, theurl, "exception thrown")
                print("Oops - crash")
            result=driver.find_element(By.XPATH,"/*").text
            #print(result)
            handler=get_handler(theurl)
            #print(handler)
            if handler==None:
                write_res(fp, urlnum-1, theurl, "no handler")
            else:
                write_res(fp, urlnum-1, theurl, handler(result, expected))

            # check results
            #recognized = list(filter(lambda x: x['url'] == theurl
                         #or not x['url'], visit))
            #for handler in recognized:
                #interest = driver.find_elements(handler['filter']['by'], handler['filter']['match'])
                #renderer = handler['render']
                #if interest:
                    #break
                #print("Handler found nothing of interest.",
                    #"No further fallback handler available."
                    #if handler == recognized[-1]
                    #else "Trying (next) fallback handler.")
            #print("Count:", len(interest))
            #print("Found:", list(map(renderer, interest)))

            urlnum=urlnum+1

    driver.quit()
