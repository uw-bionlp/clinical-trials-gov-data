import os
import re
from re import IGNORECASE
import sys
import numpy as np
sys.path.append(os.path.join(os.getcwd(), 'src'))

from preprocess.brat_document import BratDocument, BratA, BratT, BratEArgPair
from preprocess.config import Config
import preprocess.utils as utils


regex_asa = r'(American.*Anes.*)'
regex_nyha = r'(NYHA|New York Heart Assoc.*)'
regex_chronic = r'(chronic|long[ |-]term)'


def to_brat(output_dir, doc_id, Ts, text):
    with open(os.path.join(output_dir, doc_id+'.txt'), 'w+') as fout:
        fout.write(text)
    with open(os.path.join(output_dir, doc_id+'.ann'), 'w+') as fout:
        fout.write('\n'.join(Ts)) 

def chronic(annotations):
    ''' Convert 'Chronic' Modifier -> Acuteness[chronic] '''
    for ann in annotations:
        matched  = [ v for _,v in ann.Ts.items() if re.match(regex_chronic, v.span, re.IGNORECASE) and v.type == 'Modifier' ]
        if len(matched):
            max_a = max([ int(a.id.replace('A','')) for _,a in ann.As.items() ])+1 if len(ann.As) else 1
            for rec in matched:
                rec.type = 'Acuteness'
                a_id = f'A{max_a}'
                a = BratA('Acuteness-Type-Value', rec, 'chronic', a_id, -1)
                ann.As[a_id] = a
                max_a += 1
                ann.Ts[rec.id] = rec
                e = [ v for _,v in ann.Es.items() if v.args[0].val == rec ]
                if len(e):
                    e = e[0]
                    try:
                        condition = [ arg for arg in e.args if arg.type == 'Modifies' ][0].val
                        if isinstance(condition, BratT):
                            condition = [ v for _,v in ann.Es.items() if any([ arg for arg in v.args if arg.val == condition and arg.type == 'Name' ]) ][0]
                        new_arg = BratEArgPair('Acuteness', rec)
                        condition.args.append(new_arg)
                    except:
                        print(f'{ann.path}/{ann.doc_id} has a malformed Modifer!')
                    del ann.Es[e.id]
    return annotations

def acute(annotations):
    ''' Convert 'Acute' Severity -> Acuteness[acute] '''
    for ann in annotations:
        matched  = [ v for _,v in ann.Ts.items() if v.span.lower() == 'acute' and v.type == 'Severity' ]
        if len(matched):
            max_a = max([ int(a.id.replace('A','')) for _,a in ann.As.items() ])+1 if len(ann.As) else 1
            for rec in matched:
                rec.type = 'Acuteness'
                a_id = f'A{max_a}'
                a = BratA('Acuteness-Type-Value', rec, 'acute', a_id, -1)
                ann.As[a_id] = a
                max_a += 1
                ann.Ts[rec.id] = rec
                es = [ v for _,v in ann.Es.items() if any([ arg for arg in v.args if arg.val == rec and arg.type == 'Severity' ]) ]
                for e in es:
                    arg = [ arg for arg in e.args if arg.val == rec and arg.type == 'Severity' ][0]
                    arg.type = 'Acuteness'
    return annotations

def asa_and_nyha(annotations):
    ''' Convert ASA & NYHA Condition -> Observation[clinical-score] '''
    for ann in annotations:
        asa  = [ v for _,v in ann.Ts.items() if (v.span == 'ASA' or re.match(regex_asa, v.span, re.IGNORECASE)) and v.type in [ 'Condition', 'Condition-Name'] ]
        nyha = [ v for _,v in ann.Ts.items() if re.match(regex_nyha, v.span, re.IGNORECASE) and v.type in [ 'Condition', 'Condition-Name'] ]
        if len(asa) or len(nyha):
            max_a = max([ int(a.id.replace('A','')) for _,a in ann.As.items() ])+1 if len(ann.As) else 1
            for rec in asa+nyha:
                if rec.type == 'Condition-Name':
                    rec.type = 'Observation-Name'
                    a_id = f'A{max_a}'
                    a = BratA('Observation-Type-Value', rec, 'clinical-score', a_id, -1)
                    ann.As[a_id] = a
                    max_a += 1
                elif rec.type == 'Condition':
                    rec.type = 'Observation'
                    e = [ v for _,v in ann.Es.items() if v.args[0].val == rec ][0]
                    e.type = rec.type
                    ann.Es[e.id] = e
                ann.Ts[rec.id] = rec
    return annotations


def main():

    conll_path = os.path.join(Config.preprocess_dir, 'conll')
    if not os.path.exists(conll_path): 
        os.mkdir(conll_path)

    # Get data
    brat_train_raw = {} 
    for d in Config.annotation_train_dirs:
        brat_train_raw = {**brat_train_raw, **utils.fetch_brat_files(d)}
    annotations = [ BratDocument(k, v[0], v[1], v[2], surface_only=True) for k,v in brat_train_raw.items() ]

    # Convert
    for converter in [ chronic ]:
        annotations = converter(annotations)
    

    
if __name__ == '__main__':
    main()