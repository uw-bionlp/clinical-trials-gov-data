import os
import re
import sys
sys.path.append(os.path.join(os.getcwd(), 'src'))

from preprocess.brat_document import BratDocument, BratA, BratT, BratEArgPair
from preprocess.config import Config
import preprocess.utils as utils


regex_asa = r'(American.*Anes.*)'
regex_nyha = r'(NYHA|New York Heart Assoc.*)'
regex_ecog = r'(ECOG|Eastern Cooperative Oncology Group)'
regex_chronic = r'(chronic|long[ |-]term)'
regex_trailing_num = r'\d'


def to_brat(ann):
    text, anns = ann.to_brat()
    with open(os.path.join(ann.path, ann.doc_id+'.txt'), 'w+') as fout:
        fout.write(text)
    with open(os.path.join(ann.path, ann.doc_id+'.ann'), 'w+') as fout:
        fout.write(anns)

def condition_and_observation(annotations):
    ''' Check that annotations are not both Conditions and Observations '''
    for ann in annotations:
        matched  = [ v for _,v in ann.Es.items() if v.args[0].type == 'Condition' ]
        for rec in matched:
            r = rec.args[0].val
            obs  = [ v for _,v in ann.Es.items() if v.args[0].type == 'Observation' and r.char_beg_idx == v.args[0].val.char_beg_idx and r.char_end_idx == v.args[0].val.char_end_idx ]
            if len(obs):
                print('Annotation should not be both a Condition and Observation!')

def diabetes(annotations):
    ''' Check that diabetes types are modifiers '''
    for ann in annotations:
        matched  = [ v for _,v in ann.Ts.items() if v.type == 'Condition' and 'type' in v.span.lower() and 'diabet' in v.span.lower() ]
        for rec in matched:
            print('diabetes type!')

def unstable(annotations):
    ''' Check that is not a modifier '''
    for ann in annotations:
        matched  = [ v for _,v in ann.Ts.items() if v.type == 'Modifier' and 'unstable' in v.span.lower() ]
        for rec in matched:
            print('unstable should not be a modifier!')

def female_male(annotations):
    ''' Check that female and male have correct labels '''
    for ann in annotations:
        matched  = [ v for _,v in ann.Ts.items() if v.type == 'Life-Stage-And-Gender' and any([ x for x in ['female','male','men','women'] if x in v.span.lower() ]) ]
        for rec in matched:
            a_s = [ v for _,v in ann.As.items() if v.attr_of == rec ]
            for a in a_s:
                if ('female' in rec.span.lower() or 'women' in rec.span.lower()) and a.val != 'female':
                    print('Female but not annotated correctly!')
                if ('male' == rec.span.lower() or 'men' == rec.span.lower()) and a.val != 'male':
                    print('Male but not annotated correctly!')

def pos_neg(annotations):
    ''' Check that positive and negative have correct labels '''
    for ann in annotations:
        matched  = [ v for _,v in ann.Ts.items() if v.type == 'Polarity' and any([ x for x in ['positive','negative','+','-'] if x in v.span.lower() ]) ]
        for rec in matched:
            a_s = [ v for _,v in ann.As.items() if v.attr_of == rec ]
            for a in a_s:
                if ('positive' in rec.span.lower() or '+' in rec.span.lower()) and a.val != 'positive':
                    print('Positive but not annotated correctly!')
                if ('negative' == rec.span.lower() or '-' == rec.span.lower()) and a.val != 'negative':
                    print('Negative but not annotated correctly!')
                if '(' in rec.span or ')' in rec.span:
                    print('Parens in Pos/Neg!')

def eq_value_unit(annotations):
    ''' Check that Eq-Value and Eq-Units are inside Eq-Comparisons '''
    for ann in annotations:
        matched  = [ v for _,v in ann.Ts.items() if v.type in [ 'Eq-Value', 'Eq-Unit', 'Eq-Temporal-Unit' ] ]
        for rec in matched:
            trigger = [ v for _,v in ann.Es.items() if any([ arg for arg in v.args if arg.val == rec ]) ]
            if not len(trigger):
                print(f'{ann.path}/{ann.doc_id} has no parent Eq-Comparison!')
                continue
            trigger = trigger[0]
            trigger_t = trigger.args[0].val
            if rec.span not in [ 'Eq-Unit', 'Eq-Temporal-Unit'] and not (rec.char_beg_idx >= trigger_t.char_beg_idx and rec.char_end_idx <= trigger_t.char_end_idx):
                print(f'{ann.path}/{ann.doc_id} is outside parent Eq-Comparison!')

def modifiers(annotations):
    ''' Modifiers that should be part of Condition '''
    cnt = 0
    for ann in annotations:
        matched  = [ e for _,e in ann.Es.items() if e.args[0].type == 'Modifier' ]
        conds = {}
        for m in matched:
            try:
                modified = m.args[1].val.get_T()
                if modified in conds:
                    conds[modified].append(m.args[0].get_T())
                else:
                    conds[modified] = [m.args[0].get_T()]
            except:
                pass
        candidates = [(x,m[0]) for x,m in conds.items() if x.type.startswith('Condition') and len(m) == 1]
        candidates = [(x,m) for x,m in candidates if m.char_end_idx +1 == x.char_beg_idx]
        for cond, mod in candidates:
            path = ann.path.split('/')[-1]
            cnt += 1
            cond_name = [l for l in ann.raw_anns.split('\n') if f'\tCondition-Name {cond.char_beg_idx} {cond.char_end_idx}\t{cond.span}' in l][0]
            new_raw = [l for l in ann.raw_anns.split('\n') if \
                not l.startswith(f'{mod.id}\t') and \
                not f':{mod.id} ' in l and \
                not f' {cond.char_beg_idx} {cond.char_end_idx}\t' in l]
            new_cond = f'{cond.id}\tCondition {mod.char_beg_idx} {cond.char_end_idx}\t{cond.span}'
            new_cond_name = f'{cond_name.split()[0]}\tCondition-Name {mod.char_beg_idx} {cond.char_end_idx}\t{cond.span}'
            new_raw += [new_cond, new_cond_name]

            with open(os.path.join(ann.path, f'{ann.doc_id}.ann'), 'w+') as fout:
                fout.write('\n'.join(new_raw))

            #print(f'{path}/{ann.doc_id} unnecessary Modifier! "{mod.span}" "{cond.span}"')
    print(f'Total unnecessary Modifiers: {cnt}')
    

def chronic(annotations):
    ''' Convert 'Chronic' Modifier -> Acuteness[chronic] '''
    for ann in annotations:
        matched  = [ v for _,v in ann.Ts.items() if re.match(regex_chronic, v.span, re.IGNORECASE) and v.type == 'Modifier' ]
        if len(matched):
            max_a = max([ int(a.id.replace('A','')) for _,a in ann.As.items() ])+1 if len(ann.As) else 1
            for rec in matched:
                if 'chronic' in rec.span.lower() and rec.span.lower() != 'chronic':
                    print(f'{ann.path}/{ann.doc_id} has Chronic as only part of span!')
                    continue
                rec.type = 'Acuteness'
                a_id = f'A{max_a}'
                a = BratA('Acuteness-Type-Value', rec, 'chronic', a_id, -1)
                ann.As[a_id] = a
                max_a += 1
                ann.Ts[rec.id] = rec
                es = [ v for _,v in ann.Es.items() if v.args[0].val == rec ] # Old entity
                for e in es:
                    try:
                        conditions = [ arg for arg in e.args if arg.type.startswith('Modifies') ]
                        for condition in conditions:
                            cond = condition.val
                            if isinstance(cond, BratT):
                                cond = [ v for _,v in ann.Es.items() if any([ arg for arg in v.args if arg.val == cond and arg.type == 'Name' ]) ][0]
                            new_arg = BratEArgPair('Acuteness', rec)
                            cond.args.append(new_arg)
                            ann.Es[cond.id] = cond
                            other_es = [ v for _,v in ann.Es.items() if any([ arg for arg in v.args if arg.val == e ]) ]
                            for e2 in other_es:
                                for arg in e2.args[1:]:
                                    if arg.val == e:
                                        arg.val = rec
                                ann.Es[e2.id] = e2
                            rels = [ v for _,v in ann.Rs.items() if v.arg1 == e or v.arg2 == e ]
                            for rel in rels:
                                if rel.arg1 == e:
                                    rel.arg1 = rec
                                if rel.arg2 == e:
                                    rel.arg2 = rec
                                ann.Rs[rel.id] = rel
                    except Exception as ex:
                        print(f'{ann.path}/{ann.doc_id} has a malformed Modifer!')

                    del ann.Es[e.id]
    return annotations

def acute(annotations):
    ''' Convert 'Acute' Severity -> Acuteness[acute] '''
    for ann in annotations:
        matched  = [ v for _,v in ann.Ts.items() if v.span.lower() == 'acute' and v.type == 'Severity' ]
        if len(matched):
            max_a = max([ int(a.id.replace('A','')) for _,a in ann.As.items() ])+1 if len(ann.As) else 1
            for rec in matched:
                rec.type = 'Acuteness'
                a_id = f'A{max_a}'
                prev_a = [ v for _,v in ann.As.items() if v.attr_of == rec and v.type == 'Severity-Value' ]
                if len(prev_a):
                    del ann.As[prev_a[0].id]
                a = BratA('Acuteness-Type-Value', rec, 'acute', a_id, -1)
                ann.As[a_id] = a
                max_a += 1
                ann.Ts[rec.id] = rec
                es = [ v for _,v in ann.Es.items() if any([ arg for arg in v.args if arg.val == rec and arg.type.startswith('Severity') ]) ]
                for e in es:
                    arg = [ arg for arg in e.args if arg.val == rec and arg.type.startswith('Severity') ][0]
                    arg.type = 'Acuteness'
    return annotations

def asa_nyha_ecog(annotations):
    ''' Convert ASA & NYHA & ECOG Condition -> Observation[clinical-score] '''
    for ann in annotations:
        asa  = [ v for _,v in ann.Ts.items() if (v.span == 'ASA' or re.match(regex_asa, v.span, re.IGNORECASE)) and v.type in [ 'Condition', 'Condition-Name'] ]
        nyha = [ v for _,v in ann.Ts.items() if re.match(regex_nyha, v.span, re.IGNORECASE) and v.type in [ 'Condition', 'Condition-Name'] ]
        ecog = [ v for _,v in ann.Ts.items() if re.match(regex_ecog, v.span, re.IGNORECASE) and v.type in [ 'Condition', 'Condition-Name'] ]
        all = asa+nyha+ecog
        if len(all):
            max_a = max([ int(a.id.replace('A','')) for _,a in ann.As.items() ])+1 if len(ann.As) else 1
            for rec in all:
                if rec.type == 'Condition-Name':
                    rec.type = 'Observation-Name'
                    a_id = f'A{max_a}'
                    a = BratA('Observation-Type-Value', rec, 'clinical-score', a_id, -1)
                    ann.As[a_id] = a
                    max_a += 1
                elif rec.type == 'Condition':
                    rec.type = 'Observation'
                    e = [ v for _,v in ann.Es.items() if v.args[0].val == rec ][0]
                    e.type = rec.type
                    e.args[0].type = rec.type
                    eqs = [ arg for arg in e.args if arg.type == 'Stage' ]
                    for eq in eqs:
                        eq.type = 'Eq-Comparison'
                    ann.Es[e.id] = e
                ann.Ts[rec.id] = rec
    return annotations

def no_attrs(annotations):
    for ann in annotations:
        matched = [ v for _,v in ann.Es.items() if v.args[0].val.type == 'Temporal-Connection' ]
        for rec in matched:
            a_s = [ v for _,v in ann.As.items() if v.attr_of == rec ]
            if not len(a_s):
                print(f'Temporal-Connection has no attribute!')


def anatomy(annotations):
    mods = {}
    for ann in annotations:
        matched  = [ v.span.lower() for _,v in ann.Ts.items() if v.type == 'Modifier' ]
        for m in matched:
            if m in mods:
                mods[m] += 1
            else:
                mods[m] = 1
    
    for k,v in sorted(mods.items(), key=lambda x: x[1], reverse=True)[:50]:
        print(f'{k} {v}')

    return annotations
    

def main():

    # Get data
    brat_train_raw = {} 
    for d in Config.annotation_train_dirs:
        brat_train_raw = {**brat_train_raw, **utils.fetch_brat_files(d)}
    annotations = [ BratDocument(k, v[0], v[1], v[2], surface_only=True) for k,v in brat_train_raw.items() ]

    modifiers(annotations)

    As, Rs, Ts, Es, args, ents = {}, {}, {}, {}, {}, {}
    for ann in annotations:
        for _, t in ann.Ts.items():
            if t.type in Ts: Ts[t.type] += 1
            else:            Ts[t.type] = 1
            if not any([ e for _, e in ann.Es.items() if any(e.args) and e.args[0].val == t ]):
                if t.type in ents: ents[t.type] += 1
                else:              ents[t.type] = 1
        for _, e in ann.Es.items():
            if any(e.args):
                if e.args[0].type in Es: Es[e.args[0].type] += 1
                else:                    Es[e.args[0].type] = 1
                for arg in e.args[1:]:
                    if arg.type == 'Name':
                        continue
                    if any(re.findall(regex_trailing_num, arg.type)):
                        arg.type = re.sub(regex_trailing_num, '', arg.type)
                    if arg.type in args: args[arg.type] += 1
                    else:                args[arg.type] = 1
        for _, r in ann.Rs.items():
            if r.type in Rs: Rs[r.type] += 1
            else:            Rs[r.type] = 1
        for _, a in ann.As.items():
            if a.type in As: As[a.type] += 1
            else:            As[a.type] = 1

    t_sum_cnt = sum([ cnt for t, cnt in Ts.items() ])
    print('Ts', t_sum_cnt)
    for t, cnt in sorted(Ts.items()):
        print('\t', t, cnt, round(cnt / t_sum_cnt * 100.0, 1))

    r_sum_cnt = sum([ cnt for r, cnt in Rs.items() ])
    print('Rs', r_sum_cnt)
    for r, cnt in sorted(Rs.items()):
        print('\t', r, cnt, round(cnt / r_sum_cnt * 100.0, 1))

    arg_sum_cnt = sum([ cnt for arg, cnt in args.items() ])
    print('Args', arg_sum_cnt)
    for arg, cnt in sorted(args.items()):
        print('\t', arg, cnt, round(cnt / arg_sum_cnt * 100.0, 1))

    # Convert
    # TODO: anatomy, Histology
    for converter in [ anatomy ]:
        annotations = converter(annotations)
        
    #for ann in annotations:
    #    to_brat(ann)
    

    
if __name__ == '__main__':
    main()