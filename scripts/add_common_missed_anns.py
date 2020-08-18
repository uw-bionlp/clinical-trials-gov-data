import os
import sys

dirs = [ 'nic', 'tony' ]

def cleanup(start_dir):
    global cnt 
    for d in os.listdir(start_dir):
        if os.path.isfile(d):
            continue
        for fl in os.listdir(os.path.join(start_dir, d)):
            if not fl.endswith('.ann'):
                continue
            pth = os.path.join(start_dir, d, fl)
            with open(pth, 'r') as f:
                content = f.read()
            lines = content.split('\n')
            lines_cp = lines[:]
            for ln in lines:
                          
                                
for d in dirs:
    cleanup(os.path.join('ner', d))   