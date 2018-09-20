from __future__ import print_function
import os
import psycopg2 as pg
import struct
import argparse

parser = argparse.ArgumentParser()

parser.add_argument("--query", "-q", type=int, required=True)
parser.add_argument("--perfect", "-p", type=int, required=True)
parser.add_argument("--num_joins", "-n", type=int, required=True)
parser.add_argument("--true_cost", "-t", action="store_true")

args = parser.parse_args()

NUM_COMBS = 150000
NUM_TABLES = 17

def main():
    conn = pg.connect("host=localhost user=matt dbname=matt")
    cur = conn.cursor();
    job_directory =os.path.join(os.getenv("HOME"), 'join-order-benchmark')
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
    with open('job_sizes', 'rb') as fin:
        for comb in range(NUM_COMBS):
            fin.seek((args.query*NUM_COMBS+comb)*8, 0)
            num = struct.unpack('q', fin.read(8))[0]
            if num < 0 or bin(comb).count("1") != args.num_joins:
                continue

            query_str, aliases = get_query(file_contents[args.query], comb)
            tables = []
            table_aliases = []
            for table in range(17):
                if ((1 << table) & comb):
                    tables.append(hex(1<< table)[2:])
                    table_aliases.append(aliases[table])
            tables = "\""+",".join(tables)+"\""
            test_query = "set new_table_mapping_str to True;\n"
            test_query += "set perfect_estimates to {};\n".format(args.perfect)
            test_query += "set table_mapping to {};\n".format(tables)
            test_query += "set current_test_query to {};\n".format(args.query)
            result_line = ""
            result = ""
            if args.true_cost:
                test_query += "EXPLAIN ANALYZE "+query_str
                cur.execute(test_query)
                result_line = cur.fetchone()[0]
                result = float(result_line.split(" ")[3].split("..")[1])
                true_result = float(result_line.split(" ")[7].split("..")[1])
                print("-".join(table_aliases)+":", result/100, true_result, result_line)
            else:
                test_query += "EXPLAIN "+query_str
                cur.execute(test_query)
                result_line = cur.fetchone()[0]
                result = float(result_line.split(" ")[3].split("..")[1])
                print("-".join(table_aliases)+":", result/100, result_line)
            #print(query_str)


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
    return outquery, aliases
            





main()
