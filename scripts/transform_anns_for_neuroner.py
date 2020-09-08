import os
import sys
sys.path.append(os.path.join(os.getcwd(), 'src'))
from preprocess.config import Config
from preprocess.brat_document import BratDocument
import preprocess.utils as utils

output_dir = os.path.join('data', 'ner', 'neuroner')

def main():
    brat_train_raw = {} 
    for d in Config.annotation_train_dirs:
        brat_train_raw = {**brat_train_raw, **utils.fetch_brat_files(d)}
    annotations = [ BratDocument(k, v[0], v[1], v[2]) for k,v in brat_train_raw.items() ]

    for ann in annotations:
        event_types = set([ v.args[0].type for k, v in ann.Es.items() ])
        seen = set()

        with open(os.path.join(output_dir, 'events', ann.doc_id+'.txt'), 'w+') as f_ev, \
             open(os.path.join(output_dir, 'entities', ann.doc_id+'.txt'), 'w+') as f_ent:
             f_ev.write(ann.raw_text)
             f_ent.write(ann.raw_text)

        with open(os.path.join(output_dir, 'events', ann.doc_id+'.ann'), 'w+') as f_ev, \
             open(os.path.join(output_dir, 'entities', ann.doc_id+'.ann'), 'w+') as f_ent:

            for k,t in ann.Ts.items():
                if k in seen: continue
                tp = t.type

                # Events
                if t.type in event_types:
                    overlap = [ (k2, t2) for k2, t2 in ann.Ts.items() if t2 != t and t2.type in event_types and t2.char_beg_idx == t.char_beg_idx and t2.char_end_idx == t.char_end_idx ]
                    overlap_k, overlap = overlap[0][0] if len(overlap) else None, overlap[0][1] if len(overlap) else None

                    a = [ a_v for a_k, a_v in ann.As.items() if a_v.attr_of.get_T() == t ]
                    a = a[0] if len(a) else None
                    if a:
                        tp = tp + '___' + a.type + ':' + a.val

                    if overlap:
                        seen.add(overlap)
                        overlap_tp = overlap.type
                        a2 = [ a_v for a_k, a_v in ann.As.items() if a_v.attr_of.get_T() == overlap ]
                        a2 = a2[0] if len(a2) else None
                        if a2:
                            overlap_tp = overlap_tp + '___' + a2.type + ':' + a2.val
                        tp = '|'.join(sorted([ tp, overlap_tp ]))
                    write_to = f_ev

                # Entities
                else:
                    a = [ a_v for a_k, a_v in ann.As.items() if a_v.attr_of == t ]
                    a = a[0] if len(a) else None
                    if a:
                        tp = tp + '___' + a.type + ':' + a.val
                    write_to = f_ent

                if tp == 'Coreference':
                    continue
                if 'Coreference' in tp:
                    tp = tp.replace('Coreference','').replace('|','').strip()
                
                T = f'{t.id}\t{tp} {t.char_beg_idx} {t.char_end_idx}\t{t.span}'
                write_to.write(f'{T}\n')

main()
