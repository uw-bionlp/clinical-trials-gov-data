import os
import sys
import re
from shutil import copyfile

cwd = os.getcwd()
in_dir = f'{cwd}{os.path.sep}entities{os.path.sep}auto'
out_dir = f'{cwd}{os.path.sep}logical_bounds{os.path.sep}auto'

regex_start_with_num = r'^[0-9]+\.'
regex_lines = r'\n'
regex_ors = r'( and/or | or/and | or )'
regex_patients = r'^(The individual|Individuals?|Patients?|The patients?|Patients who|Participants?|The participant|The participants?|Participants who|Subjects|The subject|Subjects who) '
regex_negation = r' ?(not |no |none)'

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

        if content[self.start:self.end] in [ ' and/or ', ' or/and ', ' or ' ]:
            self.start += 1
            self.end -= 1
        if content[self.start:self.end] == ", ":
            self.end -= 1

        self.text  = content[self.start:self.end]

def infer_criteria_bounds(content):
    inclusion_trig = 'inclusion criteria'
    exclusion_trig = 'exclusion criteria'
    inclusion_ann  = 'Inclusion'
    exclusion_ann  = 'Exclusion'
    or_ann         = 'Or'

    annotations = []
    category = inclusion_ann
    cnt = 1
    lines = []
    lines_ob = [ ParsedObject(x.start(), x.end(), i, content) for i,x in enumerate(re.finditer(regex_lines, content)) ]
    ors = [ ParsedObject(x.start(), x.end(), i, content) for i,x in enumerate(re.finditer(regex_ors, content)) ]

    begin_idx = 0
    for l in lines_ob:
        lines.append(ParsedObject(begin_idx, l.start, l.idx, content))
        begin_idx = l.end
    lines.append(ParsedObject(begin_idx, len(content), len(lines)-1, content))

    # for o in ors:
    #     matches = sorted([ l for l in lines if o.start > l.start and o.end < l.end ], key=lambda x: x.end)
    #     if any(matches):
    #         m = matches[0]
    #         lft = ParsedObject(m.start, o.start-1, m.idx, content)
    #         rgt = ParsedObject(o.end+1, m.end, m.idx+1, content)
    #         if o.text == ",":
    #             lft.end += 1
    #             lft.text = content[lft.start:lft.end]
    #         del lines[m.idx]
    #         lines.insert(lft.idx, lft)
    #         lines.insert(rgt.idx, rgt)
    #         for i,l in enumerate(lines):
    #             l.idx = i

    for l in lines:
        val = l.text
        if inclusion_trig in val.lower() or exclusion_trig in val.lower():
            if inclusion_trig in val.lower():
                category = inclusion_ann
            else:
                category = exclusion_ann
            continue
        if val.lower().strip() == 'none':
            continue
        if val.startswith('- '):
            val = val[len('- '):].strip()
        elif any(re.findall(regex_start_with_num, val)):
            val = re.sub(regex_start_with_num, '', val).strip()
        if len(val) > 1 and val[-1] in [ '.', ':', ',', ';' ]:
            val = val[:-1]
        # patients = re.search(regex_patients, val)
        # if patients:
        #     val = val[patients.end():]
        
        
        # Get bounds
        begin_idx = content.find(val)
        if begin_idx == -1:
            continue
        end_idx = begin_idx + len(val)

        # Check for preceding 'or'
        # if cnt > 1:
        #     prec_or = [ o for o in ors if o.start >= annotations[-1].end_idx and o.end < end_idx ]
        #     if any(prec_or):
        #         prec = prec_or[0]
        #         T = f'T{cnt}'
        #         E = f'E{cnt}'
        #         t_ann = Annotation(T, prec.start, prec.end, f'{T}\tOr {prec.start} {prec.end}\t{content[prec.start:prec.end]}')
        #         e_ann = Annotation(E, prec.start, prec.end, f'{E}\tOr:{T} Arg:T{cnt-1} Arg2:T{cnt+1}')
        #         if not any([ a for a in annotations if a.begin_idx == prec.start or a.end_idx == prec.end]):
        #             annotations.append(t_ann)
        #             annotations.append(e_ann)
        #             cnt += 1

        # Make brat row
        T = f'T{cnt}'
        cat = exclusion_ann if re.search(regex_negation, val, re.IGNORECASE) else category
        t_ann = Annotation(T, begin_idx, end_idx, f'{T}\t{cat} {begin_idx} {end_idx}\t{content[begin_idx:end_idx]}')
        if not any([ a for a in annotations if a.begin_idx == begin_idx or a.end_idx == end_idx]):
            annotations.append(t_ann)
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
            f_out_path = f'{batch_out_dir}{os.path.sep}{f}'
            a_out_path = f_out_path.replace(".txt",".ann")
            if not os.path.exists(batch_out_dir):
                os.makedirs(batch_out_dir)

            with open(f_path) as f:
                content = f.read()

            brat_rows = infer_criteria_bounds(content)
            with open(a_out_path, 'w+') as f:
                for row in brat_rows:
                    f.write(f'{row.val}\n')
            copyfile(f_path, f_out_path)

main()