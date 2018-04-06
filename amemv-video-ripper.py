# -*- coding: utf-8 -*-

import os
import sys

import requests
import time
from six.moves import queue as Queue
from threading import Thread
import json

# Setting timeout
TIMEOUT = 10

# Retry times
RETRY = 5

# Numbers of downloading threads concurrently
THREADS = 10


def _create_user_info_file(folder, user_info):
    txtName = folder + '/' + user_info.get('uid', 'user_info') + '.json'
    f = open(txtName, "a+")
    f.write(json.dumps(user_info, sort_keys=True, indent=2))
    f.close()


def _create_challenge_info_file(folder, challenge, challenge_info):
    txtName = folder + '/' + challenge_info.get('cid') + '.json'
    f = open(txtName, "a+")
    f.write('\r\n#' + challenge + '\r\n')
    f.write(json.dumps(challenge_info, sort_keys=True, indent=2))
    f.close()


class DownloadWorker(Thread):
    def __init__(self, queue):
        Thread.__init__(self)
        self.queue = queue

    def run(self):
        while True:
            uri, target_folder = self.queue.get()
            self.download(uri, target_folder)
            self.queue.task_done()

    def download(self, uri, target_folder):
        try:
            if uri is not None:
                self._download(uri, target_folder)
        except TypeError:
            pass

    def _download(self, uri, target_folder):
        file_name = uri + '.mp4'
        file_path = os.path.join(target_folder, file_name)
        if not os.path.isfile(file_path):
            download_url = 'https://aweme.snssdk.com/aweme/v1/play/?{0}'
            download_params = {
                'video_id': uri,
                'line': '0',
                'ratio': '720p',
                'media_type': '4',
                'vr_type': '0',
                'test_cdn': 'None',
                'improve_bitrate': '0'
            }
            download_url = download_url.format('&'.join([key + '=' + download_params[key] for key in download_params]))
            print("Downloading %s from %s.\n" % (file_name, download_url))
            retry_times = 0
            while retry_times < RETRY:
                try:
                    resp = requests.get(download_url, stream=True, timeout=TIMEOUT)
                    if resp.status_code == 403:
                        retry_times = RETRY
                        print("Access Denied when retrieve %s.\n" % download_url)
                        raise Exception("Access Denied")
                    with open(file_path, 'wb') as fh:
                        for chunk in resp.iter_content(chunk_size=1024):
                            fh.write(chunk)
                    break
                except:
                    # try again
                    pass
                retry_times += 1
            else:
                try:
                    os.remove(file_path)
                except OSError:
                    pass
                print("Failed to retrieve %s from %s.\n" % download_url)


class CrawlerScheduler(object):

    def __init__(self, items):
        self.numbers = []
        self.challenges = []
        for i in range(len(items)):
            if items[i].startswith('#'):
                self.challenges.append(items[i][1:])
            else:
                self.numbers.append(items[i])
        self.queue = Queue.Queue()
        self.scheduling()

    def scheduling(self):
        # create workers
        for x in range(THREADS):
            worker = DownloadWorker(self.queue)
            # Setting daemon to True will let the main thread exit
            # even though the workers are blocking
            worker.daemon = True
            worker.start()

        for number in self.numbers:
            self.download_videos(number)

        for challenge in self.challenges:
            self.download_challenge_videos(challenge)

    def download_videos(self, number):
        self._download_user_media(number)
        self.queue.join()
        print("Finish Downloading All the videos from %s" % number)

    def download_challenge_videos(self, challenge):
        self._download_challenge_media(challenge)
        self.queue.join()
        print("Finish Downloading All the videos from #%s" % challenge)

    def _search(self, keyword, source):
        base_url = "https://api.amemv.com/aweme/v1/%s/search/?{0}" % source
        params = {
            'iid': '26666102238',
            'device_id': '46166717995',
            'os_api': '18',
            'app_name': 'aweme',
            'channel': 'App%20Store',
            'idfa': '00000000-0000-0000-0000-000000000000',
            'device_platform': 'iphone',
            'build_number': '17603',
            'vid': '2ED370A7-F09C-4C9E-90F5-872D57F3127C',
            'openudid': '20dae85eeac1da35a69e2a0ffeaeef41c78a2e97',
            'device_type': 'iPhone8,2',
            'app_version': '1.7.6',
            'version_code': '1.7.6',
            'os_version': '11.3',
            'screen_width': '1242',
            'aid': '1128',
            'ac': 'WIFI',
            'count': '20',
            'cursor': '0',
            'keyword': keyword,
            'ts': str(int(time.time()))
        }
        if source == 'discover':
            params['search_source'] = 'discover'
            params['type'] = '1'
            params['mas'] = '00a49d57e900796603a0887771255f2c2c8351009ce265bf1f2eb8'
            params['as'] = 'a1f580bcf1afba41976207'
        if source == 'challenge':
            params['iid'] = '28175672430'
            params['search_source'] = 'challenge'
            params['mas'] = '008c37d4eaf9b158c3d1b7e3fc0d66008dc45306aae0ff5380d6a8'
            params['as'] = 'a1c5600cb7576a7e273418'

        search_url = base_url.format('&'.join([key + '=' + params[key] for key in params]))
        response = requests.get(search_url, headers={
            'Host': 'api.amemv.com',
            'User-Agent': 'Aweme/1.7.6 (iPhone; iOS 11.3; Scale/3.00)'
        })

        results = json.loads(response.content.decode('utf-8'))
        if source == 'discover':
            user_list = results.get('user_list', [])
            if len(user_list) == 0:
                return None
            return user_list[0]['user_info']
        if source == 'challenge':
            challenge_list = results.get('challenge_list', [])
            if len(challenge_list) == 0:
                return None
            return challenge_list[0]['challenge_info']

    headers = {
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'accept-encoding': 'gzip, deflate, br',
        'accept-language': 'zh-CN,zh;q=0.9',
        'cache-control': 'max-age=0',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 11_0 like Mac OS X) AppleWebKit/604.1.38 (KHTML, like Gecko) Version/11.0 Mobile/15A372 Safari/604.1',
    }

    def _download_user_media(self, number):
        current_folder = os.getcwd()
        target_folder = os.path.join(current_folder, 'download/%s' % number)
        if not os.path.isdir(target_folder):
            os.mkdir(target_folder)

        while True:
            user_info = self._search(number, 'discover')
            if not user_info:
                print("Number %s does not exist" % number)
                break
            _create_user_info_file(target_folder, user_info)

            aweme_list = []
            user_video_url = "https://www.douyin.com/aweme/v1/aweme/post/?{0}"
            user_video_params = {
                'user_id': str(user_info.get('uid')),
                'count': '21',
                'max_cursor': '0',
                'aid': '1128'
            }

            def get_aweme_list(max_cursor=None):
                if max_cursor:
                    user_video_params['max_cursor'] = str(max_cursor)
                url = user_video_url.format('&'.join([key + '=' + user_video_params[key] for key in user_video_params]))
                res = requests.get(url, headers=self.headers)
                contentJson = json.loads(res.content.decode('utf-8'))
                for aweme in contentJson.get('aweme_list', []):
                    aweme_list.append(aweme)
                if contentJson.get('has_more') == 1:
                    get_aweme_list(contentJson.get('max_cursor'))

            get_aweme_list()

            if len(aweme_list) == 0:
                print("There's no video in number %s." % number)
                break

            print("\nAweme number %s, video number %d\n\n" %
                  (number, len(aweme_list)))

            try:
                for post in aweme_list:
                    uri = post['video']['play_addr']['uri']
                    self.queue.put((uri, target_folder))
                break
            except KeyError:
                break
            except UnicodeDecodeError:
                print("Cannot decode response data from URL %s" %
                      user_video_url)
                continue

    def _download_challenge_media(self, challenge):

        while True:
            challenge_info = self._search(challenge, 'challenge')
            challenge_id = challenge_info.get('cid')
            if not challenge_id:
                print("Challenge #%s does not exist" % challenge)
                break
            current_folder = os.getcwd()
            target_folder = os.path.join(current_folder, 'download/#%s' % challenge_id)
            if not os.path.isdir(target_folder):
                os.mkdir(target_folder)

            _create_challenge_info_file(target_folder, challenge, challenge_info)

            aweme_list = []
            challenge_video_url = "https://www.iesdouyin.com/aweme/v1/challenge/aweme/?{0}"
            challenge_video_params = {
                'ch_id': str(challenge_id),
                'count': '9',
                'cursor': '0',
                'aid': '1128',
                'screen_limit': '3',
                'download_click_limit': '3'
            }

            def get_aweme_list(cursor=None):
                if cursor:
                    challenge_video_params['cursor'] = str(cursor)
                url = challenge_video_url.format('&'.join([key + '=' + challenge_video_params[key] for key in challenge_video_params]))
                res = requests.get(url, headers=self.headers)
                contentJson = json.loads(res.content.decode('utf-8'))
                for aweme in contentJson.get('aweme_list', []):
                    aweme_list.append(aweme)
                if contentJson.get('has_more') == 1:
                    get_aweme_list(contentJson.get('cursor'))

            get_aweme_list()

            if len(aweme_list) == 0:
                print("There's no video in challenge %s." % challenge)
                break

            print("\nAweme challenge #%s, video number %d\n\n" % (challenge, len(aweme_list)))

            try:
                for post in aweme_list:
                    uri = post['video']['play_addr']['uri']
                    self.queue.put((uri, target_folder))
                break
            except KeyError:
                break
            except UnicodeDecodeError:
                print("Cannot decode response data from URL %s" % challenge_video_url)
                continue


def usage():
    print("1. Please create file user-number under this same directory.\n"
          "2. In user-number.txt, you can specify amemv number separated by "
          "comma/space/tab/CR. Accept multiple lines of text\n"
          "3. Save the file and retry.\n\n"
          "Sample File Content:\nnumber1,number2\n\n"
          "Or use command line options:\n\n"
          "Sample:\npython amemv-video-ripper.py number1,number2\n\n\n")
    print(u"未找到user-number.txt文件，请创建.\n"
          u"请在文件中指定抖音号，并以 逗号/空格/tab/表格鍵/回车符 分割，支持多行.\n"
          u"保存文件并重试.\n\n"
          u"例子: 抖音号1,抖音号2\n\n"
          u"或者直接使用命令行参数指定站点\n"
          u"例子: python amemv-video-ripper.py 抖音号1,抖音号2")


def parse_sites(fileName):
    with open(fileName, "r") as f:
        raw_sites = f.read().rstrip().lstrip()

    raw_sites = raw_sites.replace("\t", ",") \
        .replace("\r", ",") \
        .replace("\n", ",") \
        .replace(" ", ",")
    raw_sites = raw_sites.split(",")

    numbers = list()
    for raw_site in raw_sites:
        site = raw_site.lstrip().rstrip()
        if site:
            numbers.append(site)
    return numbers


if __name__ == "__main__":
    content = None

    if len(sys.argv) < 2:
        # check the sites file
        filename = "user-number.txt"
        if os.path.exists(filename):
            content = parse_sites(filename)
        else:
            usage()
            sys.exit(1)
    else:
        content = sys.argv[1].split(",")

    if len(content) == 0 or content[0] == "":
        usage()
        sys.exit(1)
    CrawlerScheduler(content)
