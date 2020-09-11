import os
import sys
import json
import numpy as np
sys.path.append(os.path.join(os.getcwd(), 'src'))

from preprocess.brat_document import BratDocument
from preprocess.config import Config
import preprocess.utils as utils


def write_jsonl(objs, file_path):
    with open(file_path, 'w+') as f: f.write('')
    with open(file_path, 'a+') as f:
        for obj in objs: 
            f.write(json.dumps(obj) + '\n')

def get_label_counts(dygiepp):
    flattened = []
    for d in dygiepp:
        for ev in d['events']:
            for inst in ev:
                flattened.append(inst)
    
    trigger_labels = set([ f[0][1] for f in flattened ])
    ner_labels = [] 
    for x in [ f[1:] for f in flattened if len(f) > 1 ]:
        for y in x:
            ner_labels.append(y[2])
    ner_labels = set(ner_labels)

    return trigger_labels, ner_labels

def main():

    # Get data
    brat_train_raw = {} 
    for d in Config.annotation_train_dirs:
        brat_train_raw = {**brat_train_raw, **utils.fetch_brat_files(d)}
    annotations = [ BratDocument(k, v[0], v[1], v[2]) for k,v in brat_train_raw.items() ]
    #dygiepp = [ ann.to_dygiepp_format() for ann in annotations ]
    dygiepp = [ ann.to_dygiepp_format2(debug=False) for ann in annotations ]

    ## Split 
    np.random.seed(1)
    train, test, dev = np.split(dygiepp, [int(.8*len(dygiepp)), int(.9*len(dygiepp))])
    # dev, train, test = np.split(dygiepp, [ 0, int(.8*len(dygiepp))])

    ## Save
    ner_path = os.path.join(Config.preprocess_dir, 'json')
    if not os.path.exists(ner_path): os.mkdir(ner_path)
    write_jsonl(train, os.path.join(ner_path, 'train.json'))
    write_jsonl(dev, os.path.join(ner_path, 'dev.json'))
    write_jsonl(test, os.path.join(ner_path, 'test.json'))

    # Get eval data
    brat_eval_raw = [ BratDocument(k, v[0], v[1], "") for k,v in utils.fetch_brat_files(Config.annotation_eval_dir).items() ]
    dygiepp = [ ann.to_dygiepp_format() for ann in brat_eval_raw ]
    for d in dygiepp:
        del d['ner']
        del d['clusters']
        del d['relations']
        del d['events']
    write_jsonl(dygiepp, os.path.join(ner_path, 'eval.json'))

if __name__ == '__main__':
    main()