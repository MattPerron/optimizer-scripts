import os
import struct

def main():
    NUM_QUERIES = 113 
    NUM_COMBS = 150000
    LONG_SIZE = 8
    count = 0
    table_map = {}
    #set up map
    for i in range(1,23,1):
        table_map[i] = {}
    query = 1
    exclude = [2, 15]
    with open('tpch-table-mapping.csv', 'r') as table_map_file:
        for line in table_map_file:
            tables = line.strip().split(',')
            index = 0
            for table in tables:
                table_map[query][table] = index
                index+=1
            query+=1
    with open('tpch_sizes', 'wb') as tpch_sizes:
        for query_num in range(NUM_QUERIES):
            for comb in range(NUM_COMBS):
                curr_bytes = struct.pack('q', long(-1))
                tpch_sizes.write(curr_bytes)
        for query_num in range(1,23,1):
            if query_num in exclude:
                continue
            with open('tpch-cards/{}.csv'.format(query_num), 'r') as card_file:
                lines = card_file.read().split("\n")[1:]
                for line in lines:
                    tables = line.split(',')[0].split("-")
                    if len(tables) < 1 or tables[0] == '':
                        continue
                    card = long(line.split(',')[1])
                    comb = 0
                    for table in tables:
                        comb = comb | 1<<(table_map[query_num][table])
                    if card == 38760:
                        print card, bin(comb).count("1"), comb 
                    tpch_sizes.seek((query_num*NUM_COMBS+comb)*LONG_SIZE, 0)
                    tpch_sizes.write(struct.pack('q', card))
    print "Total Count: ", count

main()
