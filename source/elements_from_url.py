import requests
from bs4 import BeautifulSoup, SoupStrainer
from urllib.parse import urlparse

SPEC_HTML_PART      = 'span'
SPEC_HTML_ATTRIBUTE = {'style':"color: #4b90c9; display: block;"}
SPEC_HTML_ATTRIBUTE2 = {"style":"color: #4b90c9;"}
NAME_HTML_PART      = 'h2'
NAME_HTML_ATTRIBUTE = {'class':"entry-title"}

# (connect, read) timeout so a stalled server can never hang the whole run.
DEFAULT_TIMEOUT = (5, 30)
# One shared connection pool: reuses TCP + TLS via keep-alive across every
# request. A Session does not retain response bodies, so it is memory-safe.
SESSION = requests.Session()

urls = {'Hündinen' : 'https://tierschutzverein-kesha.de/vermittlung/huendinnen/',
       'Rüden' : 'https://tierschutzverein-kesha.de/vermittlung/ruede/',
       'Welpen_Madchen' : 'https://tierschutzverein-kesha.de/vermittlung/welpen-junghunde/',
       'Welpen_und_Junghunde' : 'https://tierschutzverein-kesha.de/welpen-junghunde-jungs/',
       'Pflegestelle' : 'https://tierschutzverein-kesha.de/vermittlung/hunde-in-pflegestellen-deutschland/'}

def fetch_soup(url, parse_only=None):
    """GET a page (shared session + timeout) and parse it.

    Passing a SoupStrainer as parse_only builds only the needed subtree, which
    keeps the in-memory DOM small under a tight memory budget.
    """
    html_text = SESSION.get(url, timeout=DEFAULT_TIMEOUT).text
    return BeautifulSoup(html_text, 'html.parser', parse_only=parse_only)

def get_pets_from_url(url):
    # Parse only the #page-content subtree, not the whole document (header,
    # nav, footer, scripts are discarded before the DOM is built).
    soup = fetch_soup(url, parse_only=SoupStrainer('div', attrs={'id': 'page-content'}))
    table = soup.find('div', attrs = {'id':'page-content'})
    if table is None:
        # Layout change / error page / empty category: report "no dogs" instead
        # of crashing. Callers must treat [] as "unknown", never "all adopted".
        print(f"[WARN] No #page-content at {url}; treating as no dogs.")
        return []

    dogs = []
    for row in table.findAll('blockquote', attrs = {'class':'pets'}):
        dog = {}
        try:
            dog['url'] = row.a['href']
            dog['spec'] = get_html_element(row, SPEC_HTML_PART, SPEC_HTML_ATTRIBUTE)
            if dog['spec'] == '':
                dog['spec'] = get_html_element(row, SPEC_HTML_PART, SPEC_HTML_ATTRIBUTE2)
            dog['name'] = get_last_part_of_url(dog['url'])
        except TypeError:
            continue
        dogs.append(dog)
    soup.decompose()  # free the DOM now rather than waiting for GC
    return dogs

def get_html_element(html_text, element, attribute):
    value = ''
    for a in html_text.findAll(element, attrs = attribute):
        try:
            value = a.text
        except TypeError:
            value = 'N/A'
    return value


def get_last_part_of_url(url):
    parsed_url = urlparse(url)
    path_segments = parsed_url.path.strip('/').split('/')
    return path_segments[-1]