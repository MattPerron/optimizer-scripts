#!/usr/bin/python
def main():
    first_line = True
    current_query = -1
    with open("aggregate_data.csv", 'r') as agg, open("perfect_estimates.csv", 'w') as est:
        for line in agg:
            if first_line:
                first_line = False
                continue
            split_line = line.split(',')
            if int(split_line[0]) != current_query:
                est.write("\n{},{}{},".format(split_line[0], split_line[1],split_line[2]))
                current_query = int(split_line[0])
            est.write("{},".format(split_line[6][:-1]))


main()
