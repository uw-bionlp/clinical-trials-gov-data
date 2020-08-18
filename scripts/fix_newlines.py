import os
import re

input_dirs = [ os.path.join('ner', 'nic'), os.path.join('ner', 'tony') ]
regex_num_start = r'^[0-9]+.'

def check_file(txt_path, ann_path):
    with open(txt_path, 'r') as f: txt = f.read()
    with open(ann_path, 'r') as f: ann = f.read()

    prev_newstart = False
    prev_ldist = 0
    orig_lines = txt.splitlines()

    for i,l in enumerate(txt.splitlines()):
        orig = l
        stripped = l.lstrip()
        ldist = len(orig) - len(stripped)

        if stripped.startswith('- ') or re.match(regex_num_start, stripped):
            prev_newstart = True
            if re.match(regex_num_start, stripped):
                ldist = len(orig) - len(re.sub(regex_num_start, stripped, ''))
            else:
                ldist = len(orig) - len(stripped[2:].lstrip())
            prev_ldist = ldist
            continue

        if ldist > 0 and prev_newstart and prev_ldist == ldist:
            print(f'Disjoined lines found in {txt_path} line {i}...')
            
            orig_lines[i-1] = orig_lines[i-1].rstrip() + ' ' + orig.lstrip()
            del orig_lines[i]
            new_txt = '\n'.join(orig_lines)
            orig_ann = ann.splitlines()

            for i2,ann_ln in enumerate(ann.splitlines()):
                if ann_ln.startswith('T'):
                    T, indexes, span = ann_ln.split('\t')
                    beg_idx, end_idx = indexes.split()[1:]
                    new_beg_idx = new_txt[:int(end_idx)].find(span.strip())
                    new_end_idx = new_beg_idx + len(span.strip())

                    if new_beg_idx != int(beg_idx) or new_end_idx != int(end_idx):
                        new_ann_ln = f'{T}\t{indexes.split()[0]} {new_beg_idx} {new_end_idx}\t{span}'
                        orig_ann[i2] = new_ann_ln
            new_ann = '\n'.join(orig_ann)

            with open(txt_path, 'w+') as f: f.write(new_txt)
            with open(ann_path, 'w+') as f: f.write(new_ann)
            return False

    return True
            

def main():
    for input_dir in input_dirs:
        for sub_dir in os.listdir(input_dir):
            txt_fls = [ fl for fl in os.listdir(os.path.join(input_dir, sub_dir)) if fl.endswith('.txt') ]
            ann_fls = [ fl for fl in os.listdir(os.path.join(input_dir, sub_dir)) if fl.endswith('.ann') ]

            for txt_fl in txt_fls:
                file_done = False
                txt_path = os.path.join(input_dir, sub_dir, txt_fl)
                ann_path = txt_path.replace('.txt','.ann')

                while not file_done:
                    file_done = check_file(txt_path, ann_path)


main()