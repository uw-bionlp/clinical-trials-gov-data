import os
import sys
sys.path.append(os.path.join(os.getcwd(), 'src'))

from preprocess.brat_document import BratDocument, BratR
from preprocess.config import Config
import preprocess.utils as utils


def main():

    # Get data
    brat_train_raw = {} 
    for d in Config.annotation_train_dirs:
        brat_train_raw = {**brat_train_raw, **utils.fetch_brat_files(d)}
    annotations = [ BratDocument(k, v[0], v[1], v[2], surface_only=True) for k,v in brat_train_raw.items() ]

    drop_t = []
    drop_e = []
    drop_a = []

    for ann in annotations:
        for _, t in ann.Ts.items():

            # Provider Role / Type
            if t.type in ['Provider-Role','Provider-Type']:
                x=1

            # Specimen
            if t.type in ['Observation-Specimen']:
                t.type = 'Specimen'

            # Encounter-Type
            if t.type in ['Encounter-Type']:
                a = [ a for _, a in ann.As.items() if a.attr_of == t ]
                if any(a):
                    a = a[0]
                    x=1

            # Code
            if t.type.endswith('Code'):
                t.type = 'Code'

        for _, e in ann.Es.items():

            # And / Or
            if e.args[0].type in ['And','Or']:
                t = e.get_T()
                drop_e.append(e)
                drop_t.append(t)
                args1 = [ arg.val for arg in e.args[1:] if arg.type == 'Arg' ]
                args2 = [ arg.val for arg in e.args[1:] if arg.type != 'Arg' ]
                for arg1 in args1:
                    for arg2 in args2:
                        new_r = BratR(t.type, arg1, arg2, f'R{len(ann.Rs)+1}', -1)
                        ann.Rs[new_r.id] = new_r

            # Temporal Connection
            if e.args[0].type in ['Temporal-Connection']:
                t = e.get_T()
                drop_e.append(e)
                drop_t.append(t)
                a = [ a for _, a in ann.As.items() if a.attr_of == e ]
                if any(a):
                    drop_a.append(a[0])
                    a = a[0].val
                    args1 = [ arg.val for arg in e.args[1:] if arg.type == 'Arg' ]
                    args2 = [ arg.val for arg in e.args[1:] if arg.type != 'Arg' ]
                    for arg1 in args1:
                        for arg2 in args2:
                            new_r = BratR(a.capitalize(), arg1, arg2, f'R{len(ann.Rs)+1}', -1)
                            ann.Rs[new_r.id] = new_r
                    

        for _, r in ann.Rs.items():
            pass
        for _, a in ann.As.items():
            pass

if __name__ == '__main__':
    main()        