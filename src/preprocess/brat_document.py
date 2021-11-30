import os
import re
import spacy
tokenize = spacy.load('en_core_web_sm')

converters = { '˂':'<', '＜':'<', '＞':'>', '：':':', '－':'-', '﴾':'(', '﴿':')', '（':'(', '、':',', '，':',' }

def pretokenize(text):
    reg_num = r'\d'
    possible_code = r'[a-zA-Z]+\d+(\.\d{1,2})?'
    is_possible_code = lambda i: re.match(possible_code, lowered[i-2:i+2])
    dividers = { '<', '>', '=', '≥', '≤', '-', '˂', '\\', '/', '＜', '＞', '(', ')', '~', '、', '+', '≧', '±', '：', ':',
                 '③', '④', '－', ',', '﴾', '﴿', '[', ']', '，', '（', '∙', '+', '%', 'ᵃ', '*' }
    cleaned = []
    prev = ''
    prev_num = False
    prev_per = False
    prev_add_end = '', ''
    is_num = re.match(reg_num, text[0])
    pad_map = {}

    # Char-level check
    lowered = text.lower()
    for i, ch in enumerate(text):
        foll = text[i+1] if i < len(text)-1 else ''
        foll_num = re.match(reg_num, foll) or (is_num and foll in ['.',','])
        is_per = ch == '.'
        add_start, add_end = '', ''
        if ch in dividers:
            if prev != ' ': 
                add_start = ' '
            if foll != ' ': 
                add_end = ' '
        if prev_num and ch != ' ' and not is_num and not is_possible_code(i):
            add_start = ' '
        if not is_num and prev_per:
            add_start = ' '
        if (lowered[:i].endswith('pre') or lowered[:i].endswith('post') or lowered[:i].endswith('peri')) and (lowered[i:].startswith('oper') or lowered[i:].startswith('treat')):
            add_start = ' '
        if not prev_num and (ch == '.' or is_num):
            add_start = ' '
        if prev_num and ch == 'x' and foll_num:
            add_start = ' '
            add_end = ' '
        if text[:i].endswith('Grade') and ch == 'Ⅰ':
            add_start = ' '
        if text[:i].endswith('ASA') and ch == 'I':
            add_start = ' '
        if ch in converters:
            ch = converters.get(ch)
        if add_start == ' ' and (prev_add_end == ' ' or prev.endswith(' ')):
            add_start = ''
        if add_end == ' ' and foll == ' ':
            add_end = ''
        
        cleaned.append(add_start + ch + add_end)
        #pad_map[i] = (pad_map[i-1] if i > 0 else 0) + len(add_start) + len(prev_add_end)
        pad_map[i] = (pad_map[i-1] if i > 0 else 0) + len(add_start + add_end) + len(ch)-1

        prev = ch
        prev_num = is_num
        prev_per = is_per
        is_num = foll_num
        prev_add_end = add_end

    cleaned = ''.join(cleaned)
    return pad_map, cleaned

class BratDocument:
    def __init__(self, doc_id, text, anns, path, surface_only=False):
        self.doc_id       = doc_id
        self.raw_text     = text
        self.raw_anns     = anns
        self.path         = path
        self.sents        = None
        self.Ts           = None
        self.Es           = None
        self.Rs           = None 
        self.As           = None
        self.toks         = None

        if not surface_only:
            pad_map, pretokenized = pretokenize(text)
            self.pretokenized = pretokenized
            self.derive_annotations(pad_map)
        else:
            self.pretokenized = self.raw_text
            self.derive_annotations_surface_only()

    def to_brat(self):
        lines = []
        for _,v in self.Es.items(): lines.append(v.to_brat())
        for _,v in self.Ts.items(): lines.append(v.to_brat())
        for _,v in self.As.items(): lines.append(v.to_brat())
        for _,v in self.Rs.items(): lines.append(v.to_brat())
        return self.pretokenized, '\n'.join(lines)

    def set_pointers(self, Ts, Es, Rs, As):
        
        # Es
        for k, v in Es.items():
            for i, arg in enumerate(v.args):
                pointer = arg.val
                getter = Ts if pointer[0] == 'T' else Es if pointer[0] == 'E' else None
                if getter and getter.get(pointer):
                    Es[k].args[i] = BratEArgPair(arg.type, getter[pointer])
                else:
                    print(f"E's pointer doesn't exist! {self.path}/{self.doc_id}: {k}")

        # As
        for k, v in As.items():
            pointer = v.attr_of
            getter = Ts if pointer[0] == 'T' else Es if pointer[0] == 'E' else None
            if getter and getter.get(pointer):
                v.attr_of = getter[pointer]
                As[k] = v
            else:
                print(f"A's pointer doesn't exist! {self.path}/{self.doc_id}: {k}")
        for k, v in Rs.items():
            pointer = v.arg1
            getter = Ts if pointer[0] == 'T' else Es if pointer[0] == 'E' else None
            if getter and getter.get(pointer):
                v.arg1 = getter[pointer]
                Rs[k] = v
            else:
                print(f"R's pointer1 doesn't exist! {self.path}/{self.doc_id}: {k}")
            pointer = v.arg2
            getter = Ts if pointer[0] == 'T' else Es if pointer[0] == 'E' else None
            if getter and getter.get(pointer):
                v.arg2 = getter[pointer]
                Rs[k] = v
            else:
                print(f"R's pointer2 doesn't exist! {self.path}/{self.doc_id}: {k}")

        return Ts, Es, Rs, As

    def derive_annotations_surface_only(self):
        Ts, Es, Rs, As = {}, {}, {}, {}

        for i,ann in enumerate(self.raw_anns.splitlines()):
            if not len(ann.strip()) or '\t' not in ann:
                continue

            parts = ann.split('\t')
            sub_parts = [ part for part in parts[1].split(' ') if part != '' ]
            ch = parts[0].strip()
            if ch[0] == 'T':
                if ';' in parts[1]:
                    sub_parts = [ sub_parts[0], sub_parts[1], sub_parts[2].split(';')[0] ]
                Ts[ch] = BratT(sub_parts[0].strip(), int(sub_parts[1]), int(sub_parts[2]), parts[2].strip(), ch, i)
            elif ch[0] == 'A':
                if len(sub_parts) != 3:
                    continue
                As[ch] = BratA(sub_parts[0].strip(), sub_parts[1].strip(), sub_parts[2].strip(),ch, i)
            elif ch[0] == 'E': 
                Es[ch] = BratE(ch, i)
                for part in sub_parts:
                    kvs = part.split(':')
                    Es[ch].args.append(BratEArgPair(kvs[0].strip(), kvs[1].strip()))
            elif ch[0] == 'R':
                _, arg1 = sub_parts[1].split(':')
                _, arg2 = sub_parts[2].split(':')
                Rs[ch] = BratR(sub_parts[0].strip(), arg1, arg2, ch, i)

        Ts, Es, Rs, As = self.set_pointers(Ts, Es, Rs, As)
        self.Ts = Ts
        self.Es = Es
        self.As = As
        self.Rs = Rs
        

    def derive_annotations(self, pad_map):
        anns = self.raw_anns
        Ts, Es, Rs, As = {}, {}, {}, {}
        toks = tokenize(self.pretokenized)

        # First pass, index each annotation type
        for i,ann in enumerate(anns.splitlines()):
            if not len(ann.strip()) or '\t' not in ann:
                continue

            parts = ann.split('\t')
            sub_parts = [ part for part in parts[1].split(' ') if part != '' ]
            ch = parts[0].strip()
            if ch[0] == 'T':
                Ts[ch] = BratT(sub_parts[0].strip(), int(sub_parts[1]), int(sub_parts[2]), parts[2].strip(), ch, i)
            elif ch[0] == 'A':
                As[ch] = BratA(sub_parts[0].strip(), sub_parts[1].strip(), sub_parts[2].strip(),ch, i)
            elif ch[0] == 'E': 
                Es[ch] = BratE(ch, i)
                for part in sub_parts:
                    kvs = part.split(':')
                    Es[ch].args.append(BratEArgPair(kvs[0].strip(), kvs[1].strip()))
            elif ch[0] == 'R':
                _, arg1 = sub_parts[1].split(':')
                _, arg2 = sub_parts[2].split(':')
                Rs[ch] = BratR(sub_parts[0].strip(), arg1, arg2, ch, i)

        # Split pseudo-sentences on newlines
        pseudo_sents, curr_sents, final_toks, sent_idx = [], [], [], 0
        for i, tok in enumerate(toks):
            tok_ = Token(tok, sent_idx)
            if tok_.text.replace(' ','') == '\n' and i > 0 and len(curr_sents):
                pseudo_sents.append(curr_sents)
                curr_sents = []
                sent_idx += 1
            curr_sents.append(tok_)
            final_toks.append(tok_)
        if len(curr_sents):
            pseudo_sents.append(curr_sents)
        toks = final_toks

        # Add token-level indexes to 'T' types
        for k, v in Ts.items():
            try:
                start = [ t for t in toks if t.idx == v.char_beg_idx + pad_map[v.char_beg_idx]]
                if not len(start):
                    start = [ t for t in toks if t.idx == v.char_beg_idx-1 + pad_map[v.char_beg_idx]][0]
                else:
                    start = start[0]
            except:
                continue
            for i,ch in enumerate(v.span):
                if ch in converters:
                    v.span = v.span[:i] + converters.get(ch) + v.span[i+1:]
            no_spaced = v.span.replace(' ','')
            matches = [ start ]
            matches_no_spaced = start.text
            while True: 
                nxt = toks[matches[-1].i+1] if len(toks) > matches[-1].i+1 else None
                if nxt == None or " ".join([ m.text for m in matches ]).replace(' ','') == v.span.replace(' ',''):
                    break
                if no_spaced.startswith(matches_no_spaced+nxt.text.replace(' ','')):
                    matches.append(nxt)
                    matches_no_spaced = ''.join([ m.text for m in matches ]).replace(' ','')
                else:
                    break

            all_matched = " ".join([ m.text for m in matches ]).replace(' ','') == v.span.replace(' ','')
            if not all_matched:
                print(f'Spans did not match! {self.path}/{self.doc_id} {v}')

            if all_matched:
                Ts[k].tok_beg_idx  = min([ tok.i for tok in matches ])
                Ts[k].tok_end_idx  = max([ tok.i for tok in matches ])
                Ts[k].tok_idxs     = [ tok.i for tok in matches ]
                Ts[k].char_beg_idx = min([ tok.idx for tok in matches ])
                Ts[k].char_end_idx = max([ tok.idx + len(tok.text) for tok in matches ])
                Ts[k].span         = self.pretokenized[Ts[k].char_beg_idx:Ts[k].char_end_idx]
                Ts[k].sent_idx     = min([ tok.sent_idx for tok in matches ])
            else:
                print(f"T spans didn't match! {self.path}/{self.doc_id} {v}")

        Ts, Es, Rs, As = self.set_pointers(Ts, Es, Rs, As)
        self.sents = pseudo_sents
        self.toks  = final_toks
        self.Ts = Ts
        self.Es = Es
        self.As = As
        self.Rs = Rs

    def to_r_bert_format(self, relation2id, id2relation, known_rel_types):

        regex_trailing_num = r'\d'
        data, rels = [], []
        clean_rel = lambda tp: re.sub(regex_trailing_num, '', tp) if ':Arg' not in tp and any(re.findall(regex_trailing_num, tp)) else tp

        # By Entity
        for _, e1 in self.Ts.items():

            # Check Entities by Relation
            for _, e2 in self.Ts.items():
                if e1 == e2 or e1.sent_idx != e2.sent_idx or e2.type == e1.type+'-Name' or (e1.type, e2.type) not in known_rel_types:
                    continue

                rels_temp = [ r for _, r in self.Rs.items() if r.arg1.get_T() == e1 and r.arg2.get_T() == e2 ]
                relation = clean_rel('Relation:'+rels_temp[0].type) if len(rels_temp) else 'Other'
                rel = { 
                    'subj': e1 ,'subj_start': e1.tok_beg_idx, 'subj_end': e1.tok_end_idx, 'subj_type': e1.type,
                    'obj': e2,'obj_start': e2.tok_beg_idx, 'obj_end': e2.tok_end_idx, 'obj_type': e2.type,
                    'relation': relation
                }
                rels.append(rel)

            # Check Events by Relation
            for _, e2 in self.Es.items():
                t2 = e2.get_T()
                if e1.sent_idx != t2.sent_idx or (e1.type, t2.type) not in known_rel_types:
                    continue

                rels_temp = [ r for _, r in self.Rs.items() if r.arg1.get_T() == e1 and r.arg2.get_T() == t2 ]
                relation = clean_rel('Relation:'+rels_temp[0].type) if len(rels_temp) else 'Other'
                rel = { 
                    'subj': e1 ,'subj_start': e1.tok_beg_idx, 'subj_end': e1.tok_end_idx, 'subj_type': e1.type,
                    'obj': t2,'obj_start': t2.tok_beg_idx, 'obj_end': t2.tok_end_idx, 'obj_type': t2.type,
                    'relation': relation
                }
                rels.append(rel)

        # By Event
        for _, e1 in self.Es.items():
            t1 = e1.get_T()

            # Check Eq-Comparison -> Units specifically (as they can be 'Per' or 'Unit' arguments, so need to predict)
            #if t1.type == 'Eq-Comparison':
            #    args = [ arg for arg in e1.args[1:] if arg.type in [ 'Unit', 'Per' ] and isinstance(arg.val, BratT) and arg.val.type in [ 'Eq-Unit', 'Eq-Temporal-Unit' ] ]
            #    for arg in args:
            #        relation = clean_rel('Argument:'+arg.type)
            #        rel = { 
            #            'subj': e1 ,'subj_start': t1.tok_beg_idx, 'subj_end': t1.tok_end_idx, 'subj_type': t1.type,
            #            'obj': arg.val,'obj_start': arg.val.tok_beg_idx, 'obj_end': arg.val.tok_end_idx, 'obj_type': arg.val.type,
            #            'relation': relation
            #        }
            #        rels.append(rel)

            # Check Events by Relation
            for _, e2 in self.Es.items():
                t2 = e2.get_T()
                if e1 == e2 or t1.sent_idx != t2.sent_idx or (t1.type, t2.type) not in known_rel_types:
                    continue

                rels_temp = [ r for _, r in self.Rs.items() if r.arg1 == e1 and r.arg2 == e2 ]
                relation = clean_rel('Relation:'+rels_temp[0].type) if len(rels_temp) else 'Other'
                rel = { 
                    'subj': e1 ,'subj_start': t1.tok_beg_idx, 'subj_end': t1.tok_end_idx, 'subj_type': t1.type,
                    'obj': e2,'obj_start': t2.tok_beg_idx, 'obj_end': t2.tok_end_idx, 'obj_type': t2.type,
                    'relation': relation
                }
                rels.append(rel)
                    
            # Check Events by Argument
            for _, e2 in self.Es.items():
                t2 = e2.get_T()
                if t1.sent_idx != t2.sent_idx or (t1.type, t2.type) not in known_rel_types or (t2.char_beg_idx >= t1.char_beg_idx and t2.char_end_idx <= t1.char_end_idx):
                    continue
                rels_temp = [ arg for arg in e1.args[1:] if arg.val == e2 ]

                if len(rels_temp):
                    rel_type = rels_temp[0].type
                    if 'Arg' not in rel_type and any(re.findall(regex_trailing_num, rel_type)):
                        rel_type = clean_rel('Argument:'+re.sub(regex_trailing_num, '', rel_type))
                    else:
                        rel_type = 'Argument:'+rel_type
                else:
                    rel_type = 'Other'

                rel = { 
                    'subj': e1 ,'subj_start': t1.tok_beg_idx, 'subj_end': t1.tok_end_idx, 'subj_type': t1.type,
                    'obj': e2,'obj_start': t2.tok_beg_idx, 'obj_end': t2.tok_end_idx, 'obj_type': t2.type,
                    'relation': rel_type
                }
                rels.append(rel)

            # Check Entities by Argument
            for _, t2 in self.Ts.items():
                if t1.sent_idx != t2.sent_idx or (t1.type, t2.type) not in known_rel_types or t2.type == t1.type+'-Name' or (t2.char_beg_idx >= t1.char_beg_idx and t2.char_end_idx <= t1.char_end_idx):
                    continue
                rels_temp = [ arg for arg in e1.args[1:] if arg.val == t2 ]

                if len(rels_temp):
                    rel_type = rels_temp[0].type
                    if 'Arg' not in rel_type and any(re.findall(regex_trailing_num, rel_type)):
                        rel_type = clean_rel('Argument:'+re.sub(regex_trailing_num, '', rel_type))
                    else:
                        rel_type = 'Argument:'+rel_type
                else:
                    rel_type = 'Other'

                rel = { 
                    'subj': e1 ,'subj_start': t1.tok_beg_idx, 'subj_end': t1.tok_end_idx, 'subj_type': t1.type,
                    'obj': t2,'obj_start': t2.tok_beg_idx, 'obj_end': t2.tok_end_idx, 'obj_type': t2.type,
                    'relation': rel_type
                }
                rels.append(rel)

        # Dedupe
        deduped = []
        for rel in rels:
            if rel['subj_start'] == rel['obj_start'] and rel['subj_end'] == rel['obj_end']:
                continue
            if rel['relation'] == 'Other':
                dup1 = [ r for r in rels if r != rel and r['subj_start'] == rel['subj_start'] and r['subj_end'] == rel['subj_end'] and r['obj_start'] == rel['obj_start'] and r['obj_end'] == rel['obj_end'] and r['relation'] != rel['relation'] ]
                dup2 = [ r for r in rels if r != rel and r['obj_start'] == rel['subj_start'] and r['obj_end'] == rel['subj_end'] and r['subj_start'] == rel['obj_start'] and r['subj_end'] == rel['obj_end'] and r['relation'] != rel['relation'] ]
                if not len(dup1) and not len(dup2):
                    deduped.append(rel)
            else:
                dup = [ r for r in deduped if r['subj_start'] == rel['subj_start'] and r['subj_end'] == rel['subj_end'] and r['obj_start'] == rel['obj_start'] and r['obj_end'] == rel['obj_end'] and r['relation'] == rel['relation'] ]
                if not len(dup):
                    deduped.append(rel)
        rels = deduped

        pad_back, pad_forw = 10, 10
        for rel in rels:
            subj_start = rel['subj_start']
            subj_end = rel['subj_end']
            subj_type = rel['subj_type']
            subj_span = rel['subj'].get_T().span
            obj_start = rel['obj_start']
            obj_end = rel['obj_end']
            obj_type = rel['obj_type']
            obj_span = rel['obj'].get_T().span
            relation = rel['relation']
            subject_first = subj_start < obj_start
            is_other = relation == 'Other'

            if 'Arg3' in relation or 'Arg4' in relation or 'Arg5' in relation:
                relation = relation.replace('Arg3','Arg2').replace('Arg4','Arg2').replace('Arg5','Arg2')
            
            if is_other:
                relation_id = relation2id['Other']
            elif subject_first:
                relation_id = relation2id[relation+'(E1,E2)']
            else:
                relation_id = relation2id[relation+'(E2,E1)']
            tokens = [ t.text for t in self.toks ]

            if subject_first:
                prec = tokens[subj_start-pad_back:subj_start]
                foll = tokens[obj_end+1:obj_end+pad_forw]
            else:
                prec = tokens[obj_start-pad_back:obj_start]
                foll = tokens[subj_end+1:subj_end+pad_forw]
            
            last_prec_newline = [ i for i,t in enumerate(prec) if t.replace(' ','') == '\n' ]
            first_foll_newline = [ i for i,t in enumerate(foll) if t.replace(' ','') == '\n' ]

            if len(last_prec_newline) > 0 :
                prec = prec[max(last_prec_newline)+1:]
            if len(first_foll_newline) > 0:
                foll = foll[:min(first_foll_newline)]

            if subj_type.endswith('-Name'):
                subj_type = subj_type.replace('-Name','')
            if obj_type.endswith('-Name'):
                obj_type = obj_type.replace('-Name','')

            if subject_first:
                new_tokens = prec + ["[E11]"] + [subj_type] + tokens[subj_start:subj_end+1] + ["[E12]"] + \
                             tokens[subj_end+1:obj_start] + ["[E21]"] + [obj_type] + tokens[obj_start:obj_end+1] + ["[E22]"] + foll
            else:
                new_tokens = prec + ["[E11]"] + [obj_type] + tokens[obj_start:obj_end+1] + ["[E12]"] + \
                             tokens[obj_end+1:subj_start] + ["[E21]"] + [subj_type] + tokens[subj_start:subj_end+1] + ["[E22]"] + foll

            if len(new_tokens) > 100:
                continue

            token_string = " ".join([ t.strip() for t in new_tokens ]).replace('\n','')
            output = f"{token_string}\t{relation_id}\t{id2relation[relation_id]}\n"
            data.append(output)

        return data


class BratSentence:
    def __init__(self, idx, toks):
        self.idx  = idx
        self.toks = toks
        

class BratT:
    def __init__(self, tp, char_beg_idx, char_end_idx, span, id, line):
        self.id           = id
        self.type         = tp
        self.span         = span
        self.line         = line
        # self.sent_idx     
        self.char_beg_idx = char_beg_idx
        self.char_end_idx = char_end_idx
        self.tok_beg_idx  = -1
        self.tok_end_idx  = -1
        self.tok_idxs     = []
        self.sent_idx     = -1

    def __str__(self):
        return f'{self.id}, "{self.span}", {self.char_beg_idx}, {self.char_end_idx}, {self.tok_beg_idx}, {self.tok_end_idx} '

    def get_T(self):
        return self

    def to_brat(self):
        return f'{self.id}\t{self.type} {self.char_beg_idx} {self.char_end_idx}\t{self.span}'

class BratE:
    def __init__(self, id, line):
        self.id   = id
        self.args = []
        self.line = line

    def get_T(self):
        if len(self.args):
            return self.args[0].val.get_T()
        return None

    def to_brat(self):
        return f'{self.id}\t{" ".join([ arg.type + ":" + arg.val.id for arg in self.args ])}'

class BratEArgPair:
    def __init__(self, tp, val):
        self.type = tp
        self.val  = val

    def get_T(self):
        return self.val.get_T()

class BratR:
    def __init__(self, tp, arg1, arg2, id, line):
        self.id = id
        self.type = tp
        self.arg1 = arg1
        self.arg2 = arg2
        self.line = line

    def to_brat(self):
        return f'{self.id}\t{self.type} Arg1:{self.arg1.id} Arg2:{self.arg2.id}'

class BratA:
    def __init__(self, tp, attr_of, val, id, line):
        self.type = tp
        self.val  = val
        self.id   = id
        self.line = line
        self.attr_of = attr_of

    def to_brat(self):
        return f'{self.id}\t{self.type} {self.attr_of.id} {self.val}'

class Token():
    def __init__(self, tok, sent_idx):
        self.tok = tok
        self.text = tok.text
        self.i = tok.i
        self.idx = tok.idx
        self.sent_idx = sent_idx