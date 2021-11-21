import os
import sys
from pathlib import Path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from preprocess.brat_document import BratDocument, BratR
from preprocess.config import Config
import preprocess.utils as utils


out_dir = os.path.join('ner','mod_202111')

newRs = [ f'R{i}' for i in range(1, 1000) ]
newTs = [ f'T{i}' for i in range(1, 1000) ]
newAs = [ f'A{i}' for i in range(1, 1000) ]
newEs = [ f'E{i}' for i in range(1, 1000) ]

def main():

    # Get data
    brat_train_raw = {} 
    for d in Config.annotation_train_dirs:
        brat_train_raw = {**brat_train_raw, **utils.fetch_brat_files(d)}
    annotations = [ BratDocument(k, v[0], v[1], v[2], surface_only=True) for k,v in brat_train_raw.items() ]

    for ann in annotations:
        if 'training' not in ann.path: continue
        #if ann.doc_id != 'NCT03930108': continue
        drop_t = []
        drop_e = []
        drop_a = []

        for _, t in ann.Ts.items():

            # Specimen
            if t.type in ['Observation-Specimen']:
                t.type = 'Specimen'

            # Code
            if t.type.endswith('Code'):
                t.type = 'Code'

        for _, e in ann.Es.items():

            for arg in e.args[1:]:
                if arg.type == 'Eq-Comparison':
                    arg.type = 'Numeric-Filter'

            # Encounter-Type
            if any(e.args) and e.args[0].type in ['Encounter']:
                to_del = -1
                for i, arg in enumerate(e.args): 
                    if arg.type == 'Type':
                        to_del = i
                        t = arg.get_T()
                        a = [ a for _, a in ann.As.items() if a.attr_of == t ]
                        a = a[0] if any(a) else None
                        drop_t.append(t)
                        a.attr_of = e
                        ann.As[a.id] = a
                del e.args[to_del]

            # Provider
            if any(e.args) and e.args[0].type in ['Provider']:
                for i, arg in enumerate(e.args): 
                    if arg.type in ['Role','Type']:
                        t = arg.get_T()
                        a = [ a for _, a in ann.As.items() if a.attr_of == t ]
                        a = a[0] if any(a) else None
                        drop_t.append(t)
                        drop_a.append(a)
                e.args = [ arg for arg in e.args if arg.type not in ['Role','Type'] ]

            # And / Or
            if any(e.args) and e.args[0].type in ['And','Or']:
                t = e.get_T()
                drop_e.append(e)
                drop_t.append(t)
                args1 = [ arg.val for arg in e.args[1:] if arg.type == 'Arg' ]
                args2 = [ arg.val for arg in e.args[1:] if arg.type != 'Arg' ]
                for arg1 in args1:
                    for arg2 in args2:
                        new_id = [ id for id in newRs if id not in ann.Rs ][0]
                        new_r = BratR(t.type, arg1, arg2, new_id, -1)
                        ann.Rs[new_r.id] = new_r

            # Temporal Connection
            if any(e.args) and e.args[0].type in ['Temporal-Connection']:
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
                            new_id = [ id for id in newRs if id not in ann.Rs ][0]
                            new_r = BratR(a.capitalize(), arg1, arg2, new_id, -1)
                            ann.Rs[new_r.id] = new_r
        
        for x in drop_e:
            if x:
                del ann.Es[x.id]
        for x in drop_t:
            if x:
                del ann.Ts[x.id]
        for x in drop_a:
            if x:
                del ann.As[x.id]

        filename = os.path.join(out_dir, os.path.basename(ann.path), ann.doc_id)
        txt, ann = ann.to_brat()
        Path(filename).parent.mkdir(parents=True, exist_ok=True)

        with open(f'{filename}.ann', 'w+', encoding='utf-8') as fout:
            fout.write(ann)
        with open(f'{filename}.txt', 'w+', encoding='utf-8') as fout:
            fout.write(txt)


if __name__ == '__main__':
    main()        