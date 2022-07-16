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

    types = { 'Contraindication': {}, 'Indication': {}, 'Risk': {} }

    for ann in annotations:

        for _, rel in ann.Rs.items():
            arg1 = rel.arg1.get_T()
            arg2 = rel.arg2.get_T()
            rel_type = rel.type

            if arg1.span.lower() == arg2.span.lower():
                continue

            if rel_type == 'Example-Of':
                for tp in types:
                    if arg2.type == tp:
                        of_interest = [ r.val.get_T().span for r in rel.arg2.args[1:] if r.type in ['Contraindicates','Indication-For','Risk-For'] ]
                        for val in of_interest:
                            if val.lower() in types[tp]:
                                types[tp][val.lower()].add(arg1.span)
                            else:
                                types[tp][val.lower()] = set([ arg1.span ])

            #if rel.type == 'Equivalent-To' and arg1.type in ['Procedure','Condition'] and arg2.type in ['Observation']:
            #    print(f'"{arg1}" {rel_type} "{arg2}"')

            #if rel.type == 'Example-Of' and arg1.type in ['Procedure','Condition'] and arg2.type in ['Contraindication','Indication']:
            #    print(f'"{arg1}" {rel_type} "{arg2}"')

    for tp, data in sorted(types.items()):
        print(tp)
        for element, values in data.items():
            print(f'  "{element}"')
            for val in sorted(values):
                print(f'    "{values}"')


main()