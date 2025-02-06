import requests
from bs4 import BeautifulSoup 
from urllib.parse import urlparse

SPEC_HTML_PART      = 'span'
SPEC_HTML_ATTRIBUTE = {'style':"color: #4b90c9; display: block;"}
SPEC_HTML_ATTRIBUTE2 = {"style":"color: #4b90c9;"}
NAME_HTML_PART      = 'h2'
NAME_HTML_ATTRIBUTE = {'class':"entry-title"}

urls = {'Hündinen' : 'https://tierschutzverein-kesha.de/vermittlung/huendinnen/',
       'Rüden' : 'https://tierschutzverein-kesha.de/vermittlung/ruede/',
       'Welpen_Madchen' : 'https://tierschutzverein-kesha.de/vermittlung/welpen-junghunde/',
       'Welpen_und_Junghunde' : 'https://tierschutzverein-kesha.de/welpen-junghunde-jungs/',
       'Pflegestelle' : 'https://tierschutzverein-kesha.de/vermittlung/hunde-in-pflegestellen-deutschland/'}

def get_pets_from_url(url):
    html_text = requests.get(url).text
    soup = BeautifulSoup(html_text, 'html.parser')
    table = soup.find('div', attrs = {'id':'page-content'})  

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