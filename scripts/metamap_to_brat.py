import os
import sys
import re
import json
from shutil import copyfile

cwd = os.getcwd()
in_dir = f'{cwd}{os.path.sep}ner{os.path.sep}metamap'
out_dir = f'{cwd}{os.path.sep}ner{os.path.sep}auto'

# dsyn lbtr clnd topp aggp clna orgf
DX = 'dsyn'
DRUG = 'clnd'
TX = 'topp'
AGE = 'aggp'
VITAL = 'clna'
ORG_FUNC = 'orgf'
ORG_ATT = 'orga'
ORG_CHM = 'orch'
MENTAL = 'mobd'
PHARM = 'phsu'
LANG = 'lang'

regex_eq_operators   = r'(>=|<=|<|>|≥|≤|less than|greater than|up to|the past|within the past|within|younger than|and above)'
regex_ors            = r'( and/or | or/and | or |, )'
regex_between_nums   = r'[0-9]+\.?([0-9]+)?(-| to | and )[0-9]+\.?([0-9]+)?'
regex_temporal_units = r'(years|months|weeks|days|minutes)'
regex_units          = r'(kg ?/ ?m2|kg|kilograms|cm|percentile|lbs|mmHg|mmol/L|mmol/ l|mm3| mm)'
regex_nums           = r'( |>|<|≥|≤|-)[0-9]+\.?([0-9]+)?' 
regex_age            = r' (old|age|aged)( |\.|\n)'

class Annotation():
    def __init__(self, T, begin_idx, end_idx, val):
        self.T = T
        self.begin_idx = begin_idx
        self.end_idx = end_idx
        self.val = val

class ParsedObject():
    def __init__(self, start, end, idx, content):
        self.start = start
        self.end   = end
        self.idx   = idx
        self.text  = content[self.start:self.end]

def infer_equalities(data, annotations):
    content = data['text']
    Ts = sorted([ a for a in annotations if a.T.startswith('T') ], key=lambda x: x.begin_idx)
    As = sorted([ a for a in annotations if a.T.startswith('A') ], key=lambda x: x.begin_idx)
    Es = sorted([ a for a in annotations if a.T.startswith('E') ], key=lambda x: x.begin_idx)
    t_cnt = max([ int(t.T.replace('T',''))+1 for t in Ts ]) if len(Ts) > 0 else 1
    a_cnt = max([ int(a.T.replace('A',''))+1 for a in As ]) if len(As) > 0 else 1
    e_cnt = max([ int(e.T.replace('E',''))+1 for e in Es ]) if len(Es) > 0 else 1

    eq_ops         = [ ParsedObject(x.start(), x.end(), i, content) for i,x in enumerate(re.finditer(regex_eq_operators, content, re.IGNORECASE)) ]
    betw_nums      = [ ParsedObject(x.start(), x.end(), i, content) for i,x in enumerate(re.finditer(regex_between_nums, content, re.IGNORECASE)) ]
    temporal_units = [ ParsedObject(x.start(), x.end(), i, content) for i,x in enumerate(re.finditer(regex_temporal_units, content, re.IGNORECASE)) ]
    meas_units     = [ ParsedObject(x.start(), x.end(), i, content) for i,x in enumerate(re.finditer(regex_units, content, re.IGNORECASE)) ]
    nums           = [ ParsedObject(x.start(), x.end(), i, content) for i,x in enumerate(re.finditer(regex_nums, content, re.IGNORECASE)) ]
    ages           = [ ParsedObject(x.start(), x.end(), i, content) for i,x in enumerate(re.finditer(regex_age, content, re.IGNORECASE)) ]
    ors            = [ ParsedObject(x.start(), x.end(), i, content) for i,x in enumerate(re.finditer(regex_ors, content, re.IGNORECASE)) ]

    # Equality operators
    for op in eq_ops:
        T = f'T{t_cnt}'
        A = f'A{a_cnt}'
        val = None
        if op.text.lower() in [ '>=', '≥', 'the past', 'within the past', 'within', 'and above' ]:
            val = 'GTEQ'
        elif op.text.lower() in [ '<=', '≤', 'up to' ]:
            val = 'LTEQ'
        elif op.text.lower() in [ '<', 'less than', 'younger than' ]:
            val = 'LT'
        elif op.text.lower() in [ '>', 'greater than' ]:
            val = 'GT'
        if val:
            ann_ent = Annotation(T, op.start, op.end, f'{T}\tEq-Operator {op.start} {op.end}\t{op.text}')
            ann_a = Annotation(A, op.start, op.end, f'{A}\tEq-Operator-Value {T} {val}')
            annotations.append(ann_ent)
            annotations.append(ann_a)
            t_cnt += 1
            a_cnt += 1

    # Temporal units
    for op in temporal_units:
        T = f'T{t_cnt}'
        A = f'A{a_cnt}'
        val = None
        if op.text.lower() in [ 'years' ]:
            val = 'year'
        elif op.text.lower() in [ 'months' ]:
            val = 'month'
        elif op.text.lower() in [ 'weeks' ]:
            val = 'week'
        elif op.text.lower() in [ 'days' ]:
            val = 'day'
        elif op.text.lower() in [ 'minutes' ]:
            val = 'minute'
        if val:
            ann_ent = Annotation(T, op.start, op.end, f'{T}\tEq-Temporal-Unit {op.start} {op.end}\t{op.text}')
            ann_a = Annotation(A, op.start, op.end, f'{A}\tEq-Temporal-Unit-Value {T} {val}')
            annotations.append(ann_ent)
            annotations.append(ann_a)
            t_cnt += 1
            a_cnt += 1

    # Measurement units
    for op in meas_units:
        T = f'T{t_cnt}'
        A = f'A{a_cnt}'
        if op.text == ' mm':
            op.text = 'mm'
            op.start += 1
        ann_ent = Annotation(T, op.start, op.end, f'{T}\tEq-Unit {op.start} {op.end}\t{op.text}')
        annotations.append(ann_ent)
        t_cnt += 1
            
    # Ages
    for op in ages:
        T = f'T{t_cnt}'
        E = f'E{e_cnt}'
        op.start += 1
        op.end -= 1
        op.text = op.text[1:-1]
        ann_ent = Annotation(T, op.start, op.end, f'{T}\tAge {op.start} {op.end}\t{op.text}')
        ann_e = Annotation(E, op.start, op.end, f'{E}\tAge:{T}')
        annotations.append(ann_ent)
        annotations.append(ann_e)
        t_cnt += 1
        e_cnt += 1
    
    # Between
    for vals in betw_nums:
        splitter = '-' if '-' in vals.text else 'to'
        numbers = vals.text.split(splitter)
        if len(numbers) != 2:
            continue
        T = f'T{t_cnt}'
        A = f'A{a_cnt}'
        start = vals.text.find(splitter) + vals.start
        end = start + len(splitter)
        ann = Annotation(T, start, end, f'{T}\tEq-Operator {start} {end}\t{splitter}')
        ann_a = Annotation(A, start, end, f'{A}\tEq-Operator-Value {T} BETWEEN')
        annotations.append(ann)
        annotations.append(ann_a)
        t_cnt += 1
        a_cnt += 1
    
    # Numbers
    for num in nums:
        digits = re.findall(r'\d+', num.text)[0]
        T = f'T{t_cnt}'
        start = num.text.find(digits) + num.start
        end = start + len(digits)
        if start > 0 and content[start-1] == ' ' and end+2 < len(content) and content[end] == '.' and content[end+1] == ' ':
            continue
        ann = Annotation(T, start, end, f'{T}\tEq-Value {start} {end}\t{digits}')
        annotations.append(ann)
        t_cnt += 1
        
    # Equality Comparison Events
    ops   = [ a for a in annotations if 'Eq-Operator' in a.val and a.T.startswith('T') ]
    vals  = [ a for a in annotations if 'Eq-Value' in a.val and a.T.startswith('T') ]
    units = [ a for a in annotations if ('Eq-Temporal-Unit' in a.val or 'Eq-Unit' in a.val) and a.T.startswith('T') ]
    for op in ops:
        vs, us = None, None
        T = f'T{t_cnt}'
        E = f'E{e_cnt}'
        vs = [ a for a in vals if a.begin_idx in [ op.end_idx+1, op.end_idx ] or a.end_idx in [ op.begin_idx-1, op.begin_idx ] ]
        if any(vs):
            v = vs[0]
            us = [ a for a in units if a.begin_idx == v.end_idx+1 ]
            start = min([ op.begin_idx, v.begin_idx ])
            if any(us):
                u = us[0]
                end = u.end_idx
                ann_ent = Annotation(T, start, end, f'{T}\tEq-Comparison {start} {end}\t{content[start:end]}')
                ann_e = Annotation(E, start, end, f'{E}\tEq-Comparison:{T} Operator:{op.T} {"Unit" if "Eq-Unit" in u.val else "Temporal-Unit"}:{u.T} Value:{v.T}')
            else:
                end = max([ op.end_idx, v.end_idx ])
                ann_ent = Annotation(T, start, end, f'{T}\tEq-Comparison {start} {end}\t{content[start:end]}')
                ann_e = Annotation(E, start, end, f'{E}\tEq-Comparison:{T} Operator:{op.T} Value:{v.T}')
            annotations.append(ann_ent)
            annotations.append(ann_e)
            t_cnt += 1
            e_cnt += 1

    # Ors
    #for o in ors:
    #    prec = [ a for a in annotations if a.end_idx in [ o.start, o.start+1 ] and a.T.startswith('E') ]
    #    foll = [ a for a in annotations if a.begin_idx in [ o.end, o.end+1 ] and a.T.startswith('E') ]
    #    if any(prec) and any(foll):
    #        T = f'T{t_cnt}'
    #        E = f'E{e_cnt}'
    #        prec = prec[0]
    #        foll = foll[0]
    #        if o.text.startswith(' '): o.start += 1
    #        if o.text.endswith(' '): o.end -= 1
    #        t_ann = Annotation(T, o.start, o.end, f'{T}\tOr {o.start} {o.end}\t{content[o.start:o.end]}')
    #        e_ann = Annotation(E, o.start, o.end, f'{E}\tOr:{T} Arg:{prec.T} Arg2:{foll.T}')
    #        annotations.append(t_ann)
    #        annotations.append(e_ann)
    #        t_cnt += 1
    #        e_cnt += 1

    return annotations

def json_to_brat(data):
    annotations = []
    cnt = 1
    a_cnt = 1
    content = data['text']
    for sentence in data['sentences']:
        for c in sorted([ c for c in sentence['metamap']], key=lambda x: x['endDocumentCharIndex']-x['beginDocumentCharIndex'], reverse=True ):
            T_ent = f'T{cnt}'
            T_ev  = f'T{cnt+1}'
            E     = f'E{cnt}'
            A     = f'A{a_cnt}'
            beg_idx = c['beginDocumentCharIndex']
            end_idx = c['endDocumentCharIndex']
            sem_type = '|'.join(c['semanticTypes'])
            concept_name = c['conceptName']

            while content[beg_idx:end_idx] != c['sourcePhrase'] and end_idx <= len(content):
                beg_idx += 1
                end_idx += 1
            txt = content[beg_idx:end_idx]

            if txt != c['sourcePhrase']:
                continue

            if ',' in txt or '\n' in txt:
                continue
            if any([ a for a in annotations if beg_idx >= a.begin_idx and beg_idx <= a.end_idx or \
                                               end_idx <= a.end_idx and end_idx >= a.begin_idx ]):
                continue
            if txt.lower() in [ 'drainage', 'operation', 'surgery', 'elective surgery', 'psychiatric', 'treatment', \
                                'interventional', 'primary', 'coagulation', 'exercise', 'elevation', 'disorders', \
                                'condition', 'infection', 'infections', 'treatments', 'administration', 'drugs', \
                                'disease', 'diseases', 'for', 'placebo', 'new' ]:
                continue

            # Diagnosis and Organism function (eg, pregnancy)
            if DX in sem_type or ORG_FUNC in sem_type or MENTAL in sem_type:
                ann_ent = Annotation(T_ent, beg_idx, end_idx, f'{T_ent}\tCondition {beg_idx} {end_idx}\t{txt}')
                ann_ev  = Annotation(T_ev, beg_idx, end_idx, f'{T_ev}\tCondition-Name {beg_idx} {end_idx}\t{txt}')
                ann_e   = Annotation(E, beg_idx, end_idx, f'{E}\tCondition:{T_ent} Name:{T_ev}')
                annotations.append(ann_ent)
                annotations.append(ann_ev)
                annotations.append(ann_e)
                cnt += 2

            # Drug
            if DRUG in sem_type or ORG_CHM in sem_type or PHARM in sem_type:
                ann_ent = Annotation(T_ent, beg_idx, end_idx, f'{T_ent}\tMedication {beg_idx} {end_idx}\t{txt}')
                ann_ev  = Annotation(T_ev, beg_idx, end_idx, f'{T_ev}\tMedication-Name {beg_idx} {end_idx}\t{txt}')
                ann_e   = Annotation(E, beg_idx, end_idx, f'{E}\tMedication:{T_ent} Name:{T_ev}')
                annotations.append(ann_ent)
                annotations.append(ann_ev)
                annotations.append(ann_e)
                cnt += 2

            # Treatment/Procedure
            if TX in sem_type:
                ann_ent = Annotation(T_ent, beg_idx, end_idx, f'{T_ent}\tProcedure {beg_idx} {end_idx}\t{txt}')
                ann_ev  = Annotation(T_ev, beg_idx, end_idx, f'{T_ev}\tProcedure-Name {beg_idx} {end_idx}\t{txt}')
                ann_e   = Annotation(E, beg_idx, end_idx, f'{E}\tProcedure:{T_ent} Name:{T_ev}')
                annotations.append(ann_ent)
                annotations.append(ann_ev)
                annotations.append(ann_e)
                cnt += 2

            # Age & Gender
            if AGE in sem_type or ORG_ATT in sem_type:
                if not any([ a for a in [ 'child', 'adult', 'boy', 'girl', 'man', 'men', 'male', 'woman', 'women', 'female' ] if a in txt.lower() ]):
                    continue
                ann_ent = Annotation(T_ent, beg_idx, end_idx, f'{T_ent}\tLife-Stage-And-Gender {beg_idx} {end_idx}\t{txt}')
                annotations.append(ann_ent)
                cnt += 1
                if 'child' in txt.lower():
                    ann_a = Annotation(A, beg_idx, end_idx, f'{A}\tLife-Stage-And-Gender-Type {T_ent} child')
                    annotations.append(ann_a)
                    a_cnt += 1
                elif 'adult' in txt.lower():
                    ann_a = Annotation(A, beg_idx, end_idx, f'{A}\tLife-Stage-And-Gender-Type {T_ent} adult')
                    annotations.append(ann_a)
                    a_cnt += 1
                elif 'boy' in txt.lower():
                    ann_a = Annotation(A, beg_idx, end_idx, f'{A}\tLife-Stage-And-Gender-Type {T_ent} boy')
                    annotations.append(ann_a)
                    a_cnt += 1
                elif 'girl' in txt.lower():
                    ann_a = Annotation(A, beg_idx, end_idx, f'{A}\tLife-Stage-And-Gender-Type {T_ent} boy')
                    annotations.append(ann_a)
                    a_cnt += 1
                elif 'man' in txt.lower() or 'men' in txt.lower() or 'male' in txt.lower():
                    ann_a = Annotation(A, beg_idx, end_idx, f'{A}\tLife-Stage-And-Gender-Type {T_ent} male')
                    annotations.append(ann_a)
                    a_cnt += 1
                elif 'woman' in txt.lower() or 'women' in txt.lower() or 'female' in txt.lower():
                    ann_a = Annotation(A, beg_idx, end_idx, f'{A}\tLife-Stage-And-Gender-Type {T_ent} female')
                    annotations.append(ann_a)
                    a_cnt += 1

            # Vitals
            if VITAL in sem_type or ORG_ATT in sem_type:
                if not concept_name.lower() in [ 'body mass index', 'body height', 'body weight' ]:
                    continue
                ann_ent = Annotation(T_ent, beg_idx, end_idx, f'{T_ent}\tObservation {beg_idx} {end_idx}\t{txt}')
                ann_ev  = Annotation(T_ev, beg_idx, end_idx, f'{T_ev}\tObservation-Name {beg_idx} {end_idx}\t{txt}')
                ann_e   = Annotation(E, beg_idx, end_idx, f'{E}\tObservation:{T_ent} Name:{T_ev}')
                ann_a   = Annotation(A, beg_idx, end_idx, f'{A}\tObservation-Type-Value {T_ev} vital')
                annotations.append(ann_ent)
                annotations.append(ann_ev)
                annotations.append(ann_e)
                annotations.append(ann_a)
                a_cnt += 1
                cnt += 2

            # Language
            if LANG in sem_type:
                ann_ent = Annotation(T_ent, beg_idx, end_idx, f'{T_ent}\tLanguage {beg_idx} {end_idx}\t{txt}')
                annotations.append(ann_ent)
                cnt += 1
                    

    return annotations

def main():
    for batch_dir in os.listdir(in_dir):
        batch_path = f'{in_dir}{os.path.sep}{batch_dir}'
        for f in os.listdir(batch_path):
            if f.endswith('.ann'):
                continue
            batch_out_dir = f'{out_dir}{os.path.sep}{batch_dir}'
            f_path = f'{batch_path}{os.path.sep}{f}'
            f_out_path = f'{batch_out_dir}{os.path.sep}{f}'.replace('.json','.txt')
            a_out_path = f_out_path.replace(".txt",".ann")
            if not os.path.exists(batch_out_dir):
                os.makedirs(batch_out_dir)

            with open(f_path) as f:
                data = json.loads(f.read())
            brat_rows = json_to_brat(data)
            brat_rows = infer_equalities(data, brat_rows)
            with open(f_out_path, 'w+') as f:
                f.write(data['text'])
            with open(a_out_path, 'w+') as f:
                for row in brat_rows:
                    f.write(f'{row.val}\n')

main()