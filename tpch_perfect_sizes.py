import os
import struct

def main():
    NUM_QUERIES = 22 
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
                curr_bytes = struct.pack('q', -1)
                tpch_sizes.write(curr_bytes)
        for query_num in range(1,23,1):
            print query_num
            if query_num in exclude:
                continue
            with open('tpch-cards/{}.csv'.format(query_num), 'r') as card_file:
                print table_map[query_num]
                lines = card_file.read().split("\n")[1:]
                for line in lines:
                    tables = line.split(',')[0].split("-")
                    if len(tables) < 1 or tables[0] == '':
                        continue
                    card = long(line.split(',')[1])
                    comb = 0
                    for table in tables:
                        comb |= table_map[query_num][table]
                    tpch_sizes.seek((query_num*NUM_COMBS+comb)*8, 0)
                    struct.pack('q', card)



        """
    with open('tpch_sizes', 'wb') as fout:
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
        """

    print "Total Count: ", count

main()
