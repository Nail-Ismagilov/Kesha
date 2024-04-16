import requests
from bs4 import BeautifulSoup 

SPEC_HTML_PART      = 'span'
SPEC_HTML_ATTRIBUTE = {'style':"color: #4b90c9; display: block;"}
SPEC_HTML_ATTRIBUTE2 = {"style":"color: #4b90c9;"}
NAME_HTML_PART      = 'h2'
NAME_HTML_ATTRIBUTE = {'class':"entry-title"}

url = {'Hündinen' : 'https://tierschutzverein-kesha.de/vermittlung/huendinnen/',
       'Rüden' : 'https://tierschutzverein-kesha.de/vermittlung/ruede/',
       'Welpen_Madchen' : 'https://tierschutzverein-kesha.de/vermittlung/welpen-junghunde/',
       'Welpen_und_Junghunde' : 'https://tierschutzverein-kesha.de/welpen-junghunde-jungs/'}

def get_pets_from_url(self, url):
    html_text = requests.get(url).text
    soup = BeautifulSoup(html_text, 'html.parser')
    table = soup.find('div', attrs = {'id':'page-content'})  

    dogs = []
    for row in table.findAll('blockquote', attrs = {'class':'pets'}):
        dog = {}
        try:
            dog['url'] = row.a['href']
            dog['spec'] = self.get_html_element(row, SPEC_HTML_PART, SPEC_HTML_ATTRIBUTE)
            if dog['spec'] == '':
                dog['spec'] = self.get_html_element(row, SPEC_HTML_PART, SPEC_HTML_ATTRIBUTE2)
            dog['name'] = self.get_html_element(soup, NAME_HTML_PART, NAME_HTML_ATTRIBUTE)
        except TypeError:
            continue
        dogs.append(dog)
    return dogs

def get_html_element(self, html_text, element, attribute):
    value = ''
    for a in html_text.findAll(element, attrs = attribute):
        try:
            value = a.text
        except TypeError:
            value = 'N/A'
    return value