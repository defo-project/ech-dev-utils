#!/usr/bin/env python3

# Read from all the current CSV files with ECH smokeping data and make
# a single web page to present current results. ECH smokeping data for
# curl, ff, chrome, golang and rust is generated hourly, but not
# at same same instant.
# This is intended to be run from an hourly cron job. We don't need to
# care about times within a single hour. (If we have >1 data point in 
# the same hour, we'll take the last.)
# Clients, URLs to test, and which got tested can change over time,
# we'll just add 'em in as we see 'em.
# Ultimately we'll want to order the results, but not sure yet how we
# might prefer that, e.g. best results first, or worst first etc.

import os, sys, time, csv, re, json, traceback
import collections
from datetime import datetime, timezone, timedelta
from argparse import ArgumentParser

def image_stanza(image, tiptext, alttext):
    rstr='<img width="20" height="20" src="' + image + '" ' + \
         'title="' + tiptext + '" '+ \
         '" alt="' + alttext + '"/>'
    return rstr

# format the content of a cell with expected results
def cell_with_expected(exp):
    fstr=""
    # recall zero is a success test outcome
    if exp[2]==0 or exp[2]=="0":
        fstr=fstr+image_stanza("./chrome-logo.png","chrome expected good","chrome good")
    else:
        fstr=fstr+image_stanza("./chrome-logo-x.png","chrome expected fail","chrome fail")
    if exp[0]==0 or exp[0] == "0":
        fstr=fstr+image_stanza("./curl-logo.png","curl expected good","curl good")
    else:
        fstr=fstr+image_stanza("./curl-logo-x.png","curl expected fail ("+exp[1]+")","curl fail")
    if exp[1]==0 or exp[1]=="0":
        fstr=fstr+image_stanza("./ff-logo.png","firefox expected good","ff good")
    else:
        fstr=fstr+image_stanza("./ff-logo-x.png","firefox expected fail","ff fail")
    if exp[3]==0 or exp[3]=="0":
        fstr=fstr+image_stanza("./golang-logo.png","golang expected good","golang good")
    else:
        fstr=fstr+image_stanza("./golang-logo-x.png","golang expected fail","golang fail")
    if exp[4]==0 or exp[4]=="0":
        fstr=fstr+image_stanza("./rustls-logo.png","rustls expected good","rustls good")
    else:
        fstr=fstr+image_stanza("./rustls-logo-x.png","rustls expected fail","rustls fail")
    if exp[5]==0 or exp[5]=="0":
        fstr=fstr+image_stanza("./python-logo.png","python expected good","python good")
    else:
        fstr=fstr+image_stanza("./python-logo-x.png","python expected fail","python fail")
    return fstr

# display time more nicely
def cell_with_time(t):
    # hourly time stamp input is YYYYMMDD-HH0000
    # output is YY-MM-DD HH:00:00
    dt=datetime.strptime(t, '%Y%m%d-%H%M%S')
    return str(dt)


# format the content of a cell of our table, according to what
# was expected
def cell_with_measure(u,t,c,m,exp):
    if m=="expected":
        if c=="firefox":
            # zero is success
            if exp[1]==0 or exp[1]=='0':
                return(image_stanza("./ff-logo.png","firefox as expected","ff as expected"))
            else:
                return(image_stanza("./ff-logo-x.png","ff fail as expected","ff fail"))
        if c=="chrome":
            if exp[2]==0 or exp[2]=='0':
                return(image_stanza("./chrome-logo.png","chrome as expected","chrome as expected"))
            else:
                return(image_stanza("./chrome-logo-x.png","chrome fail as expected","chrome fail"))
        if c=="chromium":
            if exp[2]==0 or exp[2]=='0':
                return(image_stanza("./chrome-logo.png","chromium as expected","chromium as expected"))
            else:
                return(image_stanza("./chrome-logo-x.png","chromium fail as expected","chromium fail"))
        if c=="curl":
            if exp[0]==0 or exp[0]=='0':
                return(image_stanza("./curl-logo.png","curl as expected","curl as expected"))
            else:
                return(image_stanza("./curl-logo-x.png","curl fail as expected","curl as expected"))
        if c=="golang":
            if exp[3]==0 or exp[3]=='0':
                return(image_stanza("./golang-logo.png","golang as expected","golang as expected"))
            else:
                return(image_stanza("./golang-logo-x.png","golang fail as expected","golang as expected"))
        if c=="rustls":
            if exp[4]==0 or exp[4]=='0':
                return(image_stanza("./rustls-logo.png","rustls as expected","rustls as expected"))
            else:
                return(image_stanza("./rustls-logo-x.png","rustls fail as expected","rustls as expected"))
        if c=="python":
            if exp[5]==0 or exp[5]=='0':
                return(image_stanza("./python-logo.png","python as expected","python as expected"))
            else:
                return(image_stanza("./python-logo-x.png","python fail as expected","python as expected"))
    else:
        if c=="firefox":
            return(image_stanza("./ff-logo-x.png",m,"ff fail"))
        if c=="chrome":
            return(image_stanza("./chrome-logo-x.png",m,"chrome fail"))
        if c=="chromium":
            return(image_stanza("./chrome-logo-x.png",m,"chromium fail"))
        if c=="curl":
            return(image_stanza("./curl-logo-x.png",m,"curl as expected"))
        if c=="golang":
            return(image_stanza("./golang-logo-x.png",m,"golang as expected"))
        if c=="rustls":
            return(image_stanza("./rustls-logo-x.png",m,"rustls as expected"))
        if c=="python":
            return(image_stanza("./python-logo-x.png",m,"python as expected"))
    return "unknown client: " + c

# format a URL for a column in our table
# you need to know something about our test URLs to get this
# right
def cell_with_url(u):
    ustr='<a href="'+u+'">'+u+'</a>'
    return ustr;

def time_too_old(tstr, hours):
    earliest=datetime.now(timezone.utc)-timedelta(hours=hours)
    #print("Earliest:", earliest, file=sys.stderr)
    estr=earliest.strftime('%Y%m%d-%H%M%S')
    if tstr > estr:
        return False
    return True


if __name__ == "__main__":
    parser = ArgumentParser(description="Merge ECH smokeping data")
    parser.add_argument('--urls_to_test', default='/var/extra/urls_to_test.csv',
                        help="CSV with URLs to test and expected outcomes")
    parser.add_argument('--top_dir', default='/var/extra/smokeping',
                        help='place to find time-based result files')
    parser.add_argument('--dest_dir', default='/var/extra/sp-tabs',
                        help='directory to put resulting summary file')
    parser.add_argument('-H','--html_out', default="tab.html",
                        help='produce output as a HTML table')
    parser.add_argument("--hours", type=int, help="only show last N hours")
    args = parser.parse_args()

    # my run time
    runtime=datetime.now(timezone.utc)
    runstr=runtime.strftime('%Y%m%d-%H%M%S')

    if args.hours is not None:
        print("Only displaying last", args.hours, "hours", file=sys.stderr)

    # read URL info
    ue_list={}
    with open(args.urls_to_test) as csvfile:
        readCSV = csv.reader(csvfile, delimiter=',')
        urlnum=0
        for row in readCSV:
            # skip heading row
            if urlnum==0:
                urlnum=1
                continue
            ue_list[row[0]]=(row[1],row[2],row[3],row[4],row[5],row[6]);
            urlnum=urlnum+1
    toturls=urlnum-1
    # for quicker elimination of old URLs

    # build up the data
    clients=[ 'chrome', 'chromium', 'curl', 'firefox', 'golang', 'rustls', 'python' ]
    # times, at 1 hour granularity
    times=[]
    # measures array is url x time x client : measure
    # so we want to add a result to measures[u,t,c]
    measures=[]
    for c in clients:
        rdname=args.top_dir+"/"+c+"-runs"
        if not os.path.isdir(rdname):
            continue
        subfolders = [ f.path for f in os.scandir(rdname) if f.is_dir() ]
        #print(subfolders)
        for s in subfolders:
            csvf=s+"/"+os.path.basename(s)+".csv"
            if not os.path.isfile(csvf):
                continue
            # print("Will read " + csvf)
            # hour granularity time
            t=os.path.basename(s)[:-4]+'0000'
            if args.hours is not None and time_too_old(t, args.hours):
                continue
            if not t in times:
                times.append(t)
            urlnum=0
            with open(csvf) as csvfile:
                readCSV = csv.reader(csvfile, delimiter=',')
                urlnum=0
                for row in readCSV:
                    if urlnum==0:
                        urlnum=1
                        continue
                    # discard no-longer needed URLs
                    if row[1] not in ue_list:
                        print ("Discarding measure for", row[1], row[2], "from", os.path.basename(csvf), file=sys.stderr)
                        continue
                    urlnum=urlnum+1
                    u=row[1]
                    m=row[2]
                    # tidy up for curl script error in early files
                    if m=="expected>":
                        m="expected"
                    cellstr=cell_with_measure(u,t,c,m,ue_list[u])
                    measures.append((u,t,cellstr))

    # sort measures by most recent-time first (i.e. reverse)
    # then by URL
    trevm=sorted(measures, key=lambda x: x[1], reverse=True)
    sortedmeasures=sorted(trevm, key=lambda x: x[0])
    sortedtimes=sorted(times, reverse=True)
    #smout=open("sm.out","w")
    #for sm in sortedmeasures:
        #print(sm, file=smout)

    mergedmeasures=[]
    curr_u=sortedmeasures[0][0]
    curr_t=sortedmeasures[0][1]
    all_r=""
    line=0
    for sm in sortedmeasures:
        u=sm[0]
        t=sm[1]
        r=sm[2]
        if curr_u != u or curr_t != t:
            if curr_u not in ue_list:
                print("Warning URL missing", curr_u, file=sys.stderr)
            # record merged details
            expstr=cell_with_expected(ue_list[curr_u])
            mergedmeasures.append((line,curr_u,expstr,curr_t,all_r))
            curr_u = u
            curr_t = t
            line=line+1
            all_r=""
        all_r=all_r+" "+r
    expstr=cell_with_expected(ue_list[curr_u])
    mergedmeasures.append((line,curr_u,expstr,curr_t,all_r))

    #mmout=open("mm.out","w")
    #for mm in mergedmeasures:
        #print(mm, file=mmout)

    # table header
    outf=open(args.html_out,"w")
    print("<html>", file=outf)
    print("<head>", file=outf)
    print("</head>", file=outf)
    print("<body>", file=outf)
    print("<table border=\"1\" width=\"80%\">", file=outf)
    print("<th align=\"left\">Num</th>", file=outf)
    print("<th align=\"left\">URL</th>", file=outf)
    print("<th align=\"left\">Expected</th>", file=outf)
    for st in sortedtimes:
        print("<th align=\"center\">"+cell_with_time(st)+"</th>", file=outf)
    print("</th>", file=outf)
    print("</tr>", file=outf)
    tline=1
    curr_u=mergedmeasures[0][1]
    print("<td>"+str(tline)+"</td>", file=outf)
    print("<td>"+cell_with_url(curr_u)+"</td>", file=outf)
    print("<td align=\"center\">"+mergedmeasures[0][2]+"</td>", file=outf)
    for mm in mergedmeasures:
        if curr_u != mm[1]:
            curr_u=mm[1]
            tline=tline+1
            print("</tr>", file=outf)
            print("<tr>", file=outf)
            print("<td>"+str(tline)+"</td>", file=outf)
            print("<td>"+cell_with_url(mm[1])+"</td>", file=outf)
            print("<td align=\"center\">"+mm[2]+"</td>", file=outf)
        print("<td align=\"center\">"+mm[4]+"</td>", file=outf)
    print("</tr>", file=outf)
    print("</table>", file=outf)
    print("</body>", file=outf)
    print("</html>", file=outf)
