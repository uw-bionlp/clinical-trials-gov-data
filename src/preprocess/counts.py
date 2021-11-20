import os
import re
import sys
sys.path.append(os.path.join(os.getcwd(), 'src'))

from preprocess.brat_document import BratDocument
from preprocess.config import Config
import preprocess.utils as utils

regex_trailing_num = r'\d'

def main():

    # Get data
    brat_train_raw = {} 
    for d in Config.annotation_train_dirs:
        brat_train_raw = {**brat_train_raw, **utils.fetch_brat_files(d)}
    annotations = [ BratDocument(k, v[0], v[1], v[2], surface_only=True) for k,v in brat_train_raw.items() ]

    As, Rs, Ts, Es, args, ents = {}, {}, {}, {}, {}, {}
    for ann in annotations:
        for _, t in ann.Ts.items():
            if t.type in Ts: Ts[t.type] += 1
            else:            Ts[t.type] = 1
            if not any([ e for _, e in ann.Es.items() if any(e.args) and e.args[0].val == t ]):
                if t.type in ents: ents[t.type] += 1
                else:              ents[t.type] = 1
        for _, e in ann.Es.items():
            if any(e.args):
                if e.args[0].type in Es: Es[e.args[0].type] += 1
                else:                    Es[e.args[0].type] = 1
                for arg in e.args[1:]:
                    if any(re.findall(regex_trailing_num, arg.type)):
                        arg.type = re.sub(regex_trailing_num, '', arg.type)
                    if arg.type in args: args[arg.type] += 1
                    else:                args[arg.type] = 1
        for _, r in ann.Rs.items():
            if r.type in Rs: Rs[r.type] += 1
            else:            Rs[r.type] = 1
        for _, a in ann.As.items():
            if a.type in As: As[a.type] += 1
            else:            As[a.type] = 1

    #args = { k:v for k, v in args.items() if k not in ['Name', 'Unit', 'Value', 'Temporal-Period', 'Temporal-Recency', 'Temporal-Unit', 'Per', 'Dose', 'Operator'] }

    t_sum_cnt = sum([ cnt for t, cnt in Ts.items() ])
    print('Ts', t_sum_cnt)
    for t, cnt in sorted(Ts.items()):
        print('\t', t, cnt, round(cnt / t_sum_cnt * 100.0, 1))

    r_sum_cnt = sum([ cnt for r, cnt in Rs.items() ])
    print('Rs', r_sum_cnt)
    for r, cnt in sorted(Rs.items()):
        print('\t', r, cnt, round(cnt / r_sum_cnt * 100.0, 1))

    arg_sum_cnt = sum([ cnt for arg, cnt in args.items() ])
    print('Args', arg_sum_cnt)
    for arg, cnt in sorted(args.items()):
        print('\t', arg, cnt, round(cnt / arg_sum_cnt * 100.0, 1))


if __name__ == '__main__':
    main()