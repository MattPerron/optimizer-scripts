#!/usr/bin/python
from __future__ import print_function
import os
import sys
import psycopg2 as pg

def main():
    letters = ['a', 'b', 'c', 'd', 'e', 'f']
    simple_costs = False 
    use_nestloop = True
    use_seqscan = True
    index = 0
    directory = "/data/mperron/join-order-benchmark"
    output_dir = "denorm_estimates_brown"
    with pg.connect('host=localhost user=mperron dbname=imdb') as conn, conn.cursor() as cur, open(os.path.join(output_dir, "aggregate_data.csv"), 'w', 1) as agg_data:
        cur.execute('select 1;')
        agg_data.write("query_index, query_name, num_tables, perfect_estimates, new_plan, execution_time1, execution_time2\n")
        for fname_num in range(1, 34):
            for fname_letter in letters:
                filename = "{}{}.sql".format(fname_num, fname_letter)
                filename = os.path.join(directory, filename)
                if not os.path.exists(filename):
                    continue
                with open(filename, 'r') as f:
                    contents = f.read()
                counting = False
                max_table_count = 0
                for line in contents.split('\n'):
                    if 'FROM' in line:
                        counting = True
                    if 'WHERE' in line:
                        break
                    if counting:
                        max_table_count+=1
                plans = [None for i in range(max_table_count+1)]
                #for estimate in range(max_table_count, max_table_count+1):
                for estimate in range(0, max_table_count+1):
                #for estimate in range(4, 5):
                    print(filename, estimate) 
                    #explain once to get the plan
                    cur.execute("set current_test_query={};".format(index))
                    cur.execute("set perfect_estimates={};".format(estimate))
                    cur.execute("set new_table_mapping_str to True")
                    table_mapping = [hex(1<<x)[2:] for x in range(max_table_count)]
                    #print(type(table_mapping), table_mapping)
                    cur.execute("set table_mapping to '{}'".format(",".join(table_mapping)))
                    if simple_costs:
                        cur.execute("set seq_page_cost=0;")
                        cur.execute("set random_page_cost=0;")
                        cur.execute("set cpu_operator_cost=0;")
                        cur.execute("set cpu_tuple_cost=1;")
                        cur.execute("set cpu_index_tuple_cost=1;")
                    if use_seqscan:
                        cur.execute("set enable_seqscan=true;")
                    else:
                        cur.execute("set enable_seqscan=false;")
                    if use_nestloop:
                        cur.execute("set enable_nestloop=true;")
                    else:
                        cur.execute("set enable_nestloop=false;")
                    cur.execute("explain (costs false) " + contents);
                    plan = ''
                    with open(os.path.join(output_dir, "{}{}.{}.plan".format(fname_num, fname_letter, estimate)), 'w') as plan_file:
                        for line in cur.fetchall():
                            plan = plan+line[0]+"\n"
                            plan_file.write(line[0]+"\n")
                    new_plan = plan not in plans
                    plans[estimate] = plan

                    #execute it again to get the execution time (also output later for validation)
                    cur.execute("explain analyze "+contents)
                    with open(os.path.join(output_dir, "{}{}.{}.plan.anal.1".format(fname_num, fname_letter, estimate)), 'w') as plan_file:
                        lines = cur.fetchall()
                        for line in lines:
                            plan_file.write(line[0]+"\n")
                        execution_time1 = lines[-1][0].split()[2]
                        
                    #one last time to avoid cacheing effects
                    cur.execute("explain analyze "+contents)
                    with open(os.path.join(output_dir, "{}{}.{}.plan.anal.2".format(fname_num, fname_letter, estimate)), 'w') as plan_file:
                        lines = cur.fetchall()
                        for line in lines:
                            plan_file.write(line[0]+"\n")
                        execution_time2 = lines[-1][0].split()[2]
                    agg_data.write("{},{},{},{},{},{},{}\n".format(index, fname_num, fname_letter, estimate, 1 if new_plan else 0, execution_time1, execution_time2))
                index += 1
main()
