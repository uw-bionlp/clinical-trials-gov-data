import os
import sys
import math
import random
sys.path.append(os.path.join(os.getcwd(), 'src'))

from preprocess.config import Config
from preprocess.brat_document import BratDocument
import preprocess.utils as utils

output_dir = os.path.join('data', 'ner', 'bio')
random.seed(42)
use_cleaned = True


label_overrides = {
    'B-Age|I-Eq_Comparison': 'I-Eq_Comparison',
    'B-Age|B-Eq_Comparison': 'B-Eq_Comparison',
    'I-Eq_Comparison|I-Observation': 'I-Eq_Comparison',
    'I-Eq_Comparison|B-Observation': 'I-Eq_Comparison|B-Observation',
    'B-Assertion___Assertion_Type_Value:hypothetical|B-Modifier': 'B-Assertion___Assertion_Type_Value:hypothetical',
    'B-Condition_Type___Condition_Type_Value:problem_list': 'O',
    'I-Condition_Type___Condition_Type_Value:problem_list': 'O',
    'B-Life_Stage_And_Gender___Life_Stage_And_Gender_Type:elderly': 'B-Life_Stage_And_Gender___Life_Stage_And_Gender_Type:adult',
    'I-Life_Stage_And_Gender___Life_Stage_And_Gender_Type:elderly': 'I-Life_Stage_And_Gender___Life_Stage_And_Gender_Type:adult'
}


def main():
    brat_train_raw = {} 
    for d in Config.annotation_train_dirs:
        brat_train_raw = {**brat_train_raw, **utils.fetch_brat_files(d)}
    annotations = [ BratDocument(k, v[0], v[1], v[2]) for k,v in brat_train_raw.items() ]
    random.shuffle(annotations)

    total_cnt = len(annotations)
    train_cnt = 0
    train_desired = math.floor(total_cnt * 0.8)

    for ann in annotations:
        event_types = set([ v.args[0].type for k, v in ann.Es.items() ])
        file = 'train.txt' if train_cnt < train_desired else 'test.txt'

        if train_cnt < train_desired: 
            train_cnt += 1

        for d in ['events','entities']:
            if not os.path.exists(os.path.join(output_dir, d)): 
                os.mkdir(os.path.join(output_dir, d))

        toks_with_entities = [[x, [t for _,t in ann.Ts.items() if t.type not in event_types and x.i in t.tok_idxs]] for x in ann.toks]
        toks_with_events   = [[x, [t for _,t in ann.Ts.items() if t.type in event_types and x.i in t.tok_idxs]] for x in ann.toks]
        
        # Entities
        with open(os.path.join(output_dir, 'entities', file), 'a+', encoding='utf-8') as fout:
            fout.write('\n')
            for tok, entities in toks_with_entities:
                if '\n' in tok.text:
                    fout.write('\n')
                    continue
                txt = tok.text.strip()
                if not any(txt):
                    continue

                label = 'O'
                for e in sorted(entities, key=lambda x: x.type):
                    b_or_i = 'B-' if e.tok_idxs[0] == tok.i else 'I-'
                    tp = b_or_i + e.type.replace('-','_')
                    if e.type in ['Coreference']: 
                        continue

                    # Check for and add attribute
                    a = [ a_v for _, a_v in ann.As.items() if a_v.attr_of.get_T() == e ]
                    a = a[0] if len(a) else None
                    if a: tp = tp + '___' + a.type.replace('-','_') + ':' + a.val.replace('-','_')

                    label = tp if label == 'O' else label + '|' + tp
                    label = label if label not in label_overrides else label_overrides[label]
                fout.write(f'{txt} {ann.doc_id} {tok.idx} {tok.idx+len(txt)} {label}\n')

        # Events
        with open(os.path.join(output_dir, 'events', file), 'a+', encoding='utf-8') as fout:
            fout.write('\n')
            for tok, events in toks_with_events:
                if '\n' in tok.text:
                    fout.write('\n')
                    continue
                txt = tok.text.strip()
                if not any(txt):
                    continue

                label = 'O'
                for e in sorted(events, key=lambda x: x.type):
                    b_or_i = 'B-' if e.tok_idxs[0] == tok.i else 'I-'
                    tp = b_or_i + e.type.replace('-','_')
                    if e.type in ['Coreference']: 
                        continue

                    # Check for and add attribute
                    a = [ a_v for _, a_v in ann.As.items() if a_v.attr_of.get_T() == e ]
                    a = a[0] if len(a) else None
                    if a: tp = tp + '___' + a.type.replace('-','_') + ':' + a.val.replace('-','_')

                    label = tp if label == 'O' else label + '|' + tp
                    label = label if label not in label_overrides else label_overrides[label]
                fout.write(f'{txt} {ann.doc_id} {tok.idx} {tok.idx+len(txt)} {label}\n')
                

main()
