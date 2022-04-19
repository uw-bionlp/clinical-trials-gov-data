import os
import re
import sys

sys.path.append(os.path.join(os.getcwd(), 'src'))

from preprocess.brat_document import BratDocument, BratE, BratEArgPair, BratR, BratT
from preprocess.config import Config
import preprocess.utils as utils


def main():

    base_docs = get_base_data()
    x=1

def get_base_data():
    
    brat_train_raw = {} 
    for d in Config.annotation_train_dirs:
        brat_train_raw = {**brat_train_raw, **utils.fetch_brat_files(d)}
        break
    annotations = [ BratDocument(k, v[0], v[1], v[2]) for k,v in brat_train_raw.items() ]
    base_docs   = [ BaseDoc(a) for a in annotations ]

    return base_docs

class BaseDoc:
    def __init__(self, ann):
        self.doc_id = ann.doc_id
        self.path   = ann.path
        self.text   = ann.raw_text
        self.lines  = ann.raw_text.split('\n')
        self.derive_ents_and_rels(ann)
        self.node_groups = get_disjoint_node_groups(self.ents, self.rels)
        self.to_sequence()

    def to_sequence(self):
        seen = set()
        for line in self.node_groups:
            line_text = self.lines[[ grp[0] for grp in line ][0].sent_idx]
            print(f'    "{line_text}"')
            for grp in line:
                ordered = sorted(grp, key=lambda x: x.priority)
                for node in ordered:
                    print(f'        {str(node)}')
            print()

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
        self.is_head      = False
        self.priority     = None

        for rel in e.rels:
            rel.subj = self
        for rel in e.rels_of:   
            rel.obj = self

    def ors(self):
        return [ x for x in (self.rels + self.rels_of) if x.type == 'Or' ]

    def ands(self):
        return [ x for x in (self.rels + self.rels_of) if x.type == 'And' ]

    def _get_rels(self, tp):
        return [ x.obj for x in self.rels if x.type == tp ]

    def _get_rels_of(self, tp):
        return [ x.subj for x in self.rels_of if x.type == tp ]

    def _args_to_str_if_not_none(self, args, joiner=', '):
        return joiner.join([ str(x) for x in args if x ])

    def abbrevs(self): return self._get_rels('Abbrev-Of')
    def acuteness(self): return self._get_rels('Acuteness')
    def after(self): return self._get_rels('After')
    def asserted(self): return self._get_rels('Asserted')
    def before(self): return self._get_rels('Before')
    def caused_by(self): return self._get_rels('Caused-By')
    def classed(self): return self._get_rels('Class')
    def coded(self): return self._get_rels('Code')
    def contraindicates(self): return self._get_rels('Contraindicates')
    def contraindicated_by(self): return self._get_rels_of('Contraindicates')
    def criteria(self): return self._get_rels('Criteria')
    def doses(self): return self._get_rels('Dose')
    def durations(self): return self._get_rels('Duration')
    def during(self): return self._get_rels('During')
    def equiv_to(self): return self._get_rels('Equivalent-To')
    def examples(self): return self._get_rels_of('Example-Of')
    def exceptions(self): return self._get_rels('Except')
    def found_by(self): return self._get_rels('Found-By')
    def expect_from(self): return self._get_rels('From')
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
        self.is_head = not any(self._get_rels('Example-Of')) and \
                       not any(self._get_rels('Abbrev-Of'))
        self.priority = 3

class Acuteness(Entity):
    def __init__(self, e):
        super().__init__(e)     

    def __str__(self) -> str:
        return f'{self.val}("{self.span}")'

class Age(HeadEntity):
    def __init__(self, e):
        super().__init__(e)      

    def __str__(self) -> str:
        nf = self.num_filters()
        if any(nf):
            nf = nf[0] if len(nf) == 1 else f"or({','.join(self._args_to_str_if_not_none(nf))})"
            return f'age().num_filter({str(nf)})'
        return None

class Allergy(HeadEntity):
    def __init__(self, e):
        super().__init__(e)    

    def __str__(self) -> str:
        args = self.names() + self.temporal_filters() + self.located() + \
               self.polarities() + self.caused_by() + self.if_thens() + \
               self.stages() + self.exceptions() + self.examples() + self.abbrevs() + \
               self.modified_by() + self.severities() + self.durations() + \
               self.min_counts() + self.providers() + self.equiv_to()

        return f'allergy()' + ".".join(self._args_to_str_if_not_none(args))

class AllergyName(Entity):
    def __init__(self, e):
        super().__init__(e)          

    def __str__(self):
        return f'name("{self.span}")'

class Assertion(Entity):
    def __init__(self, e):
        super().__init__(e)     

    def __str__(self):
        return f'{self.val}()'

class Birth(HeadEntity):
    def __init__(self, e):
        super().__init__(e)   

    def __str__(self):
        return 'birth()' 

class Code(Entity):
    def __init__(self, e):
        super().__init__(e)

    def __str__(self):
        return f'code("{self.span}")' 

class Condition(HeadEntity):
    def __init__(self, e):
        super().__init__(e)

    def __str__(self):
        args = self.names() + self.temporal_filters() + self.located() + \
               self.polarities() + self.caused_by() + self.if_thens() + \
               self.stages() + self.exceptions() + self.examples() + self.abbrevs() + \
               self.modified_by() + self.severities() + self.durations() + \
               self.min_counts() + self.providers() + self.equiv_to()

        more = self._args_to_str_if_not_none(args, '.') 
        return f'cond(){"." if any(more) else ""}{more}'

class ConditionName(Entity):
    def __init__(self, e):
        super().__init__(e)

    def __str__(self):
        return f'name("{self.span}")' 

class ConditionType(Entity):
    def __init__(self, e):
        super().__init__(e)       

    def __str__(self):
        return f'type("{self.span}")'  

class Contraindication(HeadEntity):
    def __init__(self, e):
        super().__init__(e)       

    def __str__(self):
        return f'contraind("{self._args_to_str_if_not_none(self.contraindicates())}")' 

class CriteriaCount(HeadEntity):
    def __init__(self, e):
        super().__init__(e)       

    def __str__(self):
        min_cnt = f'min_cnt({self.min_counts()[0]})'
        return f'criteria({min_cnt},{",".join(self._args_to_str_if_not_none(self.criteria()))})' 

class Death(HeadEntity):
    def __init__(self, e):
        super().__init__(e)     

    def __str__(self):
        return 'death()'

class Drug(HeadEntity):
    def __init__(self, e):
        super().__init__(e)

    def __str__(self):
        args = self.names() + self.temporal_filters() + self.located() + \
               self.if_thens() + self.doses() + self.min_counts() + \
               self.exceptions() + self.examples() + self.abbrevs() + \
               self.modified_by() + self.durations() + self.providers() + \
               self.equiv_to()

        more = self._args_to_str_if_not_none(args, '.') 
        return f'drug(){"." if any(more) else ""}{more}'

class DrugName(Entity):
    def __init__(self, e):
        super().__init__(e)        

    def __str__(self):
        return f'name("{self.span}")' 

class Encounter(HeadEntity):
    def __init__(self, e):
        super().__init__(e)

class EqComparison(Entity):
    def __init__(self, e):
        super().__init__(e)

    def __str__(self):
        args = self.operators() + self.values() + self.units() + self.temporal_units() + \
               self.temporal_recencies() + self.temporal_periods() + self.per() 
            
        return f'eq({self._args_to_str_if_not_none(args)})'

class EqOperator(Entity):
    def __init__(self, e):
        super().__init__(e)  

    def __str__(self):
        return f'op({self.val})'

class EqTemporalPeriod(Entity):
    def __init__(self, e):
        super().__init__(e)

    def __str__(self):
        return f'temporal_per({self.val})'

class EqTemporalRecency(Entity):
    def __init__(self, e):
        super().__init__(e)   

    def __str__(self):
        return f'temporal_rec({self.val})'

class EqTemporalUnit(Entity):
    def __init__(self, e):
        super().__init__(e)    

    def __str__(self):
        return f'temporal_unit({self.val})'

class EqUnit(Entity):
    def __init__(self, e):
        super().__init__(e)        

    def __str__(self):
        return f'unit("{self.span}")'

class EqValue(Entity):
    def __init__(self, e):
        super().__init__(e)             
    
    def __str__(self):
        return f'val("{self.span}")'

class Ethnicity(HeadEntity):
    def __init__(self, e):
        super().__init__(e)     

    def __str__(self):
        return f'ethnic("{self.span}")'

class Exception(Entity):
    def __init__(self, e):
        super().__init__(e)   

    def __str__(self):
        return f'except("{self.span}")'

class FamilyMember(HeadEntity):
    def __init__(self, e):
        super().__init__(e)     

    def __str__(self):
        if self.val:
            return f'fam({self.val})'
        return f'fam("{self.span}")'

class Immunization(HeadEntity):
    def __init__(self, e):
        super().__init__(e)    

class ImmunizationName(Entity):
    def __init__(self, e):
        super().__init__(e)      

    def __str__(self):
        return f'name("{self.span}")' 

class Indication(HeadEntity):
    def __init__(self, e):
        super().__init__(e)    

    def __str__(self):
        return f'indic("{self._args_to_str_if_not_none(self.indications)}")' 

class Insurance(Entity):
    def __init__(self, e):
        super().__init__(e) 

    def __str__(self):
        return f'insur("{self.span}")' 

class Language(HeadEntity):
    def __init__(self, e):
        super().__init__(e)      

    def __str__(self):
        return f'lang("{self.span}")' 

class LifeStageAndGender(HeadEntity):
    def __init__(self, e):
        super().__init__(e)       

    def __str__(self):
        return f'life_gend({self.val})' 

class Location(Entity):
    def __init__(self, e):
        super().__init__(e)    

    def __str__(self):
        if self.val:
            return f'{self.val}("{self.span}")'
        return f'loc("{self.span}")'

class Modifier(Entity):
    def __init__(self, e):
        super().__init__(e)      

    def __str__(self):
        return f'mod("{self.span}")'                  

class Negation(HeadEntity):
    def __init__(self, e):
        super().__init__(e)
        self.priority = 1

    def __str__(self):
        neg = self.negates()
        neg = str(neg[0]) if len(neg) == 1 else f"and({','.join(self._args_to_str_if_not_none(neg))})"
        return f'not("{neg}")'  

class Observation(HeadEntity):
    def __init__(self, e):
        super().__init__(e)     

    def __str__(self):  
        verb = self.val if self.val else 'observ'
        args = self.names() + self.temporal_filters() + self.located() + \
               self.polarities() + self.caused_by() + self.if_thens() + \
               self.stages() + self.exceptions() + self.examples() + self.abbrevs() + \
               self.modified_by() + self.severities() + self.durations() + \
               self.min_counts() + self.providers() + self.equiv_to()

        return f'{verb}().' + self._args_to_str_if_not_none(args, '.') 

class ObservationName(Entity):
    def __init__(self, e):
        super().__init__(e) 

    def __str__(self):
        return f'name("{self.span}")' 

class Organism(HeadEntity):
    def __init__(self, e):
        super().__init__(e)     

class OrganismName(Entity):
    def __init__(self, e):
        super().__init__(e)

    def __str__(self):
        return f'name("{self.span}")'   

class Other(Entity):
    def __init__(self, e):
        super().__init__(e)    

    def __str__(self):
        return f'other("{self._args_to_str_if_not_none(self.others)}")'   

class Polarity(Entity):
    def __init__(self, e):
        super().__init__(e)    

    def __str__(self):
        return f'pol({self.val})' 

class Procedure(HeadEntity):
    def __init__(self, e):
        super().__init__(e)       

    def __str__(self):
        args = self.names() + self.temporal_filters() + self.located() + \
               self.polarities() + self.caused_by() + self.if_thens() + \
               self.stages() + self.exceptions() + self.examples() + self.abbrevs() + \
               self.modified_by() + self.severities() + self.durations() + \
               self.min_counts() + self.providers() + self.equiv_to()

        more = self._args_to_str_if_not_none(args, '.') 
        return f'proc(){"." if any(more) else ""}{more}'

class ProcedureName(Entity):
    def __init__(self, e):
        super().__init__(e)      

    def __str__(self):
        return f'name("{self.span}")'          

class Provider(Entity):
    def __init__(self, e):
        super().__init__(e)        

    def __str__(self):  
        return f'prov("{self.span}")'             

class Risk(HeadEntity):
    def __init__(self, e):
        super().__init__(e)
        self.priority = 2

    def __str__(self):
        risks_for = self.negates()
        risks_for = str(risks_for[0]) if len(risks_for) == 1 else f"or({self._args_to_str_if_not_none(risks_for)})"
        return f'risk({risks_for})'  

class Severity(Entity):
    def __init__(self, e):
        super().__init__(e)   

    def __str__(self):
        return f'sev({self.val})'                                                                        

class Specimen(Entity):
    def __init__(self, e):
        super().__init__(e)         

    def __str__(self):
        return f'specimen("{self.span}")'  

class Stability(Entity):
    def __init__(self, e):
        super().__init__(e)         

    def __str__(self):
        return f'{self.val}()'          

class Study(Entity):
    def __init__(self, e):
        super().__init__(e)    

    def __str__(self):
        return f'study()' 

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
        self.is_head      = False
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

def get_disjoint_node_groups(ents, rels):
    rel_groups = get_disjoint_edge_sets(rels)
    ent_groups = [ ([], r) for r in rel_groups ]

    for e in [ x for x in ents if x.is_head ]:
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
            curr_group = []
        else:
            curr_group.append(grp)
        prev_line_idx = grp
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

main()    