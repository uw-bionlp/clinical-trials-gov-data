import os
import re
import sys
sys.path.append(os.path.join(os.getcwd(), 'src'))

from ner.preprocess.brat_document import BratDocument
import ner.preprocess.utils as utils

regex_temporal = r'(past|previous|prior|history|received|administered|underwent|current|active|using|taking|undergoing)'
past = [ 'past', 'previously', 'previous', 'prior', 'history', 'received', 'administered', 'underwent' ]
cnt = 0

def main():
    topdir = 'ner/nic'
    for subdir in [ d for d in os.listdir(topdir) if os.path.isdir(os.path.join(topdir,d)) ]:
        brat_raw = utils.fetch_brat_files(os.path.join(topdir, subdir))
        annotations = [ BratDocument(k, v[0], v[1], v[2]) for k,v in brat_raw.items() ]
        for ann in annotations:
            add_temporal_period(ann)
    
    print(f'{cnt} updated!')

def add_temporal_period(doc):
    global cnt
    matches = [ ParsedObject(x.start(), x.end(), i, doc.raw_text) for i,x in enumerate(re.finditer(regex_temporal, doc.raw_text, re.I)) ]
    for match in matches:
        raw_ann_check = doc.raw_anns.find(f'{match.start} {match.end}')
        annotated = [ v for k,v in doc.Ts.items() if v.char_beg_idx <= match.start and v.char_end_idx >= match.end ]
        if raw_ann_check == -1 and not any(annotated):
            cnt += 1
            maxT = max([ int(v.id.replace('T','')) for k,v in doc.Ts.items() ]) if len(doc.Ts) else 0
            maxE = max([ int(v.id.replace('E','')) for k,v in doc.Es.items() ]) if len(doc.Es) else 0
            maxA = max([ int(v.id.replace('A','')) for k,v in doc.As.items() ]) if len(doc.As) else 0
            match_text = doc.raw_text[match.start:match.end]
            tp = 'past' if match_text.lower() in past else 'present'
            T  = f'T{maxT+1}\tEq-Comparison {match.start} {match.end}\t{match_text}'
            T2 = f'T{maxT+2}\tEq-Temporal-Period {match.start} {match.end}\t{match_text}'
            E  = f'E{maxE+1}\tEq-Comparison:T{maxT+1} Temporal-Period:T{maxT+2}'
            A  = f'A{maxA+1}\tEq-Temporal-Period-Value T{maxT+2} {tp}'
            nl = '\n'

            with open(f'{os.path.join(doc.path, doc.doc_id)}.ann', 'r') as f:
                curr_anns = f.read()
            
            new_anns = f'{curr_anns.strip()}{nl}{f"{nl}".join([ T, E, T2, A ])}'

            with open(f'{os.path.join(doc.path, doc.doc_id)}.ann', 'w') as f:
                f.write(new_anns)
            doc = BratDocument(doc.doc_id, doc.raw_text, new_anns, doc.path)
            

class ParsedObject():
    def __init__(self, start, end, idx, content):
        self.start = start
        self.end   = end
        self.idx   = idx
        self.text  = content[self.start:self.end]

main()
