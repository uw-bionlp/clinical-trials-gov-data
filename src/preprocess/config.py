import os

class Config:
    home                  = os.getcwd()
    annotation_dir        = os.path.join(home, 'ner')
    annotation_train_dirs = [ 
        os.path.join(annotation_dir, 'nic', 'training'), 
        os.path.join(annotation_dir, 'nic', 'batch1'),
        os.path.join(annotation_dir, 'nic', 'batch2'),
        os.path.join(annotation_dir, 'nic', 'batch3'), 
        os.path.join(annotation_dir, 'nic', 'batch4'), 
        os.path.join(annotation_dir, 'nic', 'batch5'), 
        os.path.join(annotation_dir, 'nic', 'batch6'), 
        os.path.join(annotation_dir, 'nic', 'batch7'), 
        os.path.join(annotation_dir, 'nic', 'batch8'), 
        os.path.join(annotation_dir, 'nic', 'batch9'), 
        os.path.join(annotation_dir, 'nic', 'batch10'), 
        os.path.join(annotation_dir, 'nic', 'batch11'), 
        os.path.join(annotation_dir, 'nic', 'batch12'),
        os.path.join(annotation_dir, 'nic', 'batch13'),
        os.path.join(annotation_dir, 'nic', 'batch14'),
        os.path.join(annotation_dir, 'nic', 'batch15'),
        os.path.join(annotation_dir, 'nic', 'batch16'),
        os.path.join(annotation_dir, 'nic', 'batch17'),
        os.path.join(annotation_dir, 'nic', 'batch18'),
        os.path.join(annotation_dir, 'nic', 'batch19'),
        os.path.join(annotation_dir, 'nic', 'batch20'),
    ]
    first_500 = [
        os.path.join(annotation_dir, 'nic', 'batch1'),
        os.path.join(annotation_dir, 'nic', 'batch2'),
        os.path.join(annotation_dir, 'nic', 'batch3'), 
        os.path.join(annotation_dir, 'nic', 'batch4'), 
        os.path.join(annotation_dir, 'nic', 'batch5'), 
        os.path.join(annotation_dir, 'nic', 'batch6'), 
        os.path.join(annotation_dir, 'nic', 'batch7'), 
        os.path.join(annotation_dir, 'nic', 'batch8'), 
        os.path.join(annotation_dir, 'nic', 'batch9'), 
        os.path.join(annotation_dir, 'nic', 'batch10')
    ]
    second_500 = [
        os.path.join(annotation_dir, 'nic', 'batch11'), 
        os.path.join(annotation_dir, 'nic', 'batch12'),
        os.path.join(annotation_dir, 'nic', 'batch13'),
        os.path.join(annotation_dir, 'nic', 'batch14'),
        os.path.join(annotation_dir, 'nic', 'batch15'),
        os.path.join(annotation_dir, 'nic', 'batch16'),
        os.path.join(annotation_dir, 'nic', 'batch17'),
        os.path.join(annotation_dir, 'nic', 'batch18'),
        os.path.join(annotation_dir, 'nic', 'batch19'),
        os.path.join(annotation_dir, 'nic', 'batch20')
    ]
    single_annotated = [ 
        os.path.join(annotation_dir, 'nic', 'batch3'), 
        os.path.join(annotation_dir, 'nic', 'batch4'), 
        os.path.join(annotation_dir, 'nic', 'batch5'), 
        os.path.join(annotation_dir, 'nic', 'batch6'), 
        os.path.join(annotation_dir, 'nic', 'batch7'), 
        os.path.join(annotation_dir, 'nic', 'batch8'), 
        os.path.join(annotation_dir, 'nic', 'batch9'), 
        os.path.join(annotation_dir, 'nic', 'batch10'), 
        os.path.join(annotation_dir, 'nic', 'batch11'), 
        os.path.join(annotation_dir, 'nic', 'batch12'),
        os.path.join(annotation_dir, 'nic', 'batch13'),
        os.path.join(annotation_dir, 'nic', 'batch14'),
        os.path.join(annotation_dir, 'nic', 'batch15'),
        os.path.join(annotation_dir, 'nic', 'batch16'),
        os.path.join(annotation_dir, 'nic', 'batch17'),
        os.path.join(annotation_dir, 'nic', 'batch18'),
        os.path.join(annotation_dir, 'nic', 'batch19'),
        os.path.join(annotation_dir, 'nic', 'batch20'),
    ]
    double_annotated = [
        os.path.join(annotation_dir, 'nic', 'training'),
        os.path.join(annotation_dir, 'nic', 'batch1'),
        os.path.join(annotation_dir, 'nic', 'batch2')
    ]
    annotation_test_dirs  = [ os.path.join(annotation_dir, 'training') ]
    annotation_eval_dir   = os.path.join(annotation_dir, 'tony', '.batch9')
    preprocess_dir        = os.path.join(home, 'data', 'ner')
        