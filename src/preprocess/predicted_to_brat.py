import os
import sys
import json
sys.path.append(os.path.join(os.getcwd(), 'src'))

from preprocess.brat_document import BratDocument, BratE, BratEArgPair, BratR, BratT
from preprocess.config import Config
import preprocess.utils as utils

def main():
    filename = 'NCT02504489_predicted'
    e_types = get_E_types()
    with open(f'./{filename}.json', 'r') as fin:
        data = json.loads(fin.read())
    for inc_exc in ['inclusion', 'exclusion']:
        text, Ts, As, Rs, Es = to_brat(data[inc_exc], e_types)
        
        with open(f'{filename}_{inc_exc}.txt', 'w+') as fout:
            fout.write(text)
        with open(f'{filename}_{inc_exc}.ann', 'w+') as fout:
            for key, T in Ts.items():
                fout.write(f'{key}\t{T["label"]} {T["charBeginIndex"]} {T["charEndIndex"]}\t{T["text"]}\n')
            for key, A in As.items():
                id = A["pointer"]["E_id"] if "E_id" in A['pointer'] else A["pointer"]["id"]
                fout.write(f'{key}\t{A["label"]} {id} {A["value"]}\n')
            for key, R in Rs.items():
                fout.write(f'{key}\t{R["label"]} Arg1:{R["arg1"]["pointer"]["id"]} Arg2:{R["arg2"]["pointer"]["id"]}\n')
            for key, E in Es.items():
                fout.write(f'{key}\t{E["label"]}:{E["id"]}')
                for arg in E['args']:
                    id = arg["arg"]["E_id"] if "E_id" in arg['arg'] else arg["arg"]["id"]
                    fout.write(f' {arg["label"]}:{id}')
                fout.write('\n')

def to_brat(predicted, e_types):
    text      = predicted['text']
    entities  = predicted['namedEntities']
    relations = predicted['relations']
    Ts, As, Rs, Es = {}, {}, {}, {}

    for entity in entities:
        label = entity['label']

        if entity['text'] == 'PD - 1 PD - L 1 inhibitor':
            entity['text'] = 'PD - 1 / PD - L 1 inhibitor'

        #realign_tries = 0
        #while source_text != entity['text']:
        #    entity['charBeginIndex'] -= 1
        #    entity['charEndIndex'] = entity['charBeginIndex'] + len(entity['text'])
        #    source_text = text[entity['charBeginIndex']:entity['charEndIndex']]
        #    realign_tries +=1 
        #    if realign_tries == 10:
        #        x=1

        if entity['text'] == '4 .03': 
            entity['text'] = '4.03'
            #entity['charEndIndex'] -= 1
        if entity['text'] == '≥ 1 .5 x 109 / L':
            entity['text'] = '≥ 1.5 x 109 / L'
            #entity['charEndIndex'] -= 1
        if entity['text'] == "Gilbert 's disease":
            entity['text'] = "Gilbert's disease"
            #entity['charEndIndex'] -= 1
        if entity['text'] == '≤ 3 .0 times ULN':
            entity['text'] = '≤ 3.0 times ULN'
            #entity['charEndIndex'] -= 1
        if entity['text'] == '≤ 2 .5 x ULN':
            entity['text'] = '≤ 2.5 x ULN'
            #entity['charEndIndex'] -= 1
        if entity['text'] == '≤ 1 .5 x ULN':
            entity['text'] = '≤ 1.5 x ULN'
            #entity['charEndIndex'] -= 1
        if entity['text'] == '1 .5':
            entity['text'] = '1.5'
            #entity['charEndIndex'] -= 1
        if entity['text'] == '> 2 .5 x ULN':
            entity['text'] = '> 2.5 x ULN'
            #entity['charEndIndex'] -= 1

        source_text = text[entity['charBeginIndex']:entity['charEndIndex']]
        if source_text != entity['text']:
            print('problem!!')

        if entity['text'].startswith('\n'):
            entity['text'] = entity['text'][1:]
            entity['charBeginIndex'] += 1

        if '---' in label:
            a = label.split('---')[1]
            a_label = a.split(':')[0]
            a_value = a.split(':')[1]
            a_id = f'A{len(As)+1}'
            a = { 'id': a_id, 'label': a_label, 'value': a_value }
            As[a_id] = a
            label = label.split('---')[0]
        else:
            a = None
        id = f'T{len(Ts)+1}'
        Ts[id] = entity
        entity['pointer'] = Ts[id]
        entity['id'] = id
        entity['label'] = label
        if label in e_types:
            id = f'E{len(Es)+1}'
            Es[id] = entity
            Es[id]['E_id'] = id
            Es[id]['args'] = []
            entity['pointer'] = Es[id]
        if a:
            As[a_id]['pointer'] = entity['pointer']

    for relation in relations:
        if relation['label'].startswith('Relation'):
            id = f'R{len(Rs)+1}'
            relation['arg1'] = entities[relation['subjectIndex']]['pointer']
            relation['arg2'] = entities[relation['objectIndex']]['pointer']
            relation['label'] = relation['label'].replace('Relation:','')
            Rs[id] = relation
        else:
            relation['E'] = entities[relation['subjectIndex']]['pointer']
            relation['arg'] = entities[relation['objectIndex']]['pointer']
            relation['label'] = relation['label'].replace('Argument:','')
            relation['E']['args'].append(relation)

    #for entity in entities:
    #    for relation in entity['relations']:
    #        relation['label'] = relation['label'].split(' ')[0]
    #        if relation['label'].startswith('Relation'):
    #            id = f'R{len(Rs)+1}'
    #            relation['arg1'] = entities[relation['subjectIndex']]['pointer']
    #            relation['arg2'] = entities[relation['objectIndex']]['pointer']
    #            relation['label'] = clean_label(relation['label'].replace('Relation:',''))
    #            if any([ r for r in relations if r['subjectIndex'] == relation['subjectIndex'] and r['objectIndex'] == relation['objectIndex']]):
    #                continue
    #            if len(relation['label'].split('-')) > 1:
    #                relation['label'] = relation['label'].split('-')[1]
    #            Rs[id] = relation
    #        else:
    #            relation['E'] = entities[relation['subjectIndex']]['pointer']
    #            relation['arg'] = entities[relation['objectIndex']]['pointer']
    #            relation['label'] = clean_label(relation['label'].replace('Argument:',''))
    #            if any([ r for r in relations if r['subjectIndex'] == relation['subjectIndex'] and r['objectIndex'] == relation['objectIndex']]):
    #                continue
    #            if len(relation['label'].split('-')) > 1:
    #                relation['label'] = relation['label'].split('-')[1]
    #            relation['E']['args'].append(relation)

    return text, Ts, As, Rs, Es

def clean_label(label):
    output = ''
    uppercased = False
    prev = ''
    prev_uppercased = False
    for i, ch in enumerate(label):
        uppercased = ch >= 'A' and ch <= 'Z'
        if uppercased and not prev_uppercased and i > 0 and prev != '-':
            output += '-'
        output += ch
        prev = ch
        prev_uppercased = uppercased

    return output

def get_E_types():
    brat_train_raw = {} 
    for d in Config.annotation_train_dirs:
        brat_train_raw = {**brat_train_raw, **utils.fetch_brat_files(d)}
        #break
    annotations = [ BratDocument(k, v[0], v[1], v[2], surface_only=True) for k,v in brat_train_raw.items() ]
    Es = []
    for ann in annotations:
        Es.extend([ e.get_T().type for _, e in ann.Es.items() ])

    return set(Es)

main()    