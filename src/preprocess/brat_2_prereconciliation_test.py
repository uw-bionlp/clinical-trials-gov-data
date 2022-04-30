import os
import sys
import random
sys.path.append(os.path.join(os.getcwd(), 'src'))

from preprocess.brat_document import BratDocument
from preprocess.config import Config
from brat_to_conll import brat_events_to_conll, brat_entities_to_conll
import preprocess.utils as utils


def main():

    conll_path = os.path.join(Config.preprocess_dir, 'conll')
    if not os.path.exists(conll_path): 
        os.mkdir(conll_path)

    tony_raw = {} 
    for d in [ 'batch1', 'batch2', 'training' ]:
        tony_raw = {**tony_raw, **utils.fetch_brat_files(os.path.join('ner','archive','tony',d))}
    tony_prerecon = [ BratDocument(k, v[0], v[1], v[2]) for k,v in tony_raw.items() ]

    brat_train_raw = {} 
    for d in Config.annotation_train_dirs:
        brat_train_raw = {**brat_train_raw, **utils.fetch_brat_files(d)}
    annotations = [ BratDocument(k, v[0], v[1], v[2]) for k,v in brat_train_raw.items() if k not in tony_raw ]

    random.shuffle(annotations)
    annotations = annotations[:len(tony_prerecon)]

    lct_prerecon_path = os.path.join(conll_path, 'lct_prerecon')
    lct_prerecon_events_path   = os.path.join(lct_prerecon_path, 'events')
    lct_prerecon_entities_path = os.path.join(lct_prerecon_path, 'entities')

    for p in [ lct_prerecon_path, lct_prerecon_events_path, lct_prerecon_entities_path ]:
        if not os.path.exists(p):
            os.mkdir(p)

    evt_labels =  brat_events_to_conll(os.path.join(lct_prerecon_events_path, 'tony.txt'), tony_prerecon, False, False)
    evt_labels += brat_events_to_conll(os.path.join(lct_prerecon_events_path, 'nic.txt'), annotations, False, False)
    with open(os.path.join(lct_prerecon_events_path, 'labels.txt'), 'w+', encoding='utf-8') as fout:
        fout.write('\n'.join(sorted(list(set(evt_labels)))))

    ent_labels =  brat_entities_to_conll(os.path.join(lct_prerecon_entities_path, 'tony.txt'), tony_prerecon, False, False)
    ent_labels += brat_entities_to_conll(os.path.join(lct_prerecon_entities_path, 'nic.txt'), annotations, False, False)
    with open(os.path.join(lct_prerecon_entities_path, 'labels.txt'), 'w+', encoding='utf-8') as fout:
        fout.write('\n'.join(sorted(list(set(ent_labels)))))

    
if __name__ == '__main__':
    main()