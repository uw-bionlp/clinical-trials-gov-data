import os
import sys
sys.path.append(os.path.join(os.getcwd(), 'src'))

from preprocess.brat_document import BratDocument
from preprocess.config import Config
from brat_to_conll import brat_events_to_conll, brat_entities_to_conll
import preprocess.utils as utils


def main():

    conll_path = os.path.join(Config.preprocess_dir, 'conll')
    if not os.path.exists(conll_path): 
        os.mkdir(conll_path)

    # Get data
    single_raw = {} 
    for d in Config.single_annotated:
        single_raw = {**single_raw, **utils.fetch_brat_files(d)}
    single = [ BratDocument(k, v[0], v[1], v[2]) for k,v in single_raw.items() ]

    double_raw = {} 
    for d in Config.double_annotated:
        double_raw = {**double_raw, **utils.fetch_brat_files(d)}
    double = [ BratDocument(k, v[0], v[1], v[2]) for k,v in double_raw.items() ]

    lct_single_double_path = os.path.join(conll_path, 'lct_single_double')
    lct_single_double_events_path   = os.path.join(lct_single_double_path, 'events')
    lct_single_double_entities_path = os.path.join(lct_single_double_path, 'entities')

    for p in [ lct_single_double_path, lct_single_double_path, lct_single_double_events_path, lct_single_double_entities_path ]:
        if not os.path.exists(p):
            os.mkdir(p)

    evt_labels =  brat_events_to_conll(os.path.join(lct_single_double_events_path, 'single.txt'), single, False, False)
    evt_labels += brat_events_to_conll(os.path.join(lct_single_double_events_path, 'double.txt'), double, False, False)
    with open(os.path.join(lct_single_double_events_path, 'labels.txt'), 'w+', encoding='utf-8') as fout:
        fout.write('\n'.join(sorted(list(set(evt_labels)))))

    ent_labels =  brat_entities_to_conll(os.path.join(lct_single_double_entities_path, 'single.txt'), single, False, False)
    ent_labels += brat_entities_to_conll(os.path.join(lct_single_double_entities_path, 'double.txt'), double, False, False)
    with open(os.path.join(lct_single_double_entities_path, 'labels.txt'), 'w+', encoding='utf-8') as fout:
        fout.write('\n'.join(sorted(list(set(ent_labels)))))

    
if __name__ == '__main__':
    main()