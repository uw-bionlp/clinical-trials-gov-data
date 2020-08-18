import os
import sys

dirs = [ 'nic', 'tony' ]
cnt = 0

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
                if ln.startswith('T') and 'within' in ln.lower() and 'Eq-Operator' in ln:
                    parts = ln.strip().split('\t')
                    a = [ (i,l) for i,l in enumerate(lines) if l.startswith('A') and 'Eq-Operator-Value ' + parts[0] in l ]
                    if len(a):
                        i=a[0][0]
                        a=a[0][1]

                        if 'GTEQ' in a:
                        
                            # Write updated
                            cnt+= 1
                            #print 'File: ' + pth
                            #print '   Old: ' + lines_cp[i]
                            #print '   New: ' + a.replace("GTEQ","LTEQ")

                            to_repl = lines_cp[i]
                            if to_repl == a:
                                lines_cp[i] = a.replace('GTEQ','LTEQ')
                                with open(pth, 'w') as cp:
                                    cp.write('\n'.join(lines_cp))                 
                                
for d in dirs:
    cleanup(os.path.join('ner', d))                    
print(f'\nTotal: {cnt}')