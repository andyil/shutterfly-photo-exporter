# /// script
# dependencies = [
#   "requests",
# ]
# ///

import requests
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
import logging
import shutil
import json
import time
import sys
import os




logging.basicConfig(stream=sys.stdout,
                    level=logging.DEBUG,
                    datefmt='%H:%M:%S',
                    format='[%(name)s]  %(levelname)s %(asctime)s %(threadName)s %(message)s')

logging.getLogger().setLevel(logging.WARNING)
logger = logging.getLogger('downloader')
logger.setLevel(logging.DEBUG)
logger.info('Starting')



def curl_metadata(token):
    headers = {
        'accept': 'application/json, text/javascript, */*; q=0.01',
        'accept-language': 'en-US,en;q=0.9,he-IL;q=0.8,he;q=0.7',
        'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'origin': 'https://photos.shutterfly.com',
        'priority': 'u=1, i',
        'referer': 'https://photos.shutterfly.com/',
        'sec-ch-ua': '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
    }

    params = {
        'method': 'getPaginatedMoments',
    }

    data = {"method":"getPaginatedMoments","params":[token,"0","2746403200",200000,False,False,"",True],"headers":{"X-SFLY-SubSource":"library"},"id":None}


    response = requests.post('https://cmd.thislife.com/json', params=params, headers=headers, json=data)

    j = response.json()
    return j


def curl_moment(token, moment, output_directory):
    headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9,he-IL;q=0.8,he;q=0.7',
        'origin': 'https://photos.shutterfly.com',
        'priority': 'u=1, i',
        'referer': 'https://photos.shutterfly.com/',
        'sec-ch-ua': '"Not;A=Brand";v="99", "Google Chrome";v="139", "Chromium";v="139"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'cross-site',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
    }

    moment_id = moment['uid']

    params = {
        'accessToken': token,
        'momentId': moment_id,
        'source': 'FMV',
    }

    response = requests.get('https://io.thislife.com/download', params=params, headers=headers)
    headers = response.headers
    disposition = headers['Content-Disposition']
    filename = disposition.split('=')
    filename = filename[1].replace('"', '')

    fullname = f'{moment_id}-{filename}'

    if len(fullname) > 255:
        name, extension = os.path.splitext(fullname)
        extra_length = len(fullname) - 255 - 3
        name = name[:-extra_length]
        fullname = f'{name}{extension}'
      
    fullpath = os.path.join(output_directory, fullname)

    open(fullpath, 'wb').write(response.content)
    moment_date = moment['moment_date']
    new_timestamp = float(moment_date)
    os.utime(fullpath, (new_timestamp, new_timestamp))

    return fullpath

def curl_moment_3_retries(token, moment, output_directory):
    RETRIES=3
    for ii in range(0, RETRIES):
        try:
            return curl_moment(token, moment, output_directory)
        except:
            if ii == RETRIES-1:
                raise
            logger.warning('Exception downloading moment, retry number %s', ii+1, exc_info=True)





class ShutterflyDownloader:

    def __init__(self, access_token):
        self.access_token = access_token
        self.output_dir = None
        self.metadata_dir = None

    def prepare_output_dirs(self, user_id):
        home = os.path.expanduser('~')
        outdir = os.path.join(home, 'shutterfly-downloader', user_id, 'media')
        metadata = os.path.join(home, 'shutterfly-downloader', user_id, '.metadata')
        os.makedirs(outdir, exist_ok=True)
        os.makedirs(metadata, exist_ok=True)
        self.output_dir = outdir
        self.metadata_dir = metadata



    def download_one_moment(self, moment):
        moment_id = moment['uid']
        seen_file = os.path.join(self.metadata_dir, f'{moment_id}.txt')
        if os.path.exists(seen_file):
            return
        full_path = curl_moment_3_retries(self.access_token, moment, self.output_dir)
        open(seen_file, 'w')
        return full_path


    def download_all(self):
        j = curl_metadata(self.access_token)
        result = j['result']
        message = result['message']
        if message == 'Invalid token.':
            logger.error('Invalid token')
            exit(1)
        moments = j['result']['payload']['moments']
        total = len(moments)
        logger.info(f'Token Validated. Got %s moments', total)
        self.prepare_output_dirs(moments[0]['life_uid'])

        downloaded = 0
        futures = set()
        with ThreadPoolExecutor(max_workers=8) as tp:
            logger.info('Submitting')
            for i, moment in enumerate(moments):
                future = tp.submit(self.download_one_moment, moment)
                futures.add(future)
            logger.info(f'Sent {len(futures)} download jobs')

            skipped = 0

            while futures:
                finished, futures = wait(futures, None, FIRST_COMPLETED)
                for f in finished:
                    r = f.result()
                    if r is None:
                        skipped += 1
                    else:
                        file_sz = os.path.getsize(r)
                        logger.info('Downloaded %s (%s bytes)', r, file_sz)
                logger.info('%s files to finish', len(futures))



if __name__=='__main__':
    if len(sys.argv) != 2:
      logger.error('One mandatory paramter: token')
      exit(1)
    token = sys.argv[1]
    sd = ShutterflyDownloader(token)
    sd.download_all()
