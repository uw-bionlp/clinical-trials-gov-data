import os


def read_file(path):
    with open(path, 'r') as f: 
        return f.read()

def fetch_brat_files(path):
    files = [ fl for fl in os.listdir(path) ]
    txts = { fl.replace('.txt',''): read_file(os.path.join(path, fl)) for fl in files if fl.endswith('.txt') }
    anns = { fl.replace('.ann',''): read_file(os.path.join(path, fl)) for fl in files if fl.endswith('.ann') }

    # Check all texts have corresponding annotations, and vice versa
    for k, v in txts.items(): assert k in anns, f'Text file {k} does not have an associated Annotation file!'
    for k, v in anns.items(): assert k in txts, f'Annotation file {k} does not have an associated Text file!'
    return { fl: (txt, anns[fl], path) for fl, txt in txts.items() }
    