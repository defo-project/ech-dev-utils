#!/usr/bin/env python3

# Read the smokeping results from |start| to |end| and
# create a latex table presenting those

import os, sys, time, csv, re, json, traceback
from datetime import datetime, timezone, timedelta
from argparse import ArgumentParser
from collections import defaultdict

class myMeasure:
    def __init__(self, tuple=(0, 0)):
        self.exp, self.fail = tuple

def mult_dim_dict(dim, dict_type, params):
    if dim == 1:
        if params is not None:
            return defaultdict(lambda: dict_type(params))
        else:
            return defaultdict(dict_type)
    else:
        return defaultdict(lambda: mult_dim_dict(dim - 1, dict_type, params))

if __name__ == "__main__":
    parser = ArgumentParser(description="Summarise ECH smokeping data in table format")
    parser.add_argument('--urls_to_test', default='/var/extra/urls_to_test.csv',
                        help="CSV with URLs to test and expected outcomes")
    parser.add_argument('--top_dir', default='/var/extra/smokeping',
                        help='place to find time-based result files')
    parser.add_argument('--dest_dir', default='/var/extra/sp-tabs',
                        help='directory to put resulting summary file')
    parser.add_argument('-H','--html_out', default="sp-tab.html",
                        help='produce output as a HTML table')
    parser.add_argument('-L','--latex_out', default="sp-tab.tex",
                        help='produce output as a latex table')
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
    # for quicker elimination of old URLs

    # build up the data
    clients=[ 'chrome', 'chromium', 'curl', 'firefox', 'golang', 'rustls', 'python' ]
    # times, at 1 hour granularity
    times=[]
    # myMeasures array is url x client : { count(expected), count(unexpected) }
    # so we want to add a result to measures[u,c]
    measures = mult_dim_dict(2, myMeasure, None)
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
                    om=measures[u,c]
                    for foo in om:
                        if m=="expected":
                            foo.exp += 1
                            print(foo)
                        else:
                            foo.fail += 1
                            print(foo)
                    print(om)
                    measures[u,c]=om
                    #if {u,c} in measures:
                        #oval=measures[u,c]
                        #if m=="expected":
                            #oval[0]+=1
                        #else:
                            #oval[1]+=1
                        #measures[u,c]=oval
                    #else:
                        #if m=="expected":
                            #measures.append((u,c,1,0))
                        #else:
                            #measures.append((u,c,0,1))

    # sort measures by most recent-time first (i.e. reverse)
    # then by URL
    trevm=sorted(measures, key=lambda x: x[1], reverse=True)
    sortedmeasures=sorted(trevm, key=lambda x: x[0])
    #smout=open("sm.out","w")
    if args.verbose:
        for u in ue_list:
            for c in clients:
                sm = measures[u,c]
                print(u, c, sm)
                for foo in sm:
                    print(u, c, foo.exp, foo.fail)

    sys.exit(0)

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
