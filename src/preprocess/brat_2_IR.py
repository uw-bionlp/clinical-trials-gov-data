import os
import re
import sys
import json
import numpy as np
from random import shuffle

sys.path.append(os.path.join(os.getcwd(), 'src'))

from preprocess.brat_document import BratDocument, BratE, BratEArgPair, BratR, BratT
from preprocess.config import Config
import preprocess.utils as utils

from jsbeautifier import beautify
beautify_opts = {
  "indent_size": "4",
  "indent_char": " ",
  "max_preserve_newlines": "5",
  "preserve_newlines": True,
  "keep_array_indentation": False,
  "break_chained_methods": True,
  "indent_scripts": "normal",
  "brace_style": "collapse",
  "space_before_conditional": False,
  "unescape_strings": False,
  "jslint_happy": False,
  "end_with_newline": False,
  "wrap_line_length": "0",
  "indent_inner_html": False,
  "comma_first": False,
  "e4x": False,
  "indent_empty_lines": False
}

regex_trailing_num = r'\d'

def main():

    output_dir = os.path.join('../clinical_trials_query_gen','data','seq2seq', 'annotation')
    batch_size = 100
    total_needed = batch_size * 10

    docs = get_base_data()
    output = []
    for doc in docs:
        for pair in doc.to_tree():
            output.append(pair)
        
    shuffle(output)
    batch = 1

    existing = set() 
    for d in [ 'completed', 'reviewing' ]:
        for b in os.listdir(os.path.join(output_dir, d)):
            for f in os.listdir(os.path.join(output_dir, d, b)):
                existing.add(f)

    added = len(existing)
    for rec in output:
        filename = f'{rec["key"]}.js'
        if filename in existing:
            continue
        parent_dir = os.path.join(output_dir, 'reviewing', 'batch' + str(batch))
        if not os.path.exists(parent_dir):
            os.mkdir(parent_dir)
        with open(os.path.join(parent_dir, filename), 'w+') as fout:
            fout.write("'" + rec['orig'].replace("'","''") + "'")
            fout.write('\n\n')
            fout.write("'" + rec['intent'].replace("'","''") + "'")
            fout.write('\n\n')
            fout.write(rec['snippet'])
        added += 1
        if len(os.listdir(parent_dir)) == batch_size:
            batch += 1
        if added >= total_needed:
            break
    

def get_base_data():
    brat_train_raw = {} 
    for d in Config.annotation_train_dirs:
        brat_train_raw = {**brat_train_raw, **utils.fetch_brat_files(d)}
        #break
    annotations = [ BratDocument(k, v[0], v[1], v[2]) for k,v in brat_train_raw.items() ]
    docs   = [ BaseDoc(a) for a in annotations ]

    return docs

class BaseDoc:
    def __init__(self, ann):
        self.doc_id = ann.doc_id
        self.path   = ann.path
        self.text   = ann.pretokenized
        self.lines  = ann.pretokenized.split('\n')
        self.lines_transformed = []

        print(self.doc_id)

        self.derive_ents_and_rels(ann)
        self.node_groups = get_disjoint_node_groups(self.ents, self.rels)

        self.line_offsets = []
        offset_accum = 0
        for line in self.lines:
            self.line_offsets.append(offset_accum)
            offset_accum += len(line)+1

        for ent in self.ents:
            line_offset = self.line_offsets[ent.sent_idx]
            ent.char_sent_beg_idx = ent.char_beg_idx - line_offset
            ent.char_sent_end_idx = ent.char_end_idx - line_offset
        
        for i, line in enumerate(self.lines):
            offset = 0
            pre_change_len = len(line)
            for ent in sorted([ x for x in self.ents if x.sent_idx == i ], key=lambda x: x.char_sent_beg_idx):

                # No overlapping if not first
                if any([ x for x in self.ents if x.sent_idx == i and x != ent and x.text_transform and x.char_beg_idx <= ent.char_beg_idx and any(set(ent.tok_idxs).intersection(x.tok_idxs)) ]):
                    continue

                if ent.text_transform:
                    code = ent._to_code(add_attrs=False)
                    if code:
                        if isinstance(ent, Modifier): code = f'mod({code})'
                        line = line[:ent.char_sent_beg_idx+offset] + code + line[ent.char_sent_end_idx+offset:]
                        offset = len(line) - pre_change_len

            self.lines_transformed.append(line)       

        for ent in self.ents:
            ent.executed = False

    def to_tree(self):
        output = []
        print(f'{self.doc_id}')
        for line in self.node_groups:
            line_idx = [ grp[0] for grp in line ][0].sent_idx
            orig_line_text = self.lines[line_idx]
            line_text = self.lines_transformed[line_idx]
            print(f'\n"{line_text}"')
            codes = []
            for grp in line:
                code = self.to_branch(grp)
                codes.append(code)
            if len(line_text) < 524 and any(codes):
                code = f'intersect({", ".join(codes)})' if len(codes) > 1 else codes[0]
                output.append({ 
                    "doc_id": self.doc_id,
                    "line": line_idx,
                    "key": f'{self.doc_id}_{line_idx}',
                    "orig": orig_line_text.strip(), 
                    "intent": line_text.strip(), 
                    "snippet": code 
                })
        return output

    def to_branch(self, grp):
        seen = set()

        # break into levels
        ordered = sorted(sorted(grp, key=lambda x: x.tok_beg_idx), key=lambda x: x.priority)
        for ent in ordered:
            if ent in seen:
                continue
            or_ents = ent.ors()
            and_ents = ent.ands()
            if any(and_ents):
                ent = AndEntity([ ent ] + and_ents)
                for and_ent in and_ents:
                    seen.add(and_ent)
            for or_ent in or_ents:
                or_ents += or_ent.ors()
                seen.add(or_ent)
            if any(or_ents):
                ent = OrEntity([ ent ] + or_ents)
            x = Level(ent)
            code = x.to_code()
            try:
                code = beautify(code, beautify_opts)
            except:
                pass
            return code

    def derive_ents_and_rels(self, ann):

        ents_t = [ BaseEntity(x)   for _, x in ann.Ts.items() ]
        ents_e = [ BaseEntity(x)   for _, x in ann.Es.items() ]
        rels_r = [ BaseRelation(x) for _, x in ann.Rs.items() ]
        rels_e = []
        for _, e in ann.Es.items():
            arg1 = e.args[0]
            rels_e += [ BaseRelation(arg2, arg1) for arg2 in e.args[1:] ]

        ents = ents_e + [ t for t in ents_t if not any([ e for e in ents_e if t.type == e.type and t.tok_idxs == e.tok_idxs ]) ]
        ents = [ x.to_precise(self) for x in ents if x.to_precise(self) is not None ]
        rels = rels_r + rels_e
        
        # Assign relations
        to_del = []
        for i, rel in enumerate(rels):
            subj = [ x for x in ents if rel.subj in x.id ]
            if any(subj): 
                rel.subj = subj[0]
            else: 
                to_del.append(i)
                continue

            obj = [ x for x in ents if rel.obj in x.id ]
            if any(obj): 
                rel.obj = obj[0]
            else: 
                to_del.append(i)
                continue

            if rel.subj.sent_idx != rel.obj.sent_idx:
                to_del.append(i)
                continue

            for ent in ents:
                if ent == rel.subj:
                    ent.rels.append(rel)
                elif ent == rel.obj:
                    ent.rels_of.append(rel)

        # Add values
        for _, a in ann.As.items():
            e = [ x for x in ents if a.attr_of.id in x.id ]
            if any(e):
                e[0].val = a.val

        self.ents = ents
        self.rels = [ x for i, x in enumerate(rels) if i not in to_del and x.subj.sent_idx == x.obj.sent_idx ]

        for ent in self.ents:
            ent.add_attrs()

class Level:
    def __init__(self, ent):
        self.ent = ent
        self.rels = []

    def to_code(self):
        return self.ent.to_code()

class EntityAttribute:
    def __init__(self, type, ent, multi_ent_wrapper="or"):
        self.type = type
        self.ents = [ ent ]
        self.multi_ent_wrapper = multi_ent_wrapper

    def to_code(self):
        codes = [ x.to_code() for x in self.ents ]
        codes = [ x for x in codes if x ]
        codes = f"{self.multi_ent_wrapper}({', '.join([ x for x in codes ])})" \
            if len(codes) > 1 else ', '.join([ x for x in codes ])

        return f".{self.type}({codes})"

    def get_min_char_beg_idx(self):
        start = 0
        for ent in self.ents:
            if ent.get_min_char_beg_idx() < start:
                start = ent.get_min_char_beg_idx()
        return start

class OrEntity:
    def __init__(self, ents):
        self.ents = ents
        self.rels = []
        self.rels_of = []
        for ent in self.ents:
            self.rels += ent.rels
            self.rels_of += ent.rels_of

    def to_code(self):
        codes = [ x.to_code() for x in self.ents ]
        codes = [ x for x in codes if x ]

        if len(codes) > 1:
            return f'union({", ".join(codes)})'
        if any(codes):
            return codes[0]
        return ''

class AndEntity:
    def __init__(self, ents):
        self.ents = ents
        self.rels = []
        self.rels_of = []
        for ent in self.ents:
            self.rels += ent.rels
            self.rels_of += ent.rels_of

    def to_code(self):
        codes = [ x.to_code() for x in self.ents ]
        codes = [ x for x in codes if x ]
        
        if len(codes) > 1:
            return f'intersect({", ".join(codes)})'
        if any(codes):
            return codes[0]
        return ''

class Entity:
    def __init__(self, e, doc):
        self.doc          = doc
        self.id           = e.id
        self.val          = e.val
        self.span         = e.span
        self.sent_idx     = e.sent_idx
        self.sent_idx     = e.sent_idx
        self.char_beg_idx = e.char_beg_idx
        self.char_end_idx = e.char_end_idx
        self.tok_beg_idx  = e.tok_beg_idx
        self.tok_end_idx  = e.tok_end_idx
        self.tok_idxs     = e.tok_idxs
        self.rels         = e.rels
        self.rels_of      = e.rels_of
        self.is_head      = lambda : False
        self.priority     = None
        self.attrs        = {}
        self.span_as_arg  = False
        self.executed     = False
        self.text_transform = False

        for rel in e.rels:
            rel.subj = self
        for rel in e.rels_of:   
            rel.obj = self

    def get_min_char_beg_idx(self):
        start = self.char_beg_idx
        for verb, attr in self.attrs.items():
            for ent in attr.ents:
                if ent.char_beg_idx < start:
                    start = ent.char_beg_idx
        return start

    def add_attrs(self):
        hoistable = set(['abbrev_of','modifies'])
        subj_only = set(['using','found_by','treatment_for','temporality','duration','stability','severity','numeric_filter','minimum_count',
                         'before','during','after','from','except','code','type','negates','risk-for','polarity','criteria','location','is_other',
                         'if_then','has'])
        obj_only  = set(['modifies','equivalent_to','asserted','example_of'])
        rename    = { 
            'numeric_filter': 'num_filter', 'equivalent_to': 'equiv', 'minimum_count': 'min_count',
            'example_of': 'example', 'caused_by': 'causes', 'modifies': 'mod', 'risk-for': 'for',
            'abbrev_of': 'abbrev' }
        union     = set(['using','found_by','treatment_for','example_of','caused_by'])

        def to_ent_attr(tp, ent):
            _tp = tp
            multi_ent_wrapper = 'union' if tp in union else 'or'
            if _tp in rename:
                _tp = rename[_tp]
            return EntityAttribute(_tp, ent, multi_ent_wrapper)

        for rel in self.rels_of:
            tp = rel.type.lower().replace('-','_')
            if tp in hoistable:
                self.rels    += [ x for x in rel.subj.rels if x != rel ]
                self.rels_of += [ x for x in rel.subj.rels_of if x != rel ]
                rel.subj.rels = [ x for x in rel.subj.rels if x not in (self.rels + self.rels_of) ]
                rel.subj.rels_of = [ x for x in rel.subj.rels_of if x not in (self.rels + self.rels_of) ]

            if tp not in subj_only:
                if tp in self.attrs: self.attrs[tp].ents.append(rel.subj)
                else:                self.attrs[tp] = to_ent_attr(tp, rel.subj)

        for rel in self.rels:
            tp = rel.type.lower().replace('-','_')
            if tp not in obj_only:
                if tp in self.attrs: self.attrs[tp].ents.append(rel.obj)
                else:                self.attrs[tp] = to_ent_attr(tp, rel.obj)

        for d in ['or','and']:
            if self.attrs.get(d):
                del self.attrs[d]

    def _to_code(self, add_attrs=True):
        arg = '' 
        verb = self.verb
        if self.span_as_arg:
            arg = f'"{self.span}"'
        if self.val and self.verb:
            arg = self.val.upper().replace(' ','').replace('-','_')
            verb = self.verb
        elif not self.verb and self.val:
            verb = self.val
        return f'{verb}({arg})'

    def to_code(self, add_attrs=True):
        if self.executed:
            return ''
        self.executed = True
        return self._to_code()

    def ors(self):
        return [ x.obj for x in self.rels if x.type == 'Or' ]

    def ands(self):
        return [ x.obj for x in self.rels if x.type == 'And' ]

    def _get_rels(self, tp):
        return [ x.obj for x in self.rels if x.type == tp ]

    def _get_rels_of(self, tp):
        return [ x.subj for x in self.rels_of if x.type == tp ]

    def abbrevs(self): return self._get_rels_of('Abbrev-Of')
    def acuteness(self): return self._get_rels('Acuteness')
    def afters(self): return self._get_rels('After')
    def asserted(self): return self._get_rels_of('Asserted')
    def befores(self): return self._get_rels('Before')
    def caused_by(self): return self._get_rels('Caused-By')
    def classed(self): return self._get_rels('Class')
    def coded(self): return self._get_rels('Code')
    def contraindicates(self): return self._get_rels('Contraindicates')
    def contraindicated_by(self): return self._get_rels_of('Contraindicates')
    def criteria(self): return self._get_rels('Criteria')
    def doses(self): return self._get_rels('Dose')
    def durations(self): return self._get_rels('Duration')
    def durings(self): return self._get_rels('During')
    def equiv_of(self): return self._get_rels_of('Equivalent-To')
    def equiv_to(self): return self._get_rels('Equivalent-To')
    def examples(self): return self._get_rels_of('Example-Of')
    def exceptions(self): return self._get_rels('Except')
    def found_by(self): return self._get_rels('Found-By')
    def found(self): return self._get_rels_of('Found-By')
    def except_from(self): return self._get_rels('From')
    def has(self): return self._get_rels('Has')
    def if_thens(self): return self._get_rels('If-Then')
    def indications(self): return self._get_rels('Indication-For')
    def indicated_for(self): return self._get_rels_of('Indication-For')
    def is_other(self): return self._get_rels('Is-Other')
    def located(self): return self._get_rels('Location')
    def max_value(self): return self._get_rels('Max-Value')
    def min_value(self): return self._get_rels('Min-Value')
    def min_counts(self): return self._get_rels('Minimum-Count')
    def modified_by(self): 
        mods = self._get_rels_of('Modifies')
        for name_grp in [ name._get_rels_of('Modifies') for name in self.names() ]:
            for mod in name_grp:
                mods.append(mod)
        return mods
    def names(self): return self._get_rels('Name')
    def negates(self): return self._get_rels('Negates')
    def negated(self): return self._get_rels_of('Negates')
    def num_filters(self): return self._get_rels('Numeric-Filter')
    def operators(self): return self._get_rels('Operator')
    def others(self): return self._get_rels('Other')
    def per(self): return self._get_rels('Per')
    def polarities(self): return self._get_rels('Polarity')
    def providers(self): return self._get_rels('Provider')
    def refers_to(self): return self._get_rels('Refers-To')
    def risks_for(self): return self._get_rels('Risk-For')
    def severities(self): return self._get_rels('Severity')
    def specimens(self): return self._get_rels('Specimen')
    def stabilities(self): return self._get_rels('Stability')
    def stages(self): return self._get_rels('Stage')
    def studies_of(self): return self._get_rels('Study-Of')
    def temporal_periods(self): return self._get_rels('Temporal-Period')
    def temporal_recencies(self): return self._get_rels('Temporal-Recency')
    def temporal_units(self): return self._get_rels('Temporal-Unit')
    def temporal_filters(self): return self._get_rels('Temporality')
    def treated_by(self): return self._get_rels('Treatment-For')
    def type(self): return self._get_rels('Type')
    def units(self): return self._get_rels('Unit')
    def using(self): return self._get_rels('Using')
    def values(self): return self._get_rels('Value')

class NameEntity(Entity):
    def __init__(self, e, doc):
        super().__init__(e, doc)
        self.verb = None
        
    def to_code(self):
        if self.executed:
            return ''
        self.executed = True
        return f'"{self.span}"'

class HeadEntity(Entity):
    def __init__(self, e, doc):
        super().__init__(e, doc)
        self.doc = doc
        self.is_head = lambda: \
                       not any(self._get_rels('Example-Of')) and \
                       not any(self._get_rels('Abbrev-Of')) and \
                       not any(self._get_rels('Equivalent-To')) and \
                       not any(self._get_rels_of('Using')) and \
                       not any(self._get_rels('Treatment-For')) and \
                       not any(self._get_rels('Caused-By'))
        self.priority = 3
        self.verb = 'entity'
        self.span_as_arg = True
        self.text_transform = True

    def to_code(self):
        if self.executed:
            return ''
        self.executed = True
        return self._to_code()

    def _to_code(self, add_attrs=True):
        output = ''
        verb = (self.val if self.val else self.verb).replace('-','_')
        verb_arg = '' if not self.span_as_arg or not any([ x for x in self.attrs.items() if x[0] == 'name']) else f'"{self.span}"'

        output = f'{verb}({verb_arg})'
        if add_attrs:
            for verb, attr in sorted(self.attrs.items(), key=lambda x: x[1].get_min_char_beg_idx()):
                if verb == 'name':
                    continue

                if verb in {'before','during','after'}:
                    output = f'seq(anchor({output}), {verb}({attr.to_code()}))'
                else:
                    output += attr.to_code()
        
        return output

class Acuteness(Entity):
    def __init__(self, e, doc):
        super().__init__(e, doc)
        self.verb = self.val
        self.text_transform = True

    def _to_code(self, add_attrs=True):
        if self.val == 'acute':
            return 'acute()'
        return 'chronic()'

class Age(HeadEntity):
    def __init__(self, e, doc):
        super().__init__(e, doc)      
        self.verb = 'age'
        self.span_as_arg = False

class Allergy(HeadEntity):
    def __init__(self, e, doc):
        super().__init__(e, doc)    
        self.verb = 'allergy'

    def _to_code(self, add_attrs=True):
        return None

class AllergyName(Entity):
    def __init__(self, e, doc):
        super().__init__(e, doc)
        self.verb = 'allergy'

class Assertion(Entity):
    def __init__(self, e, doc):
        super().__init__(e, doc)
        self.verb = self.val
        self.text_transform = True

    def _to_code(self, add_attrs=True):
        if self.val == 'hypothetical':
            return 'hypoth()'
        if self.val == 'possible':
            return 'possible()'
        return 'intent()'

class Birth(HeadEntity):
    def __init__(self, e, doc):
        super().__init__(e, doc)
        self.verb = 'birth'

class Code(Entity):
    def __init__(self, e, doc):
        super().__init__(e, doc)
        self.verb = 'code'
        self.span_as_arg = True
        self.text_transform = True

class Condition(HeadEntity):
    def __init__(self, e, doc):
        super().__init__(e, doc)
        self.verb = 'cond'

class ConditionName(NameEntity):
    def __init__(self, e, doc):
        super().__init__(e, doc)

class ConditionType(Entity):
    def __init__(self, e, doc):
        super().__init__(e, doc)       
        self.verb = 'type'
        self.span_as_arg = True
        self.text_transform = True

class Contraindication(HeadEntity):
    def __init__(self, e, doc):
        super().__init__(e, doc)       

class CriteriaCount(HeadEntity):
    def __init__(self, e, doc):
        super().__init__(e, doc)    
        self.verb = 'criteria'

class Death(HeadEntity):
    def __init__(self, e, doc):
        super().__init__(e, doc)
        self.verb = 'death'
        self.span_as_arg = True

class Drug(HeadEntity):
    def __init__(self, e, doc):
        super().__init__(e, doc)
        self.verb = 'drug'

class DrugName(NameEntity):
    def __init__(self, e, doc):
        super().__init__(e, doc) 

class Encounter(HeadEntity):
    def __init__(self, e, doc):
        super().__init__(e, doc)
        self.verb = 'enc'

class EqComparison(Entity):
    def __init__(self, e, doc):
        super().__init__(e, doc)
        self.verb = 'eq'
        self.text_transform = True

    def _to_code(self, add_attrs=True):
        args = []
        for _, attr in self.attrs.items():
            for ent in attr.ents:
                args.append(ent)
        codes = [ x.to_code() for x in sorted(args, key=lambda y: y.tok_beg_idx) ]
        return f'{self.verb}({", ".join([ x for x in codes if x ])})'

    def to_code(self, add_attrs=True):
        return self._to_code()

class EqOperator(Entity):
    def __init__(self, e, doc):
        super().__init__(e, doc)
        self.verb = 'op'

class EqTemporalPeriod(Entity):
    def __init__(self, e, doc):
        super().__init__(e, doc)
        self.verb = 'temporal_per'

class EqTemporalRecency(Entity):
    def __init__(self, e, doc):
        super().__init__(e, doc)   
        self.verb = 'temporal_rec'

class EqTemporalUnit(Entity):
    def __init__(self, e, doc):
        super().__init__(e, doc)
        self.verb = 'temporal_unit'

    def to_code(self):
        if any([ x for x in self.rels_of if x.type.lower() == 'per' ]):
            return f'per({self.val.upper()})'
        return f'{self.verb}({self.val.upper()})'

class EqUnit(Entity):
    def __init__(self, e, doc):
        super().__init__(e, doc)
        self.verb = 'unit'
        self.span_as_arg = True

class EqValue(Entity):
    def __init__(self, e, doc):
        super().__init__(e, doc)
        self.verb = 'val'
        self.span_as_arg = True

class Ethnicity(HeadEntity):
    def __init__(self, e, doc):
        super().__init__(e, doc)     
        self.verb = 'ethnic'

class Exception(Entity):
    def __init__(self, e, doc):
        super().__init__(e, doc)
        self.verb = 'except'
        self.text_transform = True

class FamilyMember(HeadEntity):
    def __init__(self, e, doc):
        super().__init__(e, doc)
        self.verb = 'name'
        self.span_as_arg = self.val == None

class Immunization(HeadEntity):
    def __init__(self, e, doc):
        super().__init__(e, doc)    
        self.verb = 'immune'

class ImmunizationName(NameEntity):
    def __init__(self, e, doc):
        super().__init__(e, doc)

class Indication(HeadEntity):
    def __init__(self, e, doc):
        super().__init__(e, doc)    

class Insurance(Entity):
    def __init__(self, e, doc):
        super().__init__(e, doc) 
        self.verb = 'insur'
        self.span_as_arg = True

class Language(HeadEntity):
    def __init__(self, e, doc):
        super().__init__(e, doc)      
        self.verb = 'lang'
        self.span_as_arg = True

class LifeStageAndGender(HeadEntity):
    def __init__(self, e, doc):
        super().__init__(e, doc)  
        self.verb = 'life_gend'
        self.span_as_arg = False

class Location(Entity):
    def __init__(self, e, doc):
        super().__init__(e, doc)    
        self.verb = 'loc'
        self.span_as_arg = True

    def _to_code(self, add_attrs=True):
        if self.val:
            return f'loc({self.val}("{self.span}"))'
        return f'loc("{self.span}")'

class Modifier(Entity):
    def __init__(self, e, doc):
        super().__init__(e, doc)
        self.text_transform = True

    def _to_code(self, add_attrs=True):
        return f'"{self.span}"'

class Negation(HeadEntity):
    def __init__(self, e, doc):
        super().__init__(e, doc)
        self.priority = 1
        self.verb = 'neg'
        self.span_as_arg = False

class Observation(HeadEntity):
    def __init__(self, e, doc):
        super().__init__(e, doc)     
        if self.val:
            if self.val == 'survey_or_questionniare':
                self.verb = 'survey'
            elif self.val == 'measurement':
                self.verb = 'meas'
            elif self.val == 'clinical_score':
                self.verb = 'clin_score'
            else:
                self.verb = self.val
        else:
            self.verb = 'obs'

class ObservationName(NameEntity):
    def __init__(self, e, doc):
        super().__init__(e, doc)

class Organism(HeadEntity):
    def __init__(self, e, doc):
        super().__init__(e, doc)     
        self.verb = 'org'

class OrganismName(NameEntity):
    def __init__(self, e, doc):
        super().__init__(e, doc)

class Other(Entity):
    def __init__(self, e, doc):
        super().__init__(e, doc)    
        self.text_transform = True
        self.verb = 'other'

class Polarity(Entity):
    def __init__(self, e, doc):
        super().__init__(e, doc)    
        self.verb = 'pol'
        self.text_transform = True

class Procedure(HeadEntity):
    def __init__(self, e, doc):
        super().__init__(e, doc)       
        self.verb = 'proc'

class ProcedureName(NameEntity):
    def __init__(self, e, doc):
        super().__init__(e, doc)

class Provider(Entity):
    def __init__(self, e, doc):
        super().__init__(e, doc)        
        self.verb = 'prov'
        self.span_as_arg = True

class Risk(HeadEntity):
    def __init__(self, e, doc):
        super().__init__(e, doc)
        self.priority = 2
        self.verb = 'risk'

class Severity(Entity):
    def __init__(self, e, doc):
        super().__init__(e, doc)   
        self.verb = 'sev'             
        self.text_transform = True     

class Specimen(Entity):
    def __init__(self, e, doc):
        super().__init__(e, doc)         
        self.verb = 'spec'
        self.span_as_arg = True
        self.text_transform = True

class Stability(Entity):
    def __init__(self, e, doc):
        super().__init__(e, doc)         
        self.verb = 'stability'
        self.text_transform = True

    def _to_code(self, add_attrs=True):
        if self.val == 'change':
            return 'change()'
        return 'stable()'

class Study(Entity):
    def __init__(self, e, doc):
        super().__init__(e, doc)    
        self.verb = 'study'
        self.is_head = lambda: True
        self.priority = 4
        self.text_transform = True

class BaseEntity:
    def __init__(self, brat):
        if isinstance(brat, BratT):
            val = brat
            self.id = []
        elif isinstance(brat, BratE):
            val = brat.args[0].val
            self.id = [ brat.id ]

        self.id.append(val.id)
        self._brat  = val
        self.val    = None
        self.type   = val.type
        self.span   = val.span
        self.sent_idx     = val.sent_idx
        self.char_beg_idx = val.char_beg_idx
        self.char_end_idx = val.char_end_idx
        self.tok_beg_idx  = val.tok_beg_idx
        self.tok_end_idx  = val.tok_end_idx
        self.tok_idxs     = val.tok_idxs
        self.rels         = []
        self.rels_of      = []
        self.is_head      = lambda : False
        self.sent_char_beg_idx = -1
        self.sent_char_end_idx = -1
        self.class_map    = { 
                                'Acuteness': Acuteness,
                                'Age': Age,
                                'Allergy': Allergy,
                                'Allergy-Name': AllergyName,
                                'Assertion': Assertion,
                                'Birth': Birth,
                                'Code': Code,
                                'Condition': Condition,
                                'Condition-Name': ConditionName,
                                'Condition-Type': ConditionType,
                                'Contraindication': Contraindication,
                                'Criteria-Count': CriteriaCount,
                                'Death': Death,
                                'Drug': Drug,
                                'Drug-Name': DrugName,
                                'Encounter': Encounter,
                                'Eq-Comparison': EqComparison,
                                'Eq-Operator': EqOperator,
                                'Eq-Temporal-Period': EqTemporalPeriod,
                                'Eq-Temporal-Recency': EqTemporalRecency,
                                'Eq-Temporal-Unit': EqTemporalUnit,
                                'Eq-Unit': EqUnit,
                                'Eq-Value': EqValue,
                                'Ethnicity': Ethnicity,
                                'Exception': Exception,
                                'Family-Member': FamilyMember,
                                'Immunization': Immunization,
                                'Immunization-Name': ImmunizationName,
                                'Indication': Indication,
                                'Insurance': Insurance,
                                'Language': Language,
                                'Life-Stage-And-Gender': LifeStageAndGender,
                                'Location': Location,
                                'Modifier': Modifier,
                                'Negation': Negation,
                                'Observation': Observation,
                                'Observation-Name': ObservationName,
                                'Organism': Organism,
                                'Organism-Name': OrganismName,
                                'Other': Other,
                                'Polarity': Polarity,
                                'Procedure': Procedure,
                                'Procedure-Name': ProcedureName,
                                'Provider': Provider,
                                'Risk': Risk,
                                'Severity': Severity,
                                'Specimen': Specimen,
                                'Stability': Stability,
                                'Study': Study
                            }

    def to_precise(self, doc):
        if self.type in self.class_map:
            return self.class_map[self.type](self, doc)
        return None

class BaseRelation:
    def __init__(self, brat, arg1=None):
        self._brat = brat
        if isinstance(brat, BratR):
            self.id   = brat.id
            self.type = brat.type
            self.subj = brat.arg1.id
            self.obj  = brat.arg2.id
        elif isinstance(brat, BratEArgPair):
            self.id   = None
            self.type = brat.type
            self.subj = arg1.val.id
            self.obj  = brat.val.id

        if any(re.findall(regex_trailing_num, self.type)):
            self.type = re.sub(regex_trailing_num, '', self.type)

def get_disjoint_node_groups(ents, rels):
    rel_groups = get_disjoint_edge_sets(rels)
    ent_groups = [ ([], r) for r in rel_groups ]

    for e in [ x for x in ents if x.is_head() ]:
        ent_rels = e.rels + e.rels_of
        grouped = False

        for grp in ent_groups:
            if any([ r for r in ent_rels if r in grp[1] ]):
                grp[0].append(e)
                grouped = True
                break

        if not grouped:
            new_group = ([ e ], [])
            ent_groups.append(new_group)

    ent_groups = [ x[0] for x in ent_groups if any(x[0]) ]
    ent_groups = sorted(ent_groups, key=lambda x: min([y.tok_beg_idx for y in x]))

    ent_groups_by_line = []
    curr_group = []
    prev_line_idx = -1
    for grp in ent_groups:
        line_idx = min([ y.sent_idx for y in grp ])
        if line_idx != prev_line_idx and any(curr_group):
            ent_groups_by_line.append(curr_group)
            curr_group = [ grp ]
        else:
            curr_group.append(grp)
        prev_line_idx = line_idx
    if any(curr_group):
        ent_groups_by_line.append(curr_group)

    return ent_groups_by_line

def get_disjoint_edge_sets(rels):
    rel_groups = [[]]
    for rel in rels:
        grouped = False
        conns = get_connected_edges(rel, set())
        for grp in rel_groups:
            if any([ g for g in grp if g in conns ]):
                for conn in conns:
                    grp.add(conn)
                grouped = True
                break
        if not grouped:
            rel_groups.append(conns)

    return rel_groups

def get_connected_edges(rel, accum):
    subj_rels = rel.subj.rels + rel.subj.rels_of
    obj_rels  = rel.obj.rels + rel.obj.rels_of
    all_rels  = [ r for r in (subj_rels + obj_rels) if r not in accum ]

    if not any(all_rels):
        return accum

    new_accum = set(accum)
    new_accum.add(rel)
    for edge in all_rels:
        new_accum.add(edge)
    
    recurse = [ get_connected_edges(r, new_accum) for r in all_rels ]

    return set([ rel for rel_grp in recurse for rel in rel_grp ])

def get_connected_nodes(ent, accum, rel_type):
    connected = []
    for r in ent.rels:
        if r.type != rel_type or r.obj == ent or r.obj in accum or not r.obj.is_head():
            continue
        for obj in (r.obj.rels + r.obj.rels_of):
            if obj == ent or obj in accum or not obj.is_head():
                continue
            connected.append(obj)

    #connected = list(chain(*[ r.obj.rels + r.obj.rels_of for r in ent.rels if r.type == rel_type ]))
    #connected = [ r.obj for r in connected if r.type == rel_type and r.obj not in accum and r.obj != ent and r.obj.is_head() ]

    if not any(connected):
        return accum

    new_accum = set(accum)
    new_accum.add(ent)
    for e in connected:
        new_accum.add(e)

    recurse = [ get_connected_nodes(x, new_accum, rel_type) for x in connected ]

    return set(sorted([ x for grp in recurse for x in grp ], key=lambda x: x.char_beg_idx))

main()    