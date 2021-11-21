import os
import sys
sys.path.append(os.path.join(os.getcwd(), 'src'))

from preprocess.brat_document import BratDocument
from preprocess.config import Config
import preprocess.utils as utils


def main():

    # Get data
    brat_train_raw = {} 
    for d in Config.annotation_train_dirs:
        brat_train_raw = {**brat_train_raw, **utils.fetch_brat_files(d)}
    annotations = [ BratDocument(k, v[0], v[1], v[2], surface_only=True) for k,v in brat_train_raw.items() ]

    type1_name = 'Condition'
    type2_name = 'Observation'

    type1 = []
    type2 = []

    for ann in annotations:
        for _, e in ann.Es.items():
            t = e.get_T()

            if any(e.args) and e.args[0].type == type1_name:
                type1.append(t)
            elif any(e.args) and e.args[0].type == type2_name:
                type2.append(t)

    unq_type1 = set([ x.span.lower() for x in type1 ])
    unq_type2 = set([ x.span.lower() for x in type2 ])
    both = set([ x for x in unq_type1 if x in unq_type2 ])

    for span in sorted(both):
        type1_cnt = len([ x for x in type1 if x.span.lower() == span ])
        type2_cnt = len([ x for x in type2 if x.span.lower() == span ])
        print(f'{span.rjust(20, " ")} {type1_name}: {type1_cnt}, {type2_name}: {type2_cnt}')

if __name__ == '__main__':
    main()        