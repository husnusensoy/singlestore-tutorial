import requests
from bs4 import BeautifulSoup
import re
import json

import getpass
from openai import OpenAI

import pandas as pd
import numpy as np
from tqdm import tqdm
import time
import os

import sqlalchemy as sa
from s2_openai_info import API_KEY, USERNAME, PASSWORD, CONN_STR, PORT, DATABASE, EMBEDDING_MODEL


from dotenv import load_dotenv

load_dotenv()

API_KEY = os.environ["API_KEY"]
USERNAME = os.environ["USERNAME"]
PASSWORD = os.environ["PASSWORD"]
CONN_STR = os.environ["CONN_STR"]


page = requests.get('https://en.wikipedia.org/wiki/Wikipedia:Good_articles/Video_games')
soup = BeautifulSoup(page.content, 'html.parser')
links = soup.find_all('a')
urls = [link.get('href') for link in links if link.get('href') is not None]



excluded_patterns = [
    '#',  # Anchor links
    '/wiki/Main_Page',
    '/wiki/Wikipedia:',
    '/wiki/Portal:',
    '/wiki/Special:',
    '/wiki/Help:',
    '//en.wikipedia.org/wiki/Wikipedia:',
    'https://donate.wikimedia.org/wiki/Special:',
    '/w/index.php?title=Special:',
    '/wiki/Special:My',
    'https://www.wikidata.org/wiki/Special:',
    '/w/index.php?title=',
    '/wiki/File:',
    '/wiki/Category:',
    '/wiki/Template:',
    '/wiki/Wikipedia_talk:',
    '/wiki/User:',
]

filtered_urls = ['https://en.wikipedia.org' + url for url in urls if not any(pattern in url for pattern in excluded_patterns)]
     
client = OpenAI(api_key=API_KEY)
engine = sa.create_engine(f'mysql+pymysql://{USERNAME}:{PASSWORD}@{CONN_STR}:{PORT}/{DATABASE}')
conn = engine.connect()
print('Connected to SingleStore')

def create_table():
    '''Creates the table in SingleStore'''
    conn.execute(sa.text('''DROP TABLE IF EXISTS wiki_scrape;'''))
    conn.execute(sa.text('''
    CREATE TABLE wiki_scrape(
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        url VARCHAR(255),
        paragraph TEXT,
        embedding VECTOR(512, F32) NOT NULL,
        FULLTEXT (paragraph),
        VECTOR INDEX (embedding) INDEX_OPTIONS '{"index_type":"IVF_PQ"}'
    );
    '''))
    print('Table created')

def clean_text(text):
    '''cleans the text of a wiki page'''
    text = re.sub(r'', '', text)
    text = re.sub(r'', '', text)
    text = re.sub(r'\<.*?\>', '', text)
    text = re.sub(r'\n', '', text)
    text = re.sub(r'\t', '', text)
    text = re.sub(r'\s\s+', ' ', text)
    return text

def get_text(url):
    '''Gets the text from a wiki page and returns it as a string.'''
    try:
        page = requests.get(url)
        page.raise_for_status()  # Raises an HTTPError if the HTTP request returned an unsuccessful status code
        soup = BeautifulSoup(page.content, 'html.parser')
        paragraphs = soup.find_all('p')
        cleaned_paragraphs = [clean_text(p.text) for p in paragraphs if p.text.strip()]
        return cleaned_paragraphs
    except requests.RequestException as e:
        # print(f"Error fetching URL {url}: {e}")
        return []

def normalize_l2(x:np.array) -> np.array:
    if x.ndim == 1:
        norm = np.linalg.norm(x)
        if norm == 0:
            return x
        return x / norm
    else:
        norm = np.linalg.norm(x, 2, axis=1, keepdims=True)
        return np.where(norm == 0, x, x / norm)

def get_embedding(text, model=EMBEDDING_MODEL):
    '''Generates the OpenAI embedding from an input `text`.'''
    try:
        if isinstance(text, str):
            response = client.embeddings.create(input=[text], model=model)
            embedding = normalize_l2(np.array(response.data[0].embedding[:512],dtype=np.float32))
            # return np.array(embedding).tobytes()
            return json.dumps(embedding.tolist())
        else:
            # print(f"Invalid input: {text}")
            return None
    except Exception as e:
        print(f"Error generating embedding: {e}")
        return None

def text_embedding_df(url):
    '''Creates a dataframe of the text from a wiki page and the OpenAI embeddings of that text'''
    text = get_text(url)
    from pprint import pprint
    #pprint(text)
    embeddings = [get_embedding(t) for t in text]
    df = pd.DataFrame({'paragraph': text, 'embedding': embeddings})
    return df

def scrape_wiki(url_list, table_name, engine):
    '''Pushes a dataframe to a SingleStore table'''
    for url in tqdm(url_list):
        dataframe = text_embedding_df(url)
        dataframe['url'] = url 
        dataframe = dataframe[['url', 'paragraph', 'embedding']]
        dataframe = dataframe[dataframe['embedding'].notna()]

        #print(dataframe)
        dataframe.to_sql(table_name, con=engine, if_exists='append', index=False)

#create_table()
scrape_wiki(filtered_urls[:100], 'wiki_scrape', engine)