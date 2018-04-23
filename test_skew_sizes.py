import os
import struct

NUM_QUERIES = 113
NUM_COMBS = 150000
LONG_SIZE = 8

def abs(val):
    if val < 0:
        return -val
    else:
        return val

def main():
    with open("pg_job_sizes", "rb") as pg, open("skew_job_sizes", "rb") as skew, open('true_job_sizes', 'rb') as true:
        better = 0
        same = 0
        worse = 0
        for query_num in range(NUM_QUERIES):
            for comb in range(NUM_COMBS):
                pg_size = struct.unpack('q', pg.read(LONG_SIZE))[0]
                skew_size = struct.unpack('q', skew.read(LONG_SIZE))[0]
                true_size = struct.unpack('q', true.read(LONG_SIZE))[0]
                if bin(comb).count("1") != 2 or skew_size == -1:
                    continue
                '''
                print query_num, comb
                print abs(true_size-pg_size), abs(true_size-skew_size)
                print pg_size, skew_size, true_size, "\n"
                '''
                print query_num, comb
                print abs(true_size-pg_size),  abs(true_size-skew_size)
                print pg_size, skew_size, true_size, "\n"
                if pg_size*.9 <= skew_size and pg_size*1.1 >= skew_size: 
                    same+=1
                elif abs(true_size-pg_size) > abs(true_size-skew_size): 
                    better += 1
                else:

                    worse += 1
        print "Better:", better
        print "Same:", same
        print "Worse:", worse






main()
