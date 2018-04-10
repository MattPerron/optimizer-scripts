import os
import pyodbc
import struct

def main():
    with open("job_sizes", "rb") as fin, open("mssql_job_sizes", "wb") as fout:
        for i in range(100):
            curr_num = struct.unpack('l', fin.read(8))[0]
            fout.write(struct.pack('l', curr_num))
            print curr_num



main()
