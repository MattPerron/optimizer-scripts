import os
import sys
import re
import struct
from sets import Set
import psycopg2 as pg


NUM_QUERIES = 113
NUM_COMBS = 150000
LONG_SIZE = 8

def main():
    conn = pg.connect("host=localhost user=mperron dbname=imdb")
    conn.autocommit = True
    cur = conn.cursor()
    #get most frequent values, and frequencies
    frequencies = {}
    table_counts = {}
    cur.execute("select tablename from pg_tables where schemaname = 'public'");
    '''
    for record in cur.fetchall():
        table_name = record[0]
        cur.execute("select count(*) from {};".format(table_name))
        table_counts[table_name] = cur.fetchone()[0]
    print table_counts
    cur.execute("select tablename, attname from pg_stats where schemaname = 'public' and attname like '%_id' and attname <> 'imdb_id'")
    for record in cur.fetchall():
        table_name = record[0]
        att_name = record[1]
        if table_name not in frequencies:
            frequencies[table_name] = {}

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
            '''
    job_directory = '/data/mperron/join-order-benchmark'
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
                    if bin(comb).count("1") < 2 or bin(comb).count("1") > 4:
                        continue
                    fin.seek((query_num*NUM_COMBS+comb)*8, 0)
                    fout.seek((query_num*NUM_COMBS+comb)*8, 0)
                    num = struct.unpack('q', fin.read(8))[0]
                    if num >= 0:
                        count += 1
                        num = get_estimate(file_contents[query_num], comb, cur, frequencies, table_counts, query_num)

    print "Total Count: ", count

def get_estimate(query, comb_number, cur, frequencies, table_counts, query_num):
    count_tables = bin(comb_number).count("1")
    fromfound = False
    wherefound = False
    includeline = True
    included_tables = 0
    total_tables = 0
    small = None
    small_att = None
    large = None
    large_att = None
    aliases = []
    alias_mapping = {}
    join_conditions = []
    tables = Set()
    pattern = re.compile("(.*\..*_id \= .*\.id)|(.*\.id \= .*\..*_id)|(.*\..*_id \= .*\..*_id)")

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
                if counts > 1 and pattern.match(line):
                    splitline = re.split("[ |\.]", line.strip())
                    join_conditions.append(line[6:])
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
                    tables.add(small)
                    tables.add(large)
                    continue
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
            alias_mapping[line[idx+3:]]= line.strip().split(" ")[0] 
            total_tables+=1
    outquery += ";"
    if small == None or large == None:
        return -1
    join_tables = []
    for table in tables:
        join_tables.append((alias_mapping[table], table))
    join_tables.sort(key=lambda x: x[0])
    normalized_table_name = "_j_".join([x[0] for x in join_tables])
    cur.execute("select exists (select 1 from information_schema.tables where table_catalog='imdb' and table_schema='public' and table_name = '{}');".format(normalized_table_name))
    join_table_exists = cur.fetchone()[0]
    if not join_table_exists:
        column_names = []
        for table in join_tables:
            cur.execute("select column_name from information_schema.columns where table_name='{}'".format(table[0]));
            res = cur.fetchall()
            for column in res:
                column_names.append(table[1]+"."+column[0]+" AS "+table[0]+"_t_"+column[0])
        print "creating table ", normalized_table_name
        creation_string = "SELECT {} \n INTO {} \n FROM {} \n WHERE {};".format(",\n  ".join(column_names), normalized_table_name, ",\n  ".join(["{} AS {}".format(x[0], x[1]) for x in join_tables]), "\n  AND ".join(join_conditions))
        print creation_string

        cur.execute(creation_string);
        print "created table ", normalized_table_name
        cur.execute("begin; analyze {}; commit;".format(normalized_table_name));
        print "analayzed table ", normalized_table_name

    print "\nQuery: ", query_num 
    print "FULL: "
    print query
    print "BEFORE:"
    print outquery
    for table in join_tables:
        outquery = outquery.replace(" "+table[1]+".", " "+table[0]+"_t_")
        outquery = outquery.replace("("+table[1]+".", "("+table[0]+"_t_")
    outquery_lines = outquery.split("\n")
    outquery_lines = ["EXPLAIN"]+outquery_lines[:1]+[normalized_table_name]+outquery_lines[len(join_tables)+1:]
    outquery = "\n".join(outquery_lines)
    print "AFTER:"
    print outquery
    cur.execute(outquery)
    firstline = cur.fetchone()[0].split(" ")
    est = -1 
    for blah in firstline:
        if blah.find("rows")>=0:
            est = long(blah.split("=")[1])
    return est

    '''
    small_comb = 1 << aliases.index(small)
    large_comb = 1 << aliases.index(large)
    sample = get_sample(query, small_comb, cur, [k for k in frequencies[alias_mapping[large]][large_att]['mcv']])
    join_count = 0
    for num in sample:
        print num
        join_count += frequencies[alias_mapping[large]][large_att]['mcv'][num]
    count_without_most_frequent = table_counts[alias_mapping[large]]-frequencies[alias_mapping[large]][large_att]['freq_total']
    print join_count
    orig = get_original_estimates(query_num, comb_number)
    print orig
    total_large_table_size = table_counts[alias_mapping[large]]
    large_table_proportion = float(get_original_estimates(query_num, large_comb))/total_large_table_size
    print get_original_estimates(query_num, large_comb)
    print large_table_proportion
    join_count = long(large_table_proportion*join_count )
    print join_count
    print total_large_table_size
    proportion = float(orig)/total_large_table_size
    print proportion, count_without_most_frequent
    join_count += long(count_without_most_frequent*proportion)
    '''

def get_original_estimates(query_num, comb_number):
    with open('pg_job_sizes', 'rb') as pg_sizes:
        pg_sizes.seek((query_num*NUM_COMBS+comb_number)*8, 0)
        return struct.unpack('q', pg_sizes.read(8))[0]


def get_sample(query, comb_number, cur, frequentvalues):
    count_tables = bin(comb_number).count("1")
    fromfound = False
    wherefound = False
    includeline = True
    included_tables = 0
    total_tables = 0
    aliases = []
    alias_mapping = {}
    outquery = "SELECT id FROM\n"
    for line in query.split("\n"):
        if line.find("FROM") >= 0:
            fromfound = True
        if line.find("WHERE") >= 0:
            outquery += "WHERE id in ({}) \n".format(", ".join([str(x) for x in frequentvalues]))
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
            alias_mapping[line[idx+3:]]= line.strip().split(" ")[0] 
            total_tables+=1
    outquery += ";"
    cur.execute(outquery)
    return [x[0] for x in cur.fetchall()]
            
main()
