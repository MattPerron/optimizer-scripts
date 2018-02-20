import os
import pyodbc
import struct

def main():
    conn = pyodbc.connect("DSN=mssql;UID=matt;PWD=******")
    cur = conn.cursor();
    cur.execute("set showplan_all on;")
    job_directory = '/home/matt/join-order-benchmark'
    file_letters = ['a', 'b', 'c', 'd', 'e', 'f', 'g']
    file_id = 0;
    file_contents = {}
    file_ids = {}
    for file_num in range(1, 34):
        for letter in file_letters:
            file_name = "{}{}.sql".format(file_num, letter)
            file_path = os.path.join(job_directory, file_name)
            if os.path.isfile(file_path):
                with open(file_path, 'r') as fin:
                    file_contents[file_id] = fin.read()
                    print file_name
                file_id += 1
            else:
                break
    NUM_QUERIES = 113
    NUM_COMBS = 150000
    LONG_SIZE = 8
    count = 0
    with open('mssql_job_sizes', 'wb') as fout:
        for query_num in range(NUM_QUERIES):
            for comb in range(NUM_COMBS):
                curr_bytes = struct.pack('q', -1)
                fout.write(curr_bytes)
        print "done creating file"
        with open('job_sizes', 'rb') as fin:
            for query_num in range(NUM_QUERIES):
                print query_num
                for comb in range(NUM_COMBS):
                    fin.seek((query_num*NUM_COMBS+comb)*8, 0)
                    fout.seek((query_num*NUM_COMBS+comb)*8, 0)
                    num = struct.unpack('q', fin.read(8))[0]
                    if num >= 0:
                        count += 1
                        currquery = get_query(file_contents[query_num], comb)
                        cur.execute(currquery)
                        num = int(round(cur.fetchone()[8]))
                    fout.write(struct.pack('q', num))

    print "Total Count: ", count

def get_query(query, comb_number):
    count_tables = bin(comb_number).count("1")
    fromfound = False
    wherefound = False
    includeline = True
    included_tables = 0
    total_tables = 0
    aliases = []
    outquery = "SELECT * FROM\n"
    for line in query.split("\n"):
        if line.find("FROM") >= 0:
            fromfound = True
        if line.find("WHERE") >= 0:
            outquery += "WHERE 1 = 1 \n"
            wherefound = True
        if wherefound:
            add_and = False
            if line.find("WHERE") >= 0:
                line = line[5:]
                add_and = True
                include_line = True
            if line.find("AND") >= 0:
                include_line = True
            idx = line.find(";")
            if idx >= 0:
                line = line[:idx]
            for curr_alias in range(total_tables):
                if (not((1 << curr_alias) & comb_number)):
                    space_alias_with_dot = " {}.".format(aliases[curr_alias])
                    paren_alias_with_dot = "({}.".format(aliases[curr_alias])
                    if line.find(space_alias_with_dot) >= 0 or line.find(paren_alias_with_dot) >= 0:
                        include_line = False
                        break
            if add_and and include_line:
                outquery += "AND "
            if include_line:
                outquery += line
                outquery += "\n"
        elif fromfound:
            idx = line.find(",")
            if idx >= 0:
                line = line[:idx]
            if line.find("FROM") >= 0:
                line = line[5:]
            if (comb_number & (1 << total_tables)):
                outquery += line
                included_tables+= 1
                if included_tables < count_tables:
                    outquery += ","
                outquery += "\n"
            idx = line.find("\n")
            if idx >= 0:
                line = line[:idx]
            idx = line.find("AS ")
            aliases.append(line[idx+3:])
            total_tables+=1
    outquery += ";"
    return outquery
            





main()
