#!/usr/bin/python3
"""
Analyze the word frequencies on the main articles of a website
"""
import argparse
import requests
from bs4 import BeautifulSoup
import re
import itertools
import string
from collections import defaultdict
import time
import json
import os
import operator


def load_ignored_words(words_file):
    '''Load a list of words to ignore from a text file
    '''

    ignored_words = set()
    # Read ignored words from file
    if words_file is not None:
        with open(words_file, 'r') as ignore_file:
            lines = ignore_file.readlines()
            lines = [line.strip() for line in lines]
            ignored_words = [w for line in lines for w in line.split(' ')]
        # Keep unique words
        ignored_words = set(ignored_words)
        print('[*] Ignoring the following words')
        print(ignored_words)

    return ignored_words


def retrieve_page(url, base):
    '''Rertrieve the text contents from a URL
    '''
    if url is None:
        return ''

    if not url.startswith('http'):
        url = base + url 

    try:
        print('[+] Retrieving {0}'.format(url))
        content = requests.get(url).text
    except Exception as e:
        print('[-] Error retrieving page content')
        print('[-] {0}'.format(e))
        return ''

    time.sleep(0.2)
    return content


def get_element_texts(content, element_type):
    '''Get the contents of the requested elements  
    '''
    soup = BeautifulSoup(content, 'html.parser')
    elements = soup.find_all(element_type)
    text = [element.get_text().strip() for element in elements]
    return text


def get_links(content):
    '''Get all the links of a page
    '''
    soup = BeautifulSoup(content, 'html.parser')
    elements = soup.find_all('a')
    links = [element.get('href') for element in elements]
    return links


def create_word_list(elements, ignored_words=set()):
    '''Create a list of words given a list of html elements 

    This function splits the sentenctes into words and merges them into one
    single list. Moreover, it removes punctuation and turns all words to
    lowercase in order to make frequency analysis easier.
    If provided with a list of ignored words, it removes those words from
    the final words list.

    Args:
        elements: List of HTML elements that the function gets the text from
        
        ignored_words: Set of words remove from the final list

    Returns:
        A list of all the words contained in the given elements

    '''

    word_list = []
    for element in elements:
        element_words = element.split(' ')
        if element_words is not None:
            word_list += element_words
    # Remove punctuation
    removed_punctuation = [''.join(c for c in word if c not in string.punctuation)
                           for word in word_list]
    # Make lowercase
    lower_list = [w.lower() for w in removed_punctuation]
    # Remove ignored words and words of length 1 
    final_list = [w for w in lower_list if len(w) > 1 and w not in ignored_words]

    return final_list


def get_domain(url):
    '''Get the domain name of a url (without prefix and suffix
    '''
    m = re.match(r'https?://(www\.)?(.+)\..+', url)
    return m.group(2)


def follow_links(url):
    '''Follow the links on a webpage and return the content
    '''
    cache_fname = '{domain}.json'.format(domain=get_domain(url))

    if os.path.isfile(cache_fname):
        print('[*] Loading from cache file {0}'.format(cache_fname))
        with open(cache_fname, 'r') as cache_file:
            pages = json.load(cache_file)
            return pages


    content = retrieve_page(url, url)
    links = get_links(content)
    pages = [retrieve_page(link, url) for link in links]

    print('[*] Saving cache file {0}'.format(cache_fname))
    with open(cache_fname, 'w') as cache_file:
        json.dump(pages, cache_file)

    return pages 


def mine_url(url, ignored_words):
    '''Given a url, follow all the links and return lists of words on each page
    '''
    pages = follow_links(url)
    paragraph_list = [get_element_texts(page, 'p') for page in pages]
    word_lists = [create_word_list(paragraphs, ignored_words) for paragraphs in paragraph_list]
    return word_lists


def calculate_tf(word_list):
    '''Calculate relative term frequencies for a list of words
    '''
    tf = defaultdict(int)
    max_freq = 0
    for word in word_list:
        tf[word] += 1
        if tf[word] > max_freq:
            max_freq = tf[word]

    for word, freq in tf.items():
        tf[word] = round(tf[word] / max_freq, 3)

    return tf


def main():

    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Retrieve specified HTML'
                                     ' Elements from a URL')
    parser.add_argument('url', help='The html page you want to retrieve all'
                        ' the elements from')
    parser.add_argument('-i', '--ignore', help='Path to ignored words list')
    args = parser.parse_args()

    # Add http if not already present in the url
    if not re.match('^https?://*', args.url):
        args.url = 'http://' + args.url

    # Load ignored words
    ignored_words = load_ignored_words(args.ignore)

    # Parse content
    word_lists = mine_url(args.url, ignored_words)
    all_words = itertools.chain(*word_lists)
    frequencies = calculate_tf(all_words)
    print('[*] Most Frequent Words')
    for i, w in enumerate(sorted(frequencies, key=frequencies.get, reverse=True)):
        if i > 50:
            break
        print(' {0:_<20}: {1: 5}'.format(w, frequencies[w]))


if __name__ == '__main__':
    main()
