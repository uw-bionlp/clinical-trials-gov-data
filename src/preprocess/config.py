import os

class Config:
    home                  = os.getcwd()
    annotation_dir        = os.path.join(home, 'ner')
    annotation_train_dirs = [ 
        os.path.join(annotation_dir, 'nic', 'training'), 
        os.path.join(annotation_dir, 'nic', 'batch11'), 
        os.path.join(annotation_dir, 'nic', 'batch12'),
        os.path.join(annotation_dir, 'nic', 'batch13'),
        os.path.join(annotation_dir, 'nic', 'batch14'),
        os.path.join(annotation_dir, 'nic', 'batch15'),
        os.path.join(annotation_dir, 'nic', 'batch16'),
        os.path.join(annotation_dir, 'nic', 'batch17'),
        os.path.join(annotation_dir, 'nic', 'batch18'),
        os.path.join(annotation_dir, 'tony', 'batch1'),
    ]
    annotation_test_dirs  = [ os.path.join(annotation_dir, 'training') ]
    annotation_eval_dir   = os.path.join(annotation_dir, '.batch20')
    preprocess_dir        = os.path.join(home, 'data', 'ner')
        