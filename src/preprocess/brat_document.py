import os
import re
import spacy
tokenize = spacy.load('en_core_web_sm')



def pretokenize(text):
    reg_num = r'\d'
    #common_numchars = [ ch.lower() for ch in [ 'CD4', 'B12', 'm2', 'm3', 'icd9', 'icd10' ] ]
    #is_common_numchar = lambda i: len([ com for com in common_numchars if lowered[:i+2].endswith(com)]) > 0
    possible_code = r'[a-zA-Z]+\d+(\.\d{1,2})?'
    is_possible_code = lambda i: re.match(possible_code, lowered[i-2:i+2])
    is_numeric = False
    prec_numeric = False
    dividers = { '<', '>', '=', '≥', '≤', '-', '˂', '\\', '/', '＜', '＞', '(', ')', '~', '、', '+', '≧' }
    cleaned = []
    prev = ''
    prev_num = False
    is_num = re.match(reg_num, text[0])

    # Pre/post/peri check
    reg_oper = r'(pre|post|peri)oper'
    matches = [ x for x in re.finditer(reg_oper, text, re.I) ]
    while matches:
        match = matches[0]
        idx = match.regs[1][1]
        text = text[:idx] + '-' + text[idx:]
        matches = [ x for x in re.finditer(reg_oper, text, re.I) ]

    # Char-level check
    lowered = text.lower()
    for i, ch in enumerate(text):
        foll = text[i+1] if i < len(text)-1 else ''
        foll_num = re.match(reg_num, foll) or (is_num and foll in ['.',','])
        add_start, add_end = '', ''
        if ch == '0' and foll == 'm':
            x=1
        if ch in dividers:
            if prev != ' ': 
                add_start = ' '
            if foll != ' ': 
                add_end = ' '
        if prev_num and ch != ' ' and not is_num and not is_possible_code(i):
            add_start = ' '
        prev_num = is_num
        prev = ch
        is_num = foll_num
        cleaned.append(add_start + ch + add_end)

    return ''.join(cleaned)

class BratDocument:
    def __init__(self, doc_id, text, anns, path):
        self.doc_id       = doc_id
        self.raw_text     = text
        self.pretokenized = pretokenize(text)
        self.raw_anns     = anns
        self.path         = path
        self.derive_annotations()
        self.sents
        self.Ts
        self.Es
        self.Rs
        self.As
        self.toks
        

    def derive_annotations(self, nest_sentences=False):
        anns = self.raw_anns
        Ts, Es, Rs, As = {}, {}, {}, {}
        toks = tokenize(self.pretokenized)

        # First pass, index each annotation type
        for i,ann in enumerate(anns.splitlines()):
            if not len(ann.strip()) or '\t' not in ann:
                continue

            beg_idx, end_idx, txt = -1, -1, None
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
                arg1 = sub_parts[1].split(':')[1]
                arg2 = sub_parts[2].split(':')[1]
                Rs[ch] = BratR(sub_parts[0].strip(), arg1, arg2, ch, i)

        # Split pseudo-sentences on newlines
        pseudo_sents, curr_sents, final_toks = [], [], []

        # If not nested, newlines separate sentences
        if not nest_sentences:
            for i, tok in enumerate(toks):
                if tok.text.replace(' ','') == '\n' and i > 0 and len(curr_sents):
                    pseudo_sents.append(curr_sents)
                    curr_sents = []
                curr_sents.append(tok)
                final_toks.append(tok)
            if len(curr_sents):
                pseudo_sents.append(curr_sents)
        
        # Else, following sentences indented deeper are included as part of parent sentence
        else:
            for i, tok in enumerate(toks):
                if tok.text.replace(' ','') == '\n' and i > 0 and len(curr_sents):
                    pseudo_sents.append(curr_sents)
                    curr_sents = []
                curr_sents.append(tok)
                final_toks.append(tok)
            if len(curr_sents):
                pseudo_sents.append(curr_sents)

        # Add token-level indexes to 'T' types
        splitters = r'(\/|\\| |<|>|=|≥|≤|-)'
        for k, v in Ts.items():
            all_matched, matches, tok_cands, idx_start = True, [], [], v.char_beg_idx
            splt = [ s for s in re.split(splitters, v.span) if len(s.strip()) > 0 ]
            for part in splt:
                cands = [ tok for tok in final_toks if tok.idx >= idx_start and (tok.text.startswith(part) or part.startswith(tok.text)) ]
                if len(cands) > 0:
                    best_match = sorted(cands, key=lambda x: x.idx)[0]
                    if len(str(best_match)) == 1 and len(part) > 1:
                        best_match = sorted(cands, key=lambda x: len(x), reverse=True)[0]
                    #best_match = sorted(cands, key=lambda x: len(x), reverse=True)[0]
                    matches.append(best_match)
                    idx_start += len(str(best_match))
                else:
                    all_matched = False
                    break

            if all_matched:
                Ts[k].tok_beg_idx = min([ tok.i for tok in matches ])
                Ts[k].tok_end_idx = max([ tok.i for tok in matches ])
                Ts[k].tok_idxs    = [ tok.i for tok in matches ]
            else:
                print(f"T spans didn't match! {self.path}/{self.doc_id} {v}")

        # Substitute indexed names for objects
        # Es
        to_remove = []
        for k, v in Es.items():
            for i, arg in enumerate(v.args):
                pointer = arg.val
                getter = Ts if pointer[0] == 'T' else Es if pointer[0] == 'E' else None
                if getter and getter.get(pointer):
                    Es[k].args[i] = BratEArgPair(arg.type, getter[pointer])
                else:
                    print(f"E's pointer doesn't exist! {v}")

        # As
        for k, v in As.items():
            pointer = v.attr_of
            getter = Ts if pointer[0] == 'T' else Es if pointer[0] == 'E' else None
            if getter and getter.get(pointer):
                v.attr_of = getter[pointer]
                As[k] = v
            else:
                print(f"A's pointer doesn't exist! {v}")
        for k, v in Rs.items():
            pointer = v.arg1
            getter = Ts if pointer[0] == 'T' else Es if pointer[0] == 'E' else None
            if getter and getter.get(pointer):
                v.arg1 = getter[pointer]
                Rs[k] = v
            else:
                print(f"R's pointer1 doesn't exist! {v}")
            pointer = v.arg2
            getter = Ts if pointer[0] == 'T' else Es if pointer[0] == 'E' else None
            if getter and getter.get(pointer):
                v.arg2 = getter[pointer]
                Rs[k] = v
            else:
                print(f"R's pointer2 doesn't exist! {v}")

        self.sents = pseudo_sents
        self.toks  = final_toks
        self.Ts = Ts
        self.Es = Es
        self.As = As
        self.Rs = Rs


    def to_dygiepp_format(self, debug=False):

        output = { "doc_key": self.doc_id, "sentences": [ [ tok.text for tok in sent ] for sent in self.sents ], "ner": [], "relations": [], "clusters": [], "events": [] }
        regex_trailing_num = r'[0-9]$'

        # For each sentence
        min_tok_idx, max_tok_idx = 0, 0
        for i, sent in enumerate(output['sentences']):
            max_tok_idx += len(sent)-1
            curr_ner, curr_rel, curr_coref, curr_ev = [], [], [], []

            # NER
            for k, v in self.Ts.items():
                if v.tok_beg_idx >= min_tok_idx and v.tok_end_idx <= max_tok_idx:
                    if str(self.toks[v.tok_beg_idx]) != v.span.split(' ')[0]:
                        x=1

                    a = [ a_v for a_k, a_v in self.As.items() if a_v.attr_of == v ]
                    tp = f'{v.type}___{a[0].val}' if len(a) else v.type
                    curr_ner.append([ v.tok_beg_idx, v.tok_end_idx, tp ])

            # Relations & Clusters
            for k, v in self.Rs.items():
                arg1 = v.arg1.args[0].val if isinstance(v.arg1, BratE) else v.arg1
                arg2 = v.arg2.args[0].val if isinstance(v.arg2, BratE) else v.arg2
                if  arg1.tok_beg_idx >= min_tok_idx and arg1.tok_end_idx <= max_tok_idx and \
                    arg2.tok_beg_idx >= min_tok_idx and arg2.tok_end_idx <= max_tok_idx:

                    if v.type == 'Coreference':
                        curr_coref.append([ arg1.tok_beg_idx, arg1.tok_end_idx, arg2.tok_beg_idx, arg2.tok_end_idx ])
                    else:
                        curr_rel.append([ arg1.tok_beg_idx, arg1.tok_end_idx, arg2.tok_beg_idx, arg2.tok_end_idx, v.type ])

            # Events
            for k, v in self.Es.items():
                trigger = v.args[0].val
                event_arrs = [ [ trigger.tok_beg_idx, trigger.type ] ]
                for ev in v.args[1:]:
                    if isinstance(ev.val, BratE):
                        min_idx = ev.val.args[0].val.tok_beg_idx
                        max_idx = ev.val.args[0].val.tok_end_idx
                    else:
                        min_idx = ev.val.tok_beg_idx
                        max_idx = ev.val.tok_end_idx
                    if min_idx == -1 or max_idx == -1:
                        continue
                    if min_idx >= min_tok_idx and max_idx <= max_tok_idx:
                        tp = ev.type
                        if 'Arg' not in tp and any(re.findall(regex_trailing_num, tp)):
                            tp = re.sub(regex_trailing_num, '', tp)
                        event_arrs.append([ min_idx, max_idx, tp ])
                curr_ev.append(event_arrs)

            output['ner'].append(curr_ner)
            output['clusters'].append(curr_coref)
            output['relations'].append(curr_rel)
            output['events'].append(curr_ev)
            min_tok_idx = max_tok_idx

        if debug:
            toks = []
            for sent in output['sentences']:
                for t in sent:
                    toks.append(t)

            print(output['doc_key'])
            print(f'    \nNER:')
            for ne in output['ner']: 
                for x in ne:
                    print(f'        "{" ".join([ str(toks[y]) for y in sorted(set(x[:2])) ])}" {x[2]} {x}')
            print(f'    \nRelations:')
            for rel in output['relations']:
                for x in rel:
                    print(f'        "{" ".join([ str(toks[y]) for y in sorted(set(x[:2])) ])}" "{" ".join([ str(toks[y]) for y in sorted(set(x[2:-1])) ])}"  {x[4]} {x}')
            print(f'    \nEvents:')
            for ev in output['events']:
                for x in ev:
                    print(f'        "{toks[x[0][0]]}" {x[0][1]} {x}')
                    for y in x[1:]:
                        print(f'            "{" ".join([ str(toks[z]) for z in sorted(set(y[:2])) ])}" {y[2]}')

        return output

    def to_dygiepp_format2(self, debug=False):

        output = { "doc_key": self.doc_id, "sentences": [ [ tok.text for tok in sent ] for sent in self.sents ], "ner": [], "relations": [], "clusters": [], "events": [] }

        event_types = set([ v.args[0].type for k, v in self.Es.items() ])
        regex_trailing_num = r'[0-9]$'

        # For each sentence
        min_tok_idx, max_tok_idx = 0, 0
        for i, sent in enumerate(output['sentences']):
            max_tok_idx += len(sent)-1
            curr_ner, curr_rel, curr_coref, curr_ev = [], [], [], []

            # NER
            for k, v in self.Ts.items():
                if v.type not in event_types and \
                   v.tok_beg_idx >= min_tok_idx and \
                   v.tok_end_idx <= max_tok_idx:
                    curr_ner.append([ v.tok_beg_idx, v.tok_end_idx, 'T:'+v.type ])

            # Attributes
            for k, v in self.As.items():
                t = v.attr_of.get_T()
                if t.tok_beg_idx >= min_tok_idx and t.tok_end_idx <= max_tok_idx:
                    curr_ner.append([ t.tok_beg_idx, t.tok_end_idx, 'A:'+v.type+'___'+v.val ])

            # Relations & Clusters
            for k, v in self.Rs.items():
                arg1 = v.arg1.get_T()
                arg2 = v.arg2.get_T()
                if arg1.tok_beg_idx >= min_tok_idx and arg1.tok_end_idx <= max_tok_idx and \
                   arg2.tok_beg_idx >= min_tok_idx and arg2.tok_end_idx <= max_tok_idx:
                    curr_rel.append([ arg1.tok_beg_idx, arg1.tok_end_idx, arg2.tok_beg_idx, arg2.tok_end_idx, 'R:'+v.type ])

            # Events
            for k, v in self.Es.items():
                trigger = v.get_T()
                if trigger.tok_beg_idx >= min_tok_idx and trigger.tok_end_idx <= max_tok_idx:
                    for ev in v.args[1:]:
                        t = ev.get_T()
                        tp = ev.type
                        if 'Arg' not in tp and any(re.findall(regex_trailing_num, tp)):
                            tp = re.sub(regex_trailing_num, '', tp)
                        if t.tok_beg_idx >= min_tok_idx and t.tok_end_idx <= max_tok_idx:
                            tp = ev.type
                            if 'Arg' not in tp and any(re.findall(regex_trailing_num, tp)):
                                tp = re.sub(regex_trailing_num, '', tp)
                            curr_rel.append([ trigger.tok_beg_idx, trigger.tok_end_idx, t.tok_beg_idx, t.tok_end_idx, 'E:'+tp ])

            output['ner'].append(curr_ner)
            output['clusters'].append(curr_coref)
            output['relations'].append(curr_rel)
            output['events'].append(curr_ev)
            min_tok_idx = max_tok_idx

        if debug:
            toks = []
            for sent in output['sentences']:
                for t in sent:
                    toks.append(t)

            print(output['doc_key'])
            print(f'    \nNER:')
            for ne in output['ner']: 
                for x in ne:
                    print(f'        "{" ".join([ str(toks[y]) for y in sorted(set(x[:2])) ])}" {x[2]} {x}')
            print(f'    \nRelations:')
            for rel in output['relations']:
                for x in rel:
                    print(f'        "{" ".join([ str(toks[y]) for y in sorted(set(x[:2])) ])}" "{" ".join([ str(toks[y]) for y in sorted(set(x[2:-1])) ])}"  {x[4]} {x}')

        return output

    def to_r_bert_format(self, relation2id, id2relation, known_rel_types, debug=False):

        regex_trailing_num = r'\d'
        sents = [ { 'tokens': [ tok.text for tok in sent ], 'entities': [], 'relations': [] } for sent in self.sents ]
        data = []
        clean_rel = lambda tp: re.sub(regex_trailing_num, '', tp) if ':Arg' not in tp and any(re.findall(regex_trailing_num, tp)) else tp

        sent_idx_map, tok_idx = {}, 0
        for sent_idx, sent in enumerate(sents):
            for tok in sent['tokens']:
                sent_idx_map[tok_idx] = sent_idx
                tok_idx += 1

        # For each sentence
        min_tok_idx, max_tok_idx = 0, 0
        idx = 0
        for i, sent in enumerate(sents):
            max_tok_idx += len(sent['tokens']) + (0 if i == 0 else 1)

            # Add named entities
            for k, v in self.Ts.items():
                #if v.tok_beg_idx >= min_tok_idx and v.tok_end_idx <= max_tok_idx:
                if v.tok_beg_idx in sent_idx_map and v.tok_end_idx in sent_idx_map and \
                   sent_idx_map[v.tok_beg_idx] == i and sent_idx_map[v.tok_end_idx] == i:
                    sent['entities'].append(v)

            # Add relations
            for _, R in self.Rs.items():
                arg1, arg2 = R.arg1.get_T(), R.arg2.get_T()
                if arg1.tok_beg_idx >= min_tok_idx and arg1.tok_end_idx <= max_tok_idx and \
                   arg2.tok_beg_idx >= min_tok_idx and arg2.tok_end_idx <= max_tok_idx and not \
                   (arg1.tok_beg_idx == arg2.tok_beg_idx and arg1.tok_end_idx == arg2.tok_end_idx):

                    rel_type = R.type
                    if 'Arg' not in rel_type and any(re.findall(regex_trailing_num, rel_type)):
                        rel_type = re.sub(regex_trailing_num, '', rel_type)

                    rel = { 
                        'subj': arg1 ,'subj_start': arg1.tok_beg_idx, 'subj_end': arg1.tok_end_idx, 'subj_type': arg1.type,
                        'obj': arg2,'obj_start': arg2.tok_beg_idx, 'obj_end': arg2.tok_end_idx, 'obj_type': arg2.type,
                        'relation': clean_rel('Relation:'+rel_type)
                    }
                    sent['relations'].append(rel)


            # Add event arguments
            for _, E in self.Es.items():
                if E.get_T().tok_beg_idx >= min_tok_idx and E.get_T().tok_end_idx <= max_tok_idx:
                    for arg in E.args[1:]:
                        if arg.get_T().tok_beg_idx >= min_tok_idx and \
                           arg.get_T().tok_end_idx <= max_tok_idx and \
                           (arg.get_T().tok_beg_idx > E.get_T().tok_end_idx or arg.get_T().tok_end_idx < E.get_T().tok_beg_idx):

                            rel_type = arg.type
                            if 'Arg' not in rel_type and any(re.findall(regex_trailing_num, rel_type)):
                                rel_type = re.sub(regex_trailing_num, '', rel_type)

                            rel = { 
                                'subj': E.get_T(), 'subj_start': E.get_T().tok_beg_idx, 'subj_end': E.get_T().tok_end_idx, 'subj_type': E.get_T().type,
                                'obj': arg.val.get_T(), 'obj_start': arg.val.get_T().tok_beg_idx, 'obj_end': arg.val.get_T().tok_end_idx, 'obj_type': arg.val.get_T().type,
                                'relation': clean_rel('Argument:'+rel_type)
                            }
                            sent['relations'].append(rel)

            pad_back, pad_forw = 10, 10
            for ent1 in sent['entities']:
                ent1_idxs = range(ent1.tok_beg_idx, ent1.tok_end_idx+1, 1)
                for ent2 in sent['entities']:
                    if ent1 == ent2 or \
                       ((ent1.type, ent2.type) not in known_rel_types and (ent2.type, ent1.type) not in known_rel_types) or \
                       ent2.tok_beg_idx <= ent1.tok_beg_idx or \
                       ent2.tok_beg_idx in ent1_idxs or \
                       ent2.tok_end_idx in ent1_idxs or \
                       ent2.tok_end_idx > max_tok_idx or \
                       ent2.type == ent1.type+'-Name' or \
                       ent1.type == ent2.type+'-Name' or \
                       (ent1.type == 'Eq-Comparison' and ent2.type.startswith('Eq-')) or \
                       (ent2.type == 'Eq-Comparison' and ent1.type.startswith('Eq-')):
                        continue

                    rel_ent1 = [ rel for rel in sent['relations'] if rel['subj'] in [ ent1, ent2 ] ]
                    rel_ent2 = [ rel for rel in sent['relations'] if rel['obj'] in [ ent1, ent2 ] ]

                    # If there's a gold relation
                    if len(rel_ent1) == 1 and len(rel_ent2) == 1 and rel_ent1[0] == rel_ent2[0]:
                        is_other = False
                        rel = rel_ent1[0]
                        subj_start = rel['subj_start']
                        subj_end = rel['subj_end']
                        subj_type = rel['subj_type']
                        obj_start = rel['obj_start']
                        obj_end = rel['obj_end']
                        obj_type = rel['obj_type']
                        subject_first = subj_start < obj_start
                        
                        if subject_first:
                            relation_id = relation2id[rel['relation']+'(E1,E2)']
                        else:
                            relation_id = relation2id[rel['relation']+'(E2,E1)']
                    
                    # Else 'Other' relation
                    else:
                        continue
                        is_other = True
                        subj_start = ent1.tok_beg_idx
                        subj_end = ent1.tok_end_idx
                        subj_type = ent1.type
                        obj_start = ent2.tok_beg_idx
                        obj_end = ent2.tok_end_idx
                        obj_type = ent2.type
                        relation_id = relation2id['Other']
                        subject_first = subj_start < obj_start

                    tokens = [ str(t) for t in self.toks ]
                    idx += 1

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

                    if subject_first:
                        new_tokens = prec + ["[E11]"] + [subj_type] + tokens[subj_start:subj_end+1] + ["[E12]"] + \
                                     tokens[subj_end+1:obj_start] + ["[E21]"] + [obj_type] + tokens[obj_start:obj_end+1] + ["[E22]"] + foll
                        if not is_other:
                            if " ".join(tokens[subj_start:subj_end+1]) != rel['subj'].span:
                                continue
                        if is_other:
                            if " ".join(tokens[subj_start:subj_end+1]) != ent1.span:
                                continue
                    else:
                        new_tokens = prec + ["[E11]"] + [obj_type] + tokens[obj_start:obj_end+1] + ["[E12]"] + \
                                     tokens[obj_end+1:subj_start] + ["[E21]"] + [subj_type] + tokens[subj_start:subj_end+1] + ["[E22]"] + foll
                        if not is_other:
                            if " ".join(tokens[obj_start:obj_end+1]) != rel['obj'].span:
                                continue
                        if is_other:
                            if " ".join(tokens[obj_start:obj_end+1]) != ent2.span:
                                continue

                    if len(new_tokens) > 100:
                        continue

                    """
                    if subject_first:
                        new_tokens = prec + ["[E11]"] + tokens[subj_start:subj_end+1] + ["[E12]"] + \
                                     tokens[subj_end+1:obj_start] + ["[E21]"] + tokens[obj_start:obj_end+1] + ["[E22]"] + foll
                        if " ".join(tokens[subj_start:subj_end+1]) != rel['subj'].span:
                            continue
                    else:
                        new_tokens = prec + ["[E11]"] + tokens[obj_start:obj_end+1] + ["[E12]"] + \
                                     tokens[obj_end+1:subj_start] + ["[E21]"] + tokens[subj_start:subj_end+1] + ["[E22]"] + foll
                        if " ".join(tokens[obj_start:obj_end+1]) != rel['obj'].span:
                            continue
                    """

                    token_string = " ".join([ str(t) for t in new_tokens ]).replace('\n','')
                    print(f'\n{token_string}\n\t{id2relation[relation_id]}\n')
                    data.append(f"{token_string}\t{relation_id}\t{id2relation[relation_id]}\n")
                
            min_tok_idx = max_tok_idx

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

class BratA:
    def __init__(self, tp, attr_of, val, id, line):
        self.type = tp
        self.val  = val
        self.id   = id
        self.line = line
        self.attr_of = attr_of

    def to_brat(self):
        return f'{self.id}\t{self.type} {self.attr_of.id} {self.val}'

class FauxToken:
    def __init__(self, i, idx, text):
        self.i = i
        self.idx = idx
        self.text = text

    def __repl__(self):
        return self.text

    def __str__(self):
        return self.text