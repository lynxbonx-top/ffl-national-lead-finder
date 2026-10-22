import re, time
from urllib.parse import urlparse, urljoin
import pandas as pd
from bs4 import BeautifulSoup
from requests import RequestException
from urllib.robotparser import RobotFileParser
import requests

COLUMNS=['name','role','agency','email','phone','city','state','website','profile_url','affiliation','evidence_url','source','notes']
STATES={'AL':'Alabama','AK':'Alaska','AZ':'Arizona','AR':'Arkansas','CA':'California','CO':'Colorado','CT':'Connecticut','DE':'Delaware','FL':'Florida','GA':'Georgia','HI':'Hawaii','ID':'Idaho','IL':'Illinois','IN':'Indiana','IA':'Iowa','KS':'Kansas','KY':'Kentucky','LA':'Louisiana','ME':'Maine','MD':'Maryland','MA':'Massachusetts','MI':'Michigan','MN':'Minnesota','MS':'Mississippi','MO':'Missouri','MT':'Montana','NE':'Nebraska','NV':'Nevada','NH':'New Hampshire','NJ':'New Jersey','NM':'New Mexico','NY':'New York','NC':'North Carolina','ND':'North Dakota','OH':'Ohio','OK':'Oklahoma','OR':'Oregon','PA':'Pennsylvania','RI':'Rhode Island','SC':'South Carolina','SD':'South Dakota','TN':'Tennessee','TX':'Texas','UT':'Utah','VT':'Vermont','VA':'Virginia','WA':'Washington','WV':'West Virginia','WI':'Wisconsin','WY':'Wyoming'}
HEADERS={'User-Agent':'FFLPublicResearch/1.0 (public business contact research)'}
EMAIL=re.compile(r'(?<![\w.+-])[\w.+-]+@[\w.-]+\.[a-z]{2,}(?![\w.-])',re.I)
PHONE=re.compile(r'(?<!\d)(?:\+1[\s.()-]*)?\(?\d{3}\)?[\s.()-]*\d{3}[\s.-]*\d{4}(?!\d)')
ROLE=re.compile(r'\b(agency owner|agency principal|agency manager|broker owner|managing partner|founder|co-founder|president|principal|broker|insurance agent|agent|owner)\b',re.I)
NAME=re.compile(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\s*[,–—|:-]\s*(Agency Owner|Owner|Founder|President|Managing Partner|Insurance Agent|Broker|Principal)\b')
NAME2=re.compile(r'\b(?:Agency Owner|Owner|Founder|President|Managing Partner|Broker|Principal)\s*[:–—-]\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})\b')
FFL=re.compile(r'\bfamily\s*(?:first|1st)\s*life\b',re.I)
BAD_DOMAINS={'example.com','sentry.io','wixpress.com','domain.com'}

def clean_url(s):
    s=str(s or '').strip()
    if not s:return ''
    if not s.startswith(('https://','http://')):s='https://'+s
    p=urlparse(s)
    return s if p.scheme in ('https','http') and p.hostname else ''

def permitted(url):
    from ipaddress import ip_address
    import socket
    url=clean_url(url)
    if not url:return False
    p=urlparse(url)
    if p.username or p.password or p.port not in (None,80,443):return False
    try:return all(ip_address(a[4][0]).is_global for a in socket.getaddrinfo(p.hostname,None))
    except (OSError,ValueError):return False

def fetch(url):
    if not permitted(url):return None
    p=urlparse(url)
    try:
        robot=requests.get(f'{p.scheme}://{p.netloc}/robots.txt',headers=HEADERS,timeout=7,allow_redirects=False)
        if robot.status_code in (401,403):return None
        if robot.status_code==200:
            rp=RobotFileParser();rp.parse(robot.text.splitlines())
            if not rp.can_fetch(HEADERS['User-Agent'],url):return None
        elif robot.status_code!=404:return None
        r=requests.get(url,headers=HEADERS,timeout=12,allow_redirects=False)
        if r.status_code!=200 or 'text/html' not in r.headers.get('Content-Type','').lower() or len(r.content)>1_500_000:return None
        return BeautifulSoup(r.text,'html.parser')
    except RequestException:return None

def search(query,max_results=10):
    # Optional third-party search adapter; public search engines may rate limit or block requests.
    try:
        from ddgs import DDGS
        results=DDGS().text(query,max_results=max_results)
        return [{'title':r.get('title',''),'url':clean_url(r.get('href','')),'snippet':r.get('body','')} for r in results if r.get('href')]
    except Exception as e:raise RuntimeError(f'Public search unavailable: {e}. Import URLs or CSV instead.')

def classify(text,url=''):
    if FFL.search(text):return 'Confirmed FFL (page text)'
    if FFL.search(url):return 'Possible FFL (URL only)'
    return 'Unverified'

def extract(url,source='Public website'):
    soup=fetch(url)
    if soup is None:return []
    for tag in soup(['script','style','nav','footer']):tag.decompose()
    text=soup.get_text(' ',strip=True)[:60000]
    status=classify(text,url)
    if status=='Unverified':return []  # never label unrelated insurance agencies as FFL
    title=soup.title.get_text(' ',strip=True) if soup.title else ''
    agency=(title.split('|')[0].split(' - ')[0][:100] if title else urlparse(url).netloc)
    emails=sorted({e.lower() for e in EMAIL.findall(text+' '+' '.join(a.get('href','') for a in soup.select('a[href^="mailto:"]'))) if e.split('@')[-1].lower() not in BAD_DOMAINS})
    phones=sorted(set(PHONE.findall(text)))
    # Conservative role attribution: only explicitly labeled name/role pairs.
    people=[]
    for m in NAME.finditer(text[:25000]):people.append((m.group(1),m.group(2)))
    for m in NAME2.finditer(text[:25000]):people.append((m.group(1),text[max(0,m.start()):m.start()+30].split(':')[0][:40]))
    people=list(dict.fromkeys(people))[:20] or [('', '')]
    rows=[]
    for i,(name,role) in enumerate(people):
        rows.append(dict(name=name,role=role,agency=agency,email=emails[0] if emails else '',phone=phones[0] if phones else '',city='',state='',website=f'{urlparse(url).scheme}://{urlparse(url).netloc}',profile_url=url,affiliation=status,evidence_url=url,source=source,notes='Contacts are page-level; verify they belong to the named person.' if name and (emails or phones) else ''))
    return rows

def crawl_site(url,max_pages=6):
    url=clean_url(url)
    if not url:return []
    p=urlparse(url)
    pages=[url]
    soup=fetch(url)
    if soup:
        for a in soup.select('a[href]'):
            dest=clean_url(urljoin(url,a['href']))
            if urlparse(dest).netloc==p.netloc and re.search(r'(about|team|leadership|agent|contact|staff)',urlparse(dest).path,re.I) and dest not in pages:
                pages.append(dest)
            if len(pages)>=max_pages:break
    out=[]
    for page in pages[:max_pages]:
        out.extend(extract(page,source='Agency website'))
        time.sleep(.5)
    return out

def normalize(df):
    df=df.copy()
    for c in COLUMNS:
        if c not in df:df[c]=''
        df[c]=df[c].fillna('').astype(str).str.strip()
    df['email']=df.email.str.lower()
    df['state']=df.state.str.upper().replace({v.upper():k for k,v in STATES.items()})
    # Person + agency, or email, or exact profile. Avoid collapsing all agents at one agency.
    def key(r):
        if r['name']:return ('person',re.sub(r'\W','',r['name'].lower()),re.sub(r'\W','',r['agency'].lower()))
        if r['email']:return ('email',r['email'])
        return ('profile',r['profile_url'].lower() or r['website'].lower())
    df['_key']=df.apply(key,axis=1)
    df['_score']=df[COLUMNS].ne('').sum(axis=1)
    df=df.sort_values('_score',ascending=False).drop_duplicates('_key').drop(columns=['_key','_score'])
    return df[COLUMNS].reset_index(drop=True)
