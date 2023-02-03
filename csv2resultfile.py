#!/usr/bin/env python3
#@ converts a CSV file to the RESULT log file required as input for 

import sys

import argparse

import codecs

def unescaped_str(arg_str):
    return codecs.decode(str(arg_str), 'unicode_escape')

parser = argparse.ArgumentParser(description='converts a CSV file into a RESULT file')
parser.add_argument('-i', "--input", type=str, help="input CSV file", required=True)
parser.add_argument('-o', "--output", type=str, help="output stats file", default='')
parser.add_argument('-d', '--delimiter', type=unescaped_str, default=',')
args = parser.parse_args()

outfile = sys.stdout
if args.output:
    outfile = open(args.output)

with open(args.input) as csvfile:
    header = [x.strip() for x in csvfile.readline().split(args.delimiter)]
    for line in csvfile.readlines():
        csvlist = line.split(args.delimiter)
        print("RESULT " + "\t".join(list(map(lambda x,y: (x + "=" + y.strip()), header, csvlist))), file=outfile)

outfile.close()

