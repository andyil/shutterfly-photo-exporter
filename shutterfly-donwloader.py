# /// script
# dependencies = [
#   "requests",
# ]
# ///

import requests
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


    def prepare_output_dir(self, user_id):
        home = os.path.expanduser('~')
        outdir = os.path.join(home, 'shutterfly-downloader', user_id, 'media')
        metadata = os.path.join(home, 'shutterfly-downloader', user_id, '.metadata')
        os.makedirs(outdir, exist_ok=True)
        os.makedirs(metadata, exist_ok=True)
        return outdir, metadata

    def main(self):
        total_bytes = 0
        j = curl_metadata(self.access_token)
        result = j['result']
        message = result['message']
        if message == 'Invalid token.':
            logger.error('Invalid token')
            exit(1)
        moments = j['result']['payload']['moments']
        total = len(moments)
        logger.info(f'Token Validated. Got %s moments', total)

        media_dir, metadata_dir  = self.prepare_output_dir(moments[0]['life_uid'])

        skipped = 0
        started = None
        downloaded = 0
        printed_skipping = False
        for i, moment in enumerate(moments):
            moment_id = moment['uid']
            seen_file = os.path.join(metadata_dir, f'{moment_id}.txt')
            if os.path.exists(seen_file):
                skipped += 1
                if not printed_skipping:
                    logger.info('Skipping already downloaded photos')
                    printed_skipping = True
            else:
                if skipped:
                    logger.info(f'Skipped %s photos previously downloaded', skipped)
                if started is None:
                    started = time.time()
                skipped = 0
                full_path = curl_moment_3_retries(self.access_token, moment, media_dir)
                downloaded += 1
                file_sz = os.path.getsize(full_path)
                total_bytes += file_sz
                _, _, free = shutil.disk_usage(full_path)
                photos_left = total - i
                speed = downloaded / (time.time() - started) * 60
                speed_r = round(speed, 2)
                time_to_finish = round(photos_left / speed)

                logger.info(f'Downloaded {i} {full_path} of {total}, {file_sz}, total {total_bytes}, {speed_r} photos/min, {time_to_finish} minutes to finish (left: {free})')
                open(seen_file, 'w')





if __name__=='__main__':
    token = sys.argv[1]
    sd = ShutterflyDownloader(token)
    sd.main()
