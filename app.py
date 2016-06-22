#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Usage: 
python app.py <username>
"""
import concurrent.futures
import json
import os
import requests
import sys
import warnings
from tqdm import tqdm

warnings.filterwarnings("ignore")


class InstagramScraper:

    def __init__(self, username):
        self.username = username
        self.numPosts = 0
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)
        self.future_to_item = {}
        self.save_dir = './' + self.username
        self.resume_file = os.path.join(self.save_dir, '.resume')

    def get_min_id(self):
        if os.path.exists(self.resume_file):
            with open(self.resume_file, 'r') as f:
                return json.load(f).get('min_id')
        return None

    def set_min_id(self, value):
        with open(self.resume_file, 'w') as f:
            json.dump({
                'min_id': value,
            }, f)

    def crawl(self, max_id=None, min_id=None):
        """Walks through the user's media"""
        url = 'http://instagram.com/' + self.username + '/media' + ('?&max_id=' + max_id if max_id is not None else '')
        resp = requests.get(url)
        media = json.loads(resp.text)

        if min_id is None:
            min_id = self.get_min_id()

        new_min_id = None
        is_continue = False
        for item in media['items']:
            if self.numPosts == 0:
                new_min_id = item['id']
            if item['id'] == min_id:
                break
            self.numPosts += 1
            future = self.executor.submit(self.download, item, self.save_dir)
            self.future_to_item[future] = item
        else:
            is_continue = True

        sys.stdout.write('\rFound %i new post(s)' % self.numPosts)
        sys.stdout.flush()

        if is_continue and 'more_available' in media and media['more_available'] is True:
            max_id = media['items'][-1]['id']
            self.crawl(max_id, min_id)

        if new_min_id is not None:
            self.set_min_id(new_min_id)

    def download(self, item, save_dir='./'):
        """Downloads the media file"""
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)

        item['url'] = item[item['type'] + 's']['standard_resolution']['url']
        base_name = item['url'].split('/')[-1].split('?')[0]
        file_path = os.path.join(save_dir, base_name)

        with open(file_path, 'wb') as file:
            bytes = requests.get(item['url']).content
            file.write(bytes)

        file_time = int(item['created_time'])
        os.utime(file_path, (file_time, file_time))

if __name__ == '__main__':
    username = sys.argv[1]

    scraper = InstagramScraper(username)
    scraper.crawl()

    for future in tqdm(concurrent.futures.as_completed(scraper.future_to_item), total=len(scraper.future_to_item), desc='Downloading'):
        item = scraper.future_to_item[future]

        if future.exception() is not None:
            print ('%r generated an exception: %s') % (item['url'], future.exception())
