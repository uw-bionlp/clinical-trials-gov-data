import os
import sys
import requests
import json

sys.path.append(os.path.join(os.getcwd(), 'src'))
from preprocess.config import Config
from preprocess.brat_document import BratDocument
import preprocess.utils as utils

url = 'http://localhost:5001/api/nlp/predict'
headers = {'Content-Type': 'application/json'}
data = {
    "inclusion" :
        """Inclusion Criteria:
        1. Age ≥18 years
        2. Scheduled to work with SARS-CoV-2 infected patients for at least 3 days in a week.
        Exclusion Criteria:
        1. Previous documented SARS-CoV-2 infections and subsequent negative SARS-CoV-2 rt-PCR test.
        2. Pregnancy
        3. Known hemoglobinopathies.
        4. Known anemia""",
    "exclusion": ""
}

try:
    response = requests.post(url, headers=headers, data=json.dumps(data))
    if response.ok:
        resp_data = response.json()
        cleaned_text = resp_data['cleanedText']
        entities = resp_data['namedEntities']
        
        for entity in entities:
            x=1
except Exception as ex:
    print(ex)
