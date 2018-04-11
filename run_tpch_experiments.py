#!/usr/bin/python
from __future__ import print_function
import os
import sys
import psycopg2 as pg

def main():
    simple_costs = False 
    use_nestloop = True
    use_seqscan = True
    index = 0
    output_dir = "tpch_pg_cost"
    table_count = {}
    with open('tpch-table-mapping.csv', 'r') as table_map_file:
        query_num = 1
        for line in table_map_file:
            table_count[query_num] = len(line.split(','))
            query_num += 1
    with pg.connect('host=localhost user=matt dbname=tpch') as conn, conn.cursor() as cur, open(os.path.join(output_dir, "aggregate_data.csv"), 'w', 1) as agg_data:
        agg_data.write("query_index, query_name, num_tables, perfect_estimates, new_plan, execution_time1, execution_time2\n")
        for query_num in range(1, 23):
            explain_filename = "tpch-queries/{}-explain.sql".format(query_num)
            with open(explain_filename, 'r') as f:
                explain_contents = f.read()
            explain_analyze_filename = "tpch-queries/{}-explain-analyze.sql".format(query_num)
            with open(explain_analyze_filename, 'r') as f:
                explain_analyze_contents = f.read()
            counting = False
            max_table_count = table_count[query_num] 
            plans = [None for i in range(max_table_count+1)]
            for estimate in range(max_table_count, max_table_count+1):
                print(explain_filename, estimate) 
                #explain once to get the plan
                cur.execute("set current_test_query={};".format(index))
                cur.execute("set perfect_estimates={};".format(estimate))
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
                cur.execute(explain_contents);
                plan = ''
                with open(os.path.join(output_dir, "{}.{}.plan".format(query_num, estimate)), 'w') as plan_file:
                    for line in cur.fetchall():
                        plan = plan+line[0]+"\n"
                        plan_file.write(line[0]+"\n")
                new_plan = plan not in plans
                plans[estimate] = plan

                #execute it again to get the execution time (also output later for validation)
                cur.execute(explain_analyze_contents)
                with open(os.path.join(output_dir, "{}.{}.plan.anal.1".format(query_num, estimate)), 'w') as plan_file:
                    lines = cur.fetchall()
                    for line in lines:
                        plan_file.write(line[0]+"\n")
                    execution_time1 = lines[-1][0].split()[2]
                    
                #one last time to avoid cacheing effects
                cur.execute(explain_analyze_contents)
                with open(os.path.join(output_dir, "{}.{}.plan.anal.2".format(query_num, estimate)), 'w') as plan_file:
                    lines = cur.fetchall()
                    for line in lines:
                        plan_file.write(line[0]+"\n")
                    execution_time2 = lines[-1][0].split()[2]
                agg_data.write("{},{},{},{},{},{}\n".format(index, query_num, estimate, 1 if new_plan else 0, execution_time1, execution_time2))
            index += 1
main()
