import os
import re
import struct
import psycopg2 as pg


NUM_QUERIES = 113
NUM_COMBS = 150000
LONG_SIZE = 8

def main():
    conn = pg.connect("host=localhost user=matt dbname=matt")
    cur = conn.cursor()
    #get most frequent values, and frequencies
    frequencies = {}
    table_counts = {}
    cur.execute("select tablename, attname from pg_stats where schemaname = 'public' and attname like '%_id' and attname <> 'imdb_id'")
    for record in cur.fetchall():
        table_name = record[0]
        att_name = record[1]
        if table_name not in frequencies:
            frequencies[table_name] = {}
        if table_name not in table_counts:
            cur.execute("select count(*) from {};".format(table_name))
            table_counts[table_name] = cur.fetchone()[0] 

        info = {}
        cur.execute("select {}, count(*) from {} group by {} order by {} limit 100;".format(att_name, table_name, att_name, att_name));
        total = 0
        freq_vals = {}
        for freq_val_tuple in cur.fetchall():
            total+= freq_val_tuple[1]
            freq_vals[freq_val_tuple[0]] = freq_val_tuple[1]
        info['mcv'] = freq_vals
        info['freq_total'] = total
        info['total'] = table_counts[table_name]
        frequencies[table_name][att_name] = info
    for table_name in frequencies:
        for att_name in frequencies[table_name]:
            print table_name, att_name, frequencies[table_name][att_name]['freq_total'], frequencies[table_name][att_name]['total']
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
                file_id += 1
            else:
                break
    # TODO: get the total of the larger table, total of the smaller table, and proportions of each
    count = 0
    with open('skew_job_sizes', 'wb') as fout:
        for query_num in range(NUM_QUERIES):
            for comb in range(NUM_COMBS):
                curr_bytes = struct.pack('q', -1)
                fout.write(curr_bytes)
        print "done creating file"
        with open('job_sizes', 'rb') as fin:
            for query_num in range(NUM_QUERIES):
                for comb in range(NUM_COMBS):
                    if bin(comb).count("1") != 2:
                        continue
                    fin.seek((query_num*NUM_COMBS+comb)*8, 0)
                    fout.seek((query_num*NUM_COMBS+comb)*8, 0)
                    num = struct.unpack('q', fin.read(8))[0]
                    if num >= 0:
                        count += 1
                        currquery= get_estimate(file_contents[query_num], comb)
                        #print currquery
                        #num = int(round(cur.fetchone()[8]))
                    fout.write(struct.pack('q', num))

    print "Total Count: ", count

def get_estimate(query, comb_number):
    count_tables = bin(comb_number).count("1")
    fromfound = False
    wherefound = False
    includeline = True
    included_tables = 0
    total_tables = 0
    aliases = []
    alias_mapping = {}
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
            dot_aliases = [" {}.".format(x) for x in aliases]
            counts = 0
            if include_line:
                for alias in dot_aliases:
                    if line.count(alias) == 1:  
                        counts += 1
                if counts > 1 and line.count("_id") == 1:
                    splitline = re.split("[ |\.]", line.strip())
                    small = None
                    small_att = None
                    large = None
                    large_att = None
                    if splitline[2].count("_id") == 0:
                        small = splitline[1]
                        small_att = splitline[2]
                        large = splitline[4]
                        large_att = splitline[5]
                    else:
                        small = splitline[4]
                        small_att = splitline[5]
                        large = splitline[1]
                        large_att = splitline[2]

                    print small, large
                    print small_att, large_att
                    if small_att != 'id':
                        print line
                        exit(1)
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
            alias_mapping[line[idx+3]]= line.split(" ")[0] 
            total_tables+=1
    outquery += ";"
    return outquery
            





main()
