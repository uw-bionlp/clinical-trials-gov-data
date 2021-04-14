import os
import re
import sys
sys.path.append(os.path.join(os.getcwd(), 'src'))

from preprocess.brat_document import BratDocument, BratA, BratT, BratEArgPair
import preprocess.utils as utils

# Get data
brat_raw = {**utils.fetch_brat_files(os.path.join('data/ner/chia_with_scope'))}
annotations = [ BratDocument(k, v[0], v[1], v[2], surface_only=True) for k,v in brat_raw.items() ]

As, Rs, Ts, Es, args, ents = {}, {}, {}, {}, {}, {}
for ann in annotations:
    for _, t in ann.Ts.items():
        if t.type in Ts: Ts[t.type] += 1
        else:            Ts[t.type] = 1
        if not any([ e for _, e in ann.Es.items() if any(e.args) and e.args[0].val == t ]):
            if t.type in ents: ents[t.type] += 1
            else:              ents[t.type] = 1
    for _, t in ann.Es.items():
        if any(t.args):
            if t.args[0].type in Es: Es[t.args[0].type] += 1
            else:                    Es[t.args[0].type] = 1
            for arg in t.args[1:]:
                if arg.type in args: args[arg.type] += 1
                else:                args[arg.type] = 1
    for _, r in ann.Rs.items():
        if r.type in Rs: Rs[r.type] += 1
        else:            Rs[r.type] = 1
    for _, r in ann.As.items():
        if r.type in As: As[r.type] += 1
        else:            As[r.type] = 1
sum_cnt = sum([ cnt for t, cnt in Ts.items() ])
print('Ts', sum_cnt)
for t, cnt in sorted(Ts.items()):
    print('\t', t, cnt, round(cnt / sum_cnt * 100.0, 1))
sum_cnt = sum([ cnt for r, cnt in Rs.items() ])
print('Rs', sum_cnt)
for r, cnt in sorted(Rs.items()):
    print('\t', r, cnt, round(cnt / sum_cnt * 100.0, 1))