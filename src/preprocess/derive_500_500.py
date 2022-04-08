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
    first_500_raw = {} 
    for d in Config.first_500:
        first_500_raw = {**first_500_raw, **utils.fetch_brat_files(d)}
    first_500 = [ BratDocument(k, v[0], v[1], v[2]) for k,v in first_500_raw.items() ]

    second_500_raw = {} 
    for d in Config.second_500:
        second_500_raw = {**second_500_raw, **utils.fetch_brat_files(d)}
    second_500 = [ BratDocument(k, v[0], v[1], v[2]) for k,v in second_500_raw.items() ]

    lct_500_500_path = os.path.join(conll_path, 'lct_500_500')
    lct_500_500_events_path   = os.path.join(lct_500_500_path, 'events')
    lct_500_500_entities_path = os.path.join(lct_500_500_path, 'entities')

    for p in [ lct_500_500_path, lct_500_500_path, lct_500_500_events_path, lct_500_500_entities_path ]:
        if not os.path.exists(p):
            os.mkdir(p)

    evt_labels =  brat_events_to_conll(os.path.join(lct_500_500_events_path, 'first_500.txt'), first_500, False, False)
    evt_labels += brat_events_to_conll(os.path.join(lct_500_500_events_path, 'second_500.txt'), second_500, False, False)
    with open(os.path.join(lct_500_500_events_path, 'labels.txt'), 'w+', encoding='utf-8') as fout:
        fout.write('\n'.join(sorted(list(set(evt_labels)))))

    ent_labels =  brat_entities_to_conll(os.path.join(lct_500_500_entities_path, 'first_500.txt'), first_500, False, False)
    ent_labels += brat_entities_to_conll(os.path.join(lct_500_500_entities_path, 'second_500.txt'), second_500, False, False)
    with open(os.path.join(lct_500_500_entities_path, 'labels.txt'), 'w+', encoding='utf-8') as fout:
        fout.write('\n'.join(sorted(list(set(ent_labels)))))

    
if __name__ == '__main__':
    main()