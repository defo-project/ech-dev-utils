#!/usr/bin/env python3

# Read the smokeping results from |start| to |end| and
# create a latex table presenting those

import os, sys, time, csv, re, json, traceback
from datetime import datetime, timezone, timedelta
from argparse import ArgumentParser
from pprint import pprint

def latex_out(measures):
    # make latex output
    urlind = 0
    # header
    tabhead="""\\tiny
\\begin{longtblr} [
        caption = {Interop tests from %s to %s},
        label = {tab:itests}
    ] {
        colspec = {| c | l | c | c | c | c | c | c |},
        rowhead = 1
    }
    \\hline"""
    tabtail="""\\hline
\\end{longtblr}
\\normalsize"""
    print(tabhead % (start_date, end_date))
    cols = ""
    for c in clients:
        cols += f' & {c} '
    print(f'num & url {cols}\\\\ \\hline')
    # one line per URL, columns are url-number, url, per-client: %expected/total
    for u in ue_list:
        urlind += 1
        cols = ""
        for c in clients:
            if (u,c) in measures:
                exps = measures[(u,c)][0]
                fails = measures[(u,c)][1]
                tot = exps + fails
                percent = "{:.2f}".format(exps/tot)
                cols += f' & {percent}/{tot} '
            else:
                cols += ' & n/a '
        print("%d & \\url{%s} %s\\\\ \\hline" % (urlind, u, cols))
    print(tabtail)

if __name__ == "__main__":
    parser = ArgumentParser(description="Summarise ECH smokeping data in table format")
    parser.add_argument('--urls_to_test', default='/var/extra/urls_to_test.csv',
                        help="CSV with URLs to test and expected outcomes")
    parser.add_argument('--top_dir', default='/var/extra/smokeping',
                        help='place to find time-based result files')
    parser.add_argument('--dest_dir', default='/var/extra/sp-tabs',
                        help='directory to put resulting summary file')
    parser.add_argument("-v", "--verbose", action="store_true",  help="additional output")
    parser.add_argument("--hours", type=int, help="only show last N hours")
    parser.add_argument('-s','--start', dest='start', help='start-date')
    parser.add_argument('-e','--end', dest='end', help='end-date')
    args = parser.parse_args()

    now = datetime.now()
    oneday = timedelta(1)
    
    if args.start is not None:
        start_date = datetime.strptime(args.start, '%Y-%m-%d')
    else:
        start_date = now - oneday
    if args.end is not None:
        end_date = datetime.strptime(args.end, '%Y-%m-%d')
    else:
        end_date = now

    if args.verbose:
        print(f'Reporting on {args.top_dir} from {start_date} to {end_date}')

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
    ue_list=sorted(ue_list)

    # build up the data
    clients=[ 'chromium', 'curl', 'firefox', 'golang', 'rustls', 'python' ]
    # times, at 1 hour granularity
    times=[]
    # myMeasures array is url x client : { count(expected), count(unexpected) }
    # so we want to add a result to measures[u,c]
    measures = {}
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
            # hour granularity time
            # tstr=os.path.basename(s)[:-4]+'0000'
            tstr=os.path.basename(s)
            mtime = datetime.strptime(tstr, '%Y%m%d-%H%M%S')
            if mtime >= end_date or mtime < start_date:
                if args.verbose:
                    print("Discarding " + csvf)
                continue
            if args.verbose:
                print("Will read " + csvf)
            urlnum=0
            with open(csvf) as csvfile:
                readCSV = csv.reader(csvfile, delimiter=',')
                urlnum=0
                for row in readCSV:
                    # drop 1st row (header)
                    if urlnum==0:
                        urlnum=1
                        continue
                    # discard no-longer needed URLs
                    if row[1] not in ue_list:
                        if args.verbose:
                            print ("Discarding measure for", row[1], row[2], "from", os.path.basename(csvf))
                        continue
                    urlnum=urlnum+1
                    u=row[1]
                    m=row[2]
                    # tidy up for curl script error in early files
                    if m=="expected>":
                        m="expected"
                    exps=0
                    fails=0
                    if (u,c) in measures:
                        om=measures[(u,c)]
                        exps=om[0]
                        fails=om[1]
                    if m=="expected":
                        exps += 1
                    else:
                        fails += 1
                    measures[(u,c)]=[exps, fails]
    latex_out(measures)
