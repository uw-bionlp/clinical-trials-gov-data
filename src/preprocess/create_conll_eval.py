import sys

gold_path = sys.argv[1]
test_path = sys.argv[2]

with open (gold_path, 'r') as gold:
    with open(test_path, 'r') as test:
        test_lines = test.readlines()
        for i, gold_line in enumerate(gold.readlines()):

            gold_parts = gold_line.split()
            test_parts = test_lines[i].strip().split()

            if not gold_line.strip() or not any(gold_parts):
                print()
                continue

            if gold_parts[0] != test_parts[0]:
                print(f'On line {i}, gold text "{gold_parts[0]}" did not match test text "{test_parts[0]}!"')
                exit()

            print(f'{gold_line.strip()} {test_parts[-1]}')
            
