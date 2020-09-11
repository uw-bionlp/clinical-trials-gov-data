import os
import sys
import json
import numpy as np
sys.path.append(os.path.join(os.getcwd(), 'src'))

from preprocess.brat_document import BratDocument
from preprocess.config import Config
import preprocess.utils as utils

def main():

    # Get data
    brat_train_raw = {} 
    for d in Config.annotation_train_dirs:
        brat_train_raw = {**brat_train_raw, **utils.fetch_brat_files(d)}
    annotations = [ BratDocument(k, v[0], v[1], v[2]) for k,v in brat_train_raw.items() ]
    r_bert = [ ann.to_r_bert_format(debug=False) for ann in annotations ]


    ## Split 
    #np.random.seed(1)
    #train, test, dev = np.split(dygiepp, [int(.8*len(dygiepp)), int(.9*len(dygiepp))])
    
if __name__ == '__main__':
    main()