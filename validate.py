import os

def main():
    path = 'no_base_simple_cost_no_seqscan'
    letters = ['a','b','c','d','e','f']
    for num in range(1, 34, 1):
        for letter in letters:
            highest=-1
            best_filename = ''
            if not os.path.exists(os.path.join(path, "{}{}.0.plan".format(num, letter))):
                continue
            for est in range(0, 25, 1):
                filename = os.path.join(path, "{}{}.{}.plan.anal.2".format(num, letter, est))
                if os.path.exists(filename):
                    highest = est 
                    best_filename = filename
            with open(best_filename, 'r') as best_file:
                for line in best_file:
                    if line.find("Nested Loop") >= 0 or line.find("Merge Join") >= 0 or line.find("Hash Join") >= 0:
                        first_rows = -1
                        second_rows = -1
                        split_line = line.split(' ')
                        for phrase in split_line:
                            split_phrase = phrase.split("=")
                            if split_phrase[0]=="rows":
                                if first_rows == -1:
                                    first_rows = int(split_phrase[1])
                                else:
                                    second_rows = int(split_phrase[1])
                        if(first_rows != second_rows):
                            print best_filename
                            print line[:-1]
                            print first_rows, second_rows
                            return

main()
