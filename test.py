from bs4 import BeautifulSoup
from urllib.request import Request, urlopen
import requests

req = Request('https://duckduckgo.com/?q=hemodynamic', headers={'User-Agent': 'Mozilla/5.0'})
soup = BeautifulSoup(urlopen(req, timeout=20).read(), 'html.parser')
results = soup.find_all('a', attrs={'class':'result__a'}, href=True)

for link in results:
    url = link['href']
    o = urllib.parse.urlparse(url)
    d = urllib.parse.parse_qs(o.query)
    print(d['uddg'][0])