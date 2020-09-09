import os 
import sys
from pathlib import Path

inpt_dir = os.path.join('data','ner','neuroner','predict')
event_dir = os.path.join(inpt_dir, 'events')
entity_dir = os.path.join(inpt_dir, 'entities')
out_dir = os.path.join(inpt_dir, 'final')

def main():

    for d in os.listdir(event_dir):
        batch_dir = os.path.join(event_dir, d)
        Path(os.path.join(out_dir, d)).mkdir(parents=True, exist_ok=True)
        for fl in os.listdir(batch_dir):

            if fl.endswith('.txt'):
                continue

            text_path = os.path.join(event_dir, d, fl.replace('.ann', '.txt'))
            ev_path = os.path.join(event_dir, d, fl)
            ent_path = os.path.join(entity_dir, d, fl)
            out_path = os.path.join(out_dir, d, fl)
            evs, ents, As = [], [], []

            with open(ev_path, 'r') as f:
                for l in f.read().splitlines():
                    tsplit = l.split('\t')
                    ssplit = tsplit[1].split(' ')
                    evs.append({ 'id': tsplit[0], 'type': ssplit[0], 'beg_idx': ssplit[1], 'end_idx': ssplit[2], 'text': tsplit[2] })

            with open(ent_path, 'r') as f:
                for l in f.read().splitlines():
                    tsplit = l.split('\t')
                    ssplit = tsplit[1].split(' ')
                    ents.append({ 'id': tsplit[0], 'type': ssplit[0], 'beg_idx': ssplit[1], 'end_idx': ssplit[2], 'text': tsplit[2] })

            # Copy text file over
            with open(text_path, 'r') as f:
                out_text_path = os.path.join(out_dir, d, fl.replace('.ann', '.txt'))
                with open(out_text_path, 'w+') as f2:
                    f2.write(f.read())

            T_i, A_i, E_i = 1, 1, 1

            # Split events, reset T ids
            for grp in [ evs, ents ]:
                i = 0
                while i < len(grp):
                    grp[i]['id'] = f'T{T_i}'
                    T_i += 1
                    splt = grp[i]['type'].split('|')
                    if len(splt) > 1:
                        e2 = grp[i].copy()
                        e2['type'] = splt[1]
                        e2['id'] = f'T{T_i}'
                        T_i += 1
                        grp[i]['type'] = splt[0]
                        grp.append(e2)
                    i += 1

            # Write events
            to_write = []
            with open(out_path, 'w+') as f:
                for ev in evs:
                    a = ev['type'].split('---')
                    if len(a) > 1:
                        splt = a[1].split(':')
                        a_tp, a_val = splt[0], splt[1]
                        ev['type'] = a[0]
                        A = f"A{A_i}\t{a_tp} E{E_i} {a_val}"
                        A_i += 1
                    else:
                        A = None
                    T = f"{ev['id']}\t{ev['type']} {ev['beg_idx']} {ev['end_idx']}\t{ev['text']}"
                    raw_args = [ ent for ent in ents if int(ent['beg_idx']) >= int(ev['beg_idx']) and int(ent['end_idx']) <= int(ev['end_idx']) ]
                    arg_strs = [ f"{ev['type']}:{ev['id']}" ]
                    for arg in raw_args:
                        arg_tp = arg['type'].split('---')[0]
                        if ev['type'] in [ 'Condition', 'Procedure', 'Allergy', 'Observation', 'Drug' ] and arg_tp == ev['type']+'-Name':
                            arg_strs.append(f"{'Name'}:{arg['id']}")
                        elif ev['type'] == 'Eq-Comparison':
                            if arg_tp not in [ 'Eq-Operator', 'Eq-Temporal-Unit', 'Eq-Unit', 'Eq-Value', 'Eq-Temporal-Period', 'Eq-Temporal-Recency' ]:
                                continue
                            arg_tp = arg_tp.replace('Eq-Operator-','').replace('Eq-','')
                            arg_strs.append(f"{arg_tp}:{arg['id']}")
                    E = f"E{E_i}\t{' '.join(arg_strs)}"
                    E_i += 1
                    to_write.append(T)
                    to_write.append(E)
                    if A: to_write.append(A)

                # Write entities
                for ent in ents:
                    a = ent['type'].split('---')
                    if len(a) > 1:
                        splt = a[1].split(':')
                        a_tp, a_val = splt[0], splt[1]
                        ent['type'] = a[0]
                        A = f"A{A_i}\t{a_tp} {ent['id']} {a_val}"
                        A_i += 1
                    else:
                        A = None

                    T = f"{ent['id']}\t{ent['type']} {ent['beg_idx']} {ent['end_idx']}\t{ent['text']}"
                    to_write.append(T)
                    if A: to_write.append(A)

                to_write = '\n'.join(to_write)
                f.write(to_write)

main()