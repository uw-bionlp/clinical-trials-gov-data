import os
import sys

sys.path.append(os.path.join(os.getcwd(), 'src'))

from preprocess.brat_document import BratDocument
from preprocess.config import Config
import preprocess.utils as utils

def main():
    brat_train_raw = {} 
    for d in Config.annotation_train_dirs:
        brat_train_raw = {**brat_train_raw, **utils.fetch_brat_files(d)}
    annotations = [ BratDocument(k, v[0], v[1], v[2]) for k,v in brat_train_raw.items() ]
        
    output_dir = os.path.join('../clinical_trials_query_gen','data','seq2seq', 'annotation')

    for d in [ 'completed', 'reviewing' ]:
        for b in os.listdir(os.path.join(output_dir, d)):
            for f in os.listdir(os.path.join(output_dir, d, b)):
                filename = os.path.join(output_dir, d, b, f)

                with open(filename, 'r') as fin:
                    full_text = fin.read().strip()
                    lines = full_text.splitlines()

                nct_filename = f.split('_')[0]
                line_num     = int(f.replace('.js','').split('_')[1])

                needs_inc_exc = False
                for line in lines:
                    if not line:
                        continue
                    if line[0] == "'":
                        line_no_quotes = line.replace("'","")
                        needs_inc_exc = line_no_quotes not in {'INC','EXC'}
                        break

                if needs_inc_exc:
                    elig_text = [ a for a in annotations if a.doc_id == nct_filename ][0].raw_text
                    exc_line = get_exc_line_idx(elig_text)
                    inc_exc = "'INC'" if line_num < exc_line else "'EXC'"
                    new_full_text = inc_exc + '\n\n' + full_text
                    with open(filename, 'w+') as fout:
                        fout.write(new_full_text)



def get_exc_line_idx(full_text):
    for i, line in enumerate(full_text.splitlines()):
        if 'Exclusion' in line:
            return i
    return 100000


main()
            
