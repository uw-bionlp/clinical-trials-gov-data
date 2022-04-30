from itertools import chain
import os
import re
import sys
import json
import numpy as np

sys.path.append(os.path.join(os.getcwd(), 'src'))

from preprocess.brat_document import BratDocument, BratE, BratEArgPair, BratR, BratT
from preprocess.config import Config
import preprocess.utils as utils

regex_trailing_num = r'\d'

def main():

    docs = get_base_data()
    output = []
    for doc in docs:
        try:
            for pair in doc.to_sequence():
                output.append(pair)
        except:
            pass
        print(len(output))
        if len(output) > 2000:
            break

    _, train, test = np.split(output, [ 0, int(.8*len(output))])

    with open(os.path.join('data', 'seq2seq', 'train.json'), 'w+') as fout:
        fout.write(json.dumps(list(train), indent=4))
    with open(os.path.join('data', 'seq2seq', 'test.json'), 'w+') as fout:
        fout.write(json.dumps(list(test), indent=4))

def get_base_data():
    
    skip = set([ 'NCT03866512', 'NCT03863912', 'NCT03869684', 'NCT03867864', 'NCT03869164' ])

    brat_train_raw = {} 
    for d in Config.annotation_train_dirs:
        brat_train_raw = {**brat_train_raw, **utils.fetch_brat_files(d)}
        #break
    annotations = [ BratDocument(k, v[0], v[1], v[2]) for k,v in brat_train_raw.items() ]
    docs   = [ BaseDoc(a) for a in annotations if a.doc_id not in skip ]

    return docs

class BaseDoc:
    def __init__(self, ann):
        self.doc_id = ann.doc_id
        self.path   = ann.path
        self.text   = ann.raw_text
        self.lines  = ann.raw_text.split('\n')
        self.derive_ents_and_rels(ann)
        self.node_groups = get_disjoint_node_groups(self.ents, self.rels)

    def to_sequence(self):
        output = []
        seen = set()
        print(f'{self.doc_id}')
        for line in self.node_groups:
            line_text = self.lines[[ grp[0] for grp in line ][0].sent_idx]
            #print(f'"{line_text}"')
            codes = []
            for grp in line:
                ordered = sorted(sorted(grp, key=lambda x: x.tok_beg_idx), key=lambda x: x.priority)
                for node in ordered:
                    if node in seen or not node.is_valid:
                        continue
                    code, used = node.to_code(), node.get_deps()
                    codes.append(code)
                    for ent in used:
                        seen.add(ent)
                    #print('\n' + code)
            if len(line_text) < 150 and any(codes):
                code = f'or({", ".join(codes)})' if len(codes) > 1 else codes[0]
                output.append({ "intent": line_text.strip(), "snippet": code.replace('\n','').replace('"',"'") })
            #print()
        return output

    def derive_ents_and_rels(self, ann):

        ents_t = [ BaseEntity(x)   for _, x in ann.Ts.items() ]
        ents_e = [ BaseEntity(x)   for _, x in ann.Es.items() ]
        rels_r = [ BaseRelation(x) for _, x in ann.Rs.items() ]
        rels_e = []
        for _, e in ann.Es.items():
            arg1 = e.args[0]
            rels_e += [ BaseRelation(arg2, arg1) for arg2 in e.args[1:] ]

        ents = ents_e + [ t for t in ents_t if not any([ e for e in ents_e if t.type == e.type and t.tok_idxs == e.tok_idxs ]) ]
        ents = [ x.to_precise() for x in ents if x.to_precise() is not None ]
        rels = rels_r + rels_e
        
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

        for _, a in ann.As.items():
            e = [ x for x in ents if a.attr_of.id in x.id ]
            if any(e):
                e[0].val = a.val
        
        self.ents = ents
        self.rels = [ x for i, x in enumerate(rels) if i not in to_del and x.subj.sent_idx == x.obj.sent_idx ]

class Entity:
    def __init__(self, e):
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
        self.is_valid     = True
        self.deps         = []
        self.span_as_arg  = False

        for rel in e.rels:
            rel.subj = self
        for rel in e.rels_of:   
            rel.obj = self

    def to_code(self, check_conjunctives=True):
        arg = '' 
        verb = self.verb
        if self.span_as_arg:
            arg = f'"{self.span}"'
        if self.val and self.verb:
            arg = self.val.upper()
            verb = self.verb
        elif not self.verb and self.val:
            verb = self.val
        return f'{verb}({arg})'

    def get_deps(self):
        return []

    def invalidate_siblings(self):
        get_connected_nodes(self, set(), 'Or', invalidate_matches=True)
        get_connected_nodes(self, set(), 'And', invalidate_matches=True)

    def ors(self):
        return [ x for x in (self.rels + self.rels_of) if x.type == 'Or' ]

    def ands(self):
        return [ x for x in (self.rels + self.rels_of) if x.type == 'And' ]

    def _get_rels(self, tp):
        rels = [ x for x in self.rels if x.type == tp and x.obj.is_valid ]
        for rel in rels: rel.obj.invalidate_siblings()

        return [ x.obj for x in rels if x.obj.is_valid ]

    def _get_rels_of(self, tp):
        return [ x.subj for x in self.rels_of if x.type == tp and x.subj.is_valid ]

    def _args_to_str_if_not_none(self, args, check_conjunctives=True):
        return ', '.join([ x if isinstance(x, str) else x.to_code(check_conjunctives) for x in args if x ])

    def _chained_methods_to_str_if_not_none(self, method_strs):
        if any(method_strs):
            return '.' + '.'.join([ x for x in method_strs if x ])
        return ''

    def _get_rels_as_func(self, func, verb, add_newline=False):
        ents = func()
        #ents += list(chain(*[ x.get_deps() for x in ents ]))

        nl = '\n' if add_newline else ''
        if any(ents):
            return f'{verb}({nl}{self._args_to_str_if_not_none(ents)}{nl})', ents
        return '', ents

    def get_func_usings(self): return self._get_rels_as_func(self.using, 'using', add_newline=True)
    def get_func_abbrevs(self): return self._get_rels_as_func(self.abbrevs, 'abbrev')
    def get_func_examples(self): return self._get_rels_as_func(self.examples, 'example')
    def get_func_befores(self): return self._get_rels_as_func(self.befores, 'before', add_newline=True)
    def get_func_durings(self): return self._get_rels_as_func(self.durings, 'during', add_newline=True)
    def get_func_afters(self): return self._get_rels_as_func(self.afters, 'after', add_newline=True)
    def get_func_equivs(self): return self._get_rels_as_func(self.equiv_of, 'equiv', add_newline=True)
    def get_func_num_filters(self): return self._get_rels_as_func(self.num_filters, 'num_filter')
    def get_func_temporal_filters(self): return self._get_rels_as_func(self.temporal_filters, 'temporal_filter')
    def get_func_durations(self): return self._get_rels_as_func(self.durations, 'duration')

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


class HeadEntity(Entity):
    def __init__(self, e):
        super().__init__(e)
        self.is_head = lambda: \
                       not any(self._get_rels('Example-Of')) and \
                       not any(self._get_rels('Abbrev-Of')) and \
                       not any(self._get_rels('Equivalent-To'))
        self.priority = 3
        self.verb = 'entity'

    def get_deps(self):
        return self.deps

    def to_code(self, check_conjunctives=True):
        methods = self.names() + self.located() + self.asserted() + \
               self.polarities() + self.caused_by() + self.if_thens() + \
               self.stages() + self.exceptions() + self.examples() + \
               self.modified_by() + self.severities() + self.found_by() + \
               self.min_counts() + self.providers() + self.negates() + \
               self.except_from() + self.type() + self.min_counts() + \
               self.criteria()

        if check_conjunctives:
            try:
                ors  = get_connected_nodes(self, set(), 'Or', invalidate_matches=True)
                ands = get_connected_nodes(self, set(), 'And', invalidate_matches=True)
            except:
                ors = []
                ands = []
        else:
            ors  = []
            ands = []
        method_strs = [ x.to_code() for x in methods if x.is_valid ]
        method_deps = list(chain(*[ x.get_deps() for x in methods ]))
        examples, example_deps = self.get_func_examples()
        abbrevs, abbrev_deps = self.get_func_abbrevs()
        usings, using_deps = self.get_func_usings()
        equiv, equiv_deps = self.get_func_equivs()
        num_filters, num_filter_deps = self.get_func_num_filters()
        temp_filters, temp_filter_deps = self.get_func_temporal_filters()
        durations, duration_deps = self.get_func_durations()
        befores, before_deps = self.get_func_befores()
        durings, during_deps = self.get_func_durings()
        afters, after_deps = self.get_func_afters()

        self.deps = methods + method_deps + using_deps + equiv_deps + num_filter_deps + temp_filter_deps + duration_deps + \
                    before_deps + during_deps + after_deps + example_deps + abbrev_deps
        self.deps += list(chain(*[ x.get_deps() for x in self.deps ]))

        method_strs += [ equiv, num_filters, temp_filters, durations, usings, befores, durings, afters, examples, abbrevs ]
        verb = (self.val if self.val else self.verb).replace('-','_')
        verb_arg = '' if not self.span_as_arg else f'"{self.span}"'
        self_output = f'{verb}({verb_arg})' + self._chained_methods_to_str_if_not_none(method_strs)

        wrapper = ''
        use_wrapper = False
        for verb, iter in [[ 'intersect', list(ands) ], [ 'union', list(ors) ]]:
            if any(iter):
                if not use_wrapper:
                    iter.insert(0, self_output)
                    use_wrapper = True
                wrapper += f'{verb}(\n{self._args_to_str_if_not_none(iter, False)}\n)'

        if not use_wrapper:
            return self_output
        return wrapper

class Acuteness(Entity):
    def __init__(self, e):
        super().__init__(e)
        self.verb = self.val

class Age(HeadEntity):
    def __init__(self, e):
        super().__init__(e)      
        self.verb = 'age'

class Allergy(HeadEntity):
    def __init__(self, e):
        super().__init__(e)    
        self.verb = 'allergy'

class AllergyName(Entity):
    def __init__(self, e):
        super().__init__(e)
        self.verb = 'name'
        self.span_as_arg = True

class Assertion(Entity):
    def __init__(self, e):
        super().__init__(e)
        self.verb = self.val

class Birth(HeadEntity):
    def __init__(self, e):
        super().__init__(e)
        self.verb = 'birth'

class Code(Entity):
    def __init__(self, e):
        super().__init__(e)
        self.verb = 'code'
        self.span_as_arg = True

class Condition(HeadEntity):
    def __init__(self, e):
        super().__init__(e)
        self.verb = 'cond'

class ConditionName(Entity):
    def __init__(self, e):
        super().__init__(e)
        self.verb = 'name'
        self.span_as_arg = True

class ConditionType(Entity):
    def __init__(self, e):
        super().__init__(e)       
        self.verb = 'type'
        self.span_as_arg = True

class Contraindication(HeadEntity):
    def __init__(self, e):
        super().__init__(e)       

    def get_deps(self):
        deps = self.contraindicates()
        return deps

    def to_code(self, check_conjunctives=True):
        contraindicated = self.contraindicates()
        return f'contraind("{self._args_to_str_if_not_none(contraindicated)}")'

class CriteriaCount(HeadEntity):
    def __init__(self, e):
        super().__init__(e)    
        self.verb = 'criteria'

class Death(HeadEntity):
    def __init__(self, e):
        super().__init__(e)
        self.verb = 'death'
        self.span_as_arg = True

class Drug(HeadEntity):
    def __init__(self, e):
        super().__init__(e)
        self.verb = 'drug'

class DrugName(Entity):
    def __init__(self, e):
        super().__init__(e)        
        self.verb = 'name'
        self.span_as_arg = True

class Encounter(HeadEntity):
    def __init__(self, e):
        super().__init__(e)
        self.verb = 'enc'

class EqComparison(Entity):
    def __init__(self, e):
        super().__init__(e)
        self.verb = 'eq'

    def get_deps(self):
        return self.deps

    def to_code(self, check_conjunctives=True):
        methods = self.operators() + self.values() + self.units() + self.temporal_units() + \
                  self.temporal_recencies() + self.temporal_periods() + self.per()

        if check_conjunctives:
            ors  = get_connected_nodes(self, set(), 'Or', invalidate_matches=True)
            ands = get_connected_nodes(self, set(), 'And', invalidate_matches=True)
        else:
            ors  = []
            ands = []
        method_strs = [ x.to_code() for x in methods if x.is_valid ]
        equiv, equiv_deps = self.get_func_equivs()
        befores, before_deps = self.get_func_befores()
        durings, during_deps = self.get_func_durings()
        afters, after_deps = self.get_func_afters()

        self.deps = methods + equiv_deps + before_deps + during_deps + after_deps

        method_strs += [ equiv, befores, durings, afters ]
        verb = (self.val if self.val else self.verb).replace('-','_')
        verb_arg = '' if not self.span_as_arg else f'"{self.span}"'
        self_output = f'{verb}({verb_arg})' + self._chained_methods_to_str_if_not_none(method_strs)

        wrapper = ''
        use_wrapper = False
        for verb, iter in [[ 'intersect', list(ands) ], [ 'union', list(ors) ]]:
            if any(iter):
                if not use_wrapper:
                    iter.insert(0, self_output)
                    use_wrapper = True
                wrapper += f'{verb}(\n{self._args_to_str_if_not_none(iter, False)}\n)'

        if not use_wrapper:
            return self_output
        return wrapper

class EqOperator(Entity):
    def __init__(self, e):
        super().__init__(e)
        self.verb = 'op'

class EqTemporalPeriod(Entity):
    def __init__(self, e):
        super().__init__(e)
        self.verb = 'temporal_per'

class EqTemporalRecency(Entity):
    def __init__(self, e):
        super().__init__(e)   
        self.verb = 'temporal_rec'

class EqTemporalUnit(Entity):
    def __init__(self, e):
        super().__init__(e)
        self.verb = 'temporal_unit'

class EqUnit(Entity):
    def __init__(self, e):
        super().__init__(e)
        self.verb = 'unit'

class EqValue(Entity):
    def __init__(self, e):
        super().__init__(e)
        self.verb = 'val'
        self.span_as_arg = True

class Ethnicity(HeadEntity):
    def __init__(self, e):
        super().__init__(e)     
        self.verb = 'ethnic'

class Exception(Entity):
    def __init__(self, e):
        super().__init__(e)
        self.verb = 'except'
        self.span_as_arg = True

class FamilyMember(HeadEntity):
    def __init__(self, e):
        super().__init__(e)
        self.verb = 'name'
        self.span_as_arg = self.val == None

class Immunization(HeadEntity):
    def __init__(self, e):
        super().__init__(e)    
        self.verb = 'immune'

class ImmunizationName(Entity):
    def __init__(self, e):
        super().__init__(e)      
        self.verb = 'name'
        self.span_as_arg = True

class Indication(HeadEntity):
    def __init__(self, e):
        super().__init__(e)    

    def get_deps(self):
        return self.indications()

    def to_code(self, check_conjunctives=True):
        indic = self.indications()
        return f'indic("{self._args_to_str_if_not_none(indic)}")'

class Insurance(Entity):
    def __init__(self, e):
        super().__init__(e) 
        self.verb = 'insur'
        self.span_as_arg = True

class Language(HeadEntity):
    def __init__(self, e):
        super().__init__(e)      
        self.verb = 'lang'
        self.span_as_arg = True

class LifeStageAndGender(HeadEntity):
    def __init__(self, e):
        super().__init__(e)  
        self.verb = 'life_gend'

class Location(Entity):
    def __init__(self, e):
        super().__init__(e)    
        self.verb = 'loc' if not self.val else self.val
        self.span_as_arg = True

class Modifier(Entity):
    def __init__(self, e):
        super().__init__(e)      
        self.verb = 'mod'
        self.span_as_arg = True      

class Negation(HeadEntity):
    def __init__(self, e):
        super().__init__(e)
        self.priority = 1
        self.verb = 'neg'

class Observation(HeadEntity):
    def __init__(self, e):
        super().__init__(e)     
        self.verb = 'observ'

class ObservationName(Entity):
    def __init__(self, e):
        super().__init__(e) 
        self.verb = 'name'
        self.span_as_arg = True

class Organism(HeadEntity):
    def __init__(self, e):
        super().__init__(e)     
        self.verb = 'org'

class OrganismName(Entity):
    def __init__(self, e):
        super().__init__(e)
        self.verb = 'name'
        self.span_as_arg = True

class Other(Entity):
    def __init__(self, e):
        super().__init__(e)    

    def get_deps(self):
        return self.others()

    def to_code(self, check_conjunctives=True):
        others = self.others()
        return f'other("{self._args_to_str_if_not_none(others)}")'

class Polarity(Entity):
    def __init__(self, e):
        super().__init__(e)    
        self.verb = 'pol'

class Procedure(HeadEntity):
    def __init__(self, e):
        super().__init__(e)       
        self.verb = 'proc'

class ProcedureName(Entity):
    def __init__(self, e):
        super().__init__(e)      
        self.verb = 'name'
        self.span_as_arg = True

class Provider(Entity):
    def __init__(self, e):
        super().__init__(e)        
        self.verb = 'prov'
        self.span_as_arg = True

class Risk(HeadEntity):
    def __init__(self, e):
        super().__init__(e)
        self.priority = 2

    def get_deps(self):
        return self.risks_for()

    def to_code(self, check_conjunctives=True):
        risks_for = self.risks_for()
        return f'risk({risks_for})'

class Severity(Entity):
    def __init__(self, e):
        super().__init__(e)   
        self.verb = 'sev'                          

class Specimen(Entity):
    def __init__(self, e):
        super().__init__(e)         
        self.verb = 'spec'
        self.span_as_arg = True

class Stability(Entity):
    def __init__(self, e):
        super().__init__(e)         
        self.verb = 'stability'

class Study(Entity):
    def __init__(self, e):
        super().__init__(e)    
        self.verb = 'study'

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

    def to_precise(self):
        if self.type in self.class_map:
            return self.class_map[self.type](self)
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

def get_connected_nodes(ent, accum, rel_type, invalidate_matches=False):
    try:
        connected = list(chain(*[ r.obj.rels + r.obj.rels_of for r in ent.rels if r.type == rel_type ]))
        connected = [ r.obj for r in connected if r.type == rel_type and r.obj not in accum and r.obj != ent and r.obj.is_head() ]
    except:
        return accum

    if invalidate_matches:
        for ent in connected:
            ent.is_valid = False

    if not any(connected):
        return accum

    new_accum = set(accum)
    new_accum.add(ent)
    for e in connected:
        new_accum.add(e)

    recurse = [ get_connected_nodes(x, new_accum, rel_type, invalidate_matches) for x in connected ]

    return set(sorted([ x for grp in recurse for x in grp ], key=lambda x: x.char_beg_idx))

main()    