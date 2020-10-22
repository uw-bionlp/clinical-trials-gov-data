import os
import re
import json
import shutil
from xml.dom import minidom
from dateutil.parser import parse as parse_date

EMPTY = ''
SPACE = ' '
NEWLINE = '\n'
REGEX_UNNECESSARY_NEWLINE = r'(?<=[a-zA-Z ,.])([\r\n])(?!([0-9-]|Inclusion|Exclusion))'
REGEX_UNNECESSARY_NEWLINE2 = r'[a-zA-Z0-9,.\(\)]+\n +[a-zA-Z,.\(\)]'

REGEX_BAD_NEWLINE1 = r'(<|>|<=|>=)\n\d+(\.\d{1,2})? '
REGEX_BAD_NEWLINE2 = r'([a-zA-Z]+\n[0-9]+\.?)\n'
REGEX_BAD_NEWLINE3 = r'[0-9]+\n[a-z]+'
REGEX_BAD_NEWLINE4 = r';\n\(\d\)'
REGEX_BAD_NEWLINE5 = r'[a-zA-Z]+\n[0-9]+(\s|\.[0-9])'
REGEX_BAD_NEWLINES = [ REGEX_BAD_NEWLINE1, REGEX_BAD_NEWLINE2, REGEX_BAD_NEWLINE3, REGEX_BAD_NEWLINE4, REGEX_BAD_NEWLINE5 ]

REGEX_ICD10 = r'ICD-?10'
REGEX_CPT = r'CPT'
REGEX_IMMUNE = r'(immuni|vaccin)'
REGEX_LOW = r'( low |reduced|decreased)'
REGEX_MOST_RECENT = r'(most recent|last )'
REGEX_NEGATIVE = r'negative'
REGEX_REACTIVE = r'reactive'

MIN_LEN = 75
MAX_LEN = 2000

def prep_dir(path):
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path)

def strip_inner(text, start, end):
    i = 0
    space_start = -1
    inner = text[start:end]

    while i < len(inner):
        char = inner[i]
        if char in [ SPACE, NEWLINE ]:
            if space_start == -1:
                space_start = i
        else:
            if space_start > -1:
                text = text[:start+space_start] + SPACE + text[start+i:]
                return text
        i += 1
    return text

def get_left_padding(text):
    x = 0
    while x < len(text):
        char = text[x]
        if char != SPACE and char != NEWLINE:
            return x-1
        x += 1
    return 0

def scrub(text):
    output = []
    lpad = get_left_padding(text)

    for ln in text.split(NEWLINE):
        if ln == EMPTY:
            continue
        output.append(ln.rstrip()[lpad:])
    out = NEWLINE.join(output)
    while any(re.finditer(REGEX_UNNECESSARY_NEWLINE2, out)):
        con = [ a for a in re.finditer(REGEX_UNNECESSARY_NEWLINE2, out)][0]
        out = strip_inner(out, con.start(), con.end())

    for reg in REGEX_BAD_NEWLINES:
        bad = [ b for b in re.finditer(reg, out, re.IGNORECASE) ]

        # Bail if this is the general pattern for this doc
        if len(bad) > 3:
            continue
        for b in bad:
            txt = out[b.start():b.end()]
            if txt.endswith('Exclusion') or txt.endswith('Inclusion'):
                continue
            bounds = 10
            sb = b.start()-bounds if b.start()-bounds > 0 else b.start()
            se = b.end()+bounds if b.end()+bounds < len(out) else b.end()
            print('\t\t"' + out[sb:se].replace('\n',' ----- ') + '"')
            
            start = b.start() + out[b.start():b.end()].find('\n')
            end = start + len('\n')
            out = out[:start] + ' ' + out[end:]

    return out.strip()

def parse(filepath):
    doc = minidom.parse(filepath)
    elig = doc.getElementsByTagName('eligibility')
    first_submit = doc.getElementsByTagName('study_first_submitted')
    countries = doc.getElementsByTagName('location_countries')
    source = doc.getElementsByTagName('source')
    keywords = doc.getElementsByTagName('keyword')
    if len(first_submit):
        dt = parse_date(first_submit[0].firstChild.data)
    if dt and len(elig):
        crit = [ node for node in elig[0].childNodes if node.nodeName == 'criteria' ]
        if len(crit):
            text = [ node for node in crit[0].childNodes if node.nodeName == 'textblock' ]
            if len(text):
                text = text[0].firstChild.data
                text_len = len(text)
                if text_len >= MIN_LEN and text_len <= MAX_LEN:
                    if len(countries):
                        country = [ node for node in countries[0].childNodes if node.nodeName == 'country' ][0].firstChild.data
                        source = source[0].firstChild.data if len(source) else None
                        keywords = [ w.firstChild.data for w in keywords ] if len(keywords) else []
                        if country == 'United States':
                            return { 
                                'year': dt.year, 'criteria': scrub(text), 'country': country, 
                                'source': source, 'keywords': keywords 
                            }
    return None

def save_to_file(filepath, data):
    with open(filepath, 'w+', encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def parse_files(main_dir):
    i = 1
    for d in os.listdir(main_dir):
        dirpath = main_dir + os.path.sep + d
        if os.path.isfile(dirpath):
            continue
        for f in os.listdir(dirpath):
            print(f'Parsing file {i}: {f}...')
            filepath = dirpath + os.path.sep + f
            data = parse(filepath)
            i += 1
            if data:
                year_out_dir = os.path.join(out_dir, str(data['year']))
                f_out_path = f'{year_out_dir}{os.path.sep}{f.replace(".xml", ".json")}'

                if not os.path.exists(year_out_dir):
                    os.makedirs(year_out_dir)

                #for name, reg in [ ['icd10',REGEX_ICD10], ['cpt',REGEX_CPT], ['immune',REGEX_IMMUNE], ['low',REGEX_LOW], ['most-recent',REGEX_MOST_RECENT], ['negative',REGEX_NEGATIVE], ['reactive',REGEX_REACTIVE] ]:
                for name, reg in [ ['low',REGEX_LOW] ]:
                    data[name] = True if re.search(reg, data['criteria'], re.IGNORECASE) else False

                    if data[name]:
                        dir_name = os.path.join('data','docs','meta',name)
                        if not os.path.exists(dir_name):
                            os.makedirs(dir_name)
                        with open(dir_name+'/'+f.replace('.xml','.txt'), 'w+') as fout:
                            fout.write(data['criteria'])
                        with open(dir_name+'/'+f.replace('.xml','.json'), 'w+', encoding="utf-8") as fout:
                            json.dump(data, fout, ensure_ascii=False, indent=4)

                #save_to_file(f_out_path, data)

cwd = os.getcwd() + os.path.sep
main_dir = cwd + os.path.join('data','AllPublicXML')
out_dir = cwd + os.path.join('data','docs','json')

parse_files(main_dir)