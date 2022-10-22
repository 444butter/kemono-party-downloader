import os
from concurrent.futures import ThreadPoolExecutor
from time import sleep

import bs4
import requests
import re


class Post:
    title: str
    url: str
    timestamp: str
    content: str
    files: list = []
    downloads: list = []
    links: list = []

    @property
    def total_files(self):
        return len(self.files) + len(self.downloads)

    def download(self, path, update_progress, progress, parent):
        failed = []
        foldername = re.sub(r'[\\/*?:"<>|]', '', self.title)
        os.makedirs(path + foldername, exist_ok=True)
        prog_counter = 0
        with open(path + foldername + "\\post.url", 'w', encoding="utf-8") as f:
            f.write("[InternetShortcut]\nURL=" + self.url)
        with open(path + foldername + "\\content.txt", 'w', encoding="utf-8") as f:
            f.write(self.content)
        with open(path + foldername + "\\links_in_content.txt", 'w', encoding="utf-8") as f:
            f.write("\n".join(self.links))
        if self.files:
            os.makedirs(path + foldername + "\\files", exist_ok=True)
            with ThreadPoolExecutor(max_workers=10) as executor:
                for file in self.files:
                    executor.submit(self.download_file, failed, parent, path + foldername + "\\files\\", prog_counter, progress, update_progress, file)
        if self.downloads:
            os.makedirs(path + foldername + "\\downloads", exist_ok=True)
            with ThreadPoolExecutor(max_workers=10) as executor:
                for download in self.downloads:
                    executor.submit(
                        self.download_file,
                        failed, parent, path + foldername + "\\downloads\\", prog_counter, progress, update_progress,
                        download
                        )

        with open(path + foldername + "\\failed.txt", 'w', encoding="utf-8") as f:
            f.write("\n".join(failed))

    def download_file(self, failed, parent, path, prog_counter, progress, update_progress, download):
        res = parent.session.get(download, stream=True)
        prog_counter += 1
        progress["percent"] = int(prog_counter / self.total_files * 100)
        update_progress(progress)
        if res.status_code != 200:
            res = parent.session.get(re.sub(r'\?f=.+', '', download), stream=True)
            if res.status_code != 200:
                failed.append(download)
                return
        # get the file name from the url or the get parameter
        filename = re.search(r'f=(.+)', download)
        if filename:
            filename = filename.group(1)
        else:
            filename = download.split("/")[-1]
        with open(path + filename, 'wb') as f:
            f.write(res.content)


class Artist:
    name: str
    id: int
    url: str
    avatar: str
    posts: list[Post]

    @property
    def total_posts(self):
        return len(self.posts)


class Downloader:

    def __init__(self, logger=None):
        self.baseURL = 'https://kemono.party'
        if logger is None:
            self.logger = print
        else:
            self.logger = logger
        self.artist = None
        self.download_location = "C:\\Downloads\\"
        self.downloadmngr = None
        self.download_queue = []  # get cookie
        self.session = requests.Session()

    def get_user(self, url):
        self.logger("Getting artist data...")
        if not url.startswith(self.baseURL):
            url = self.baseURL + url
        res = self.session.get(url)
        try:
            res.raise_for_status()
        except Exception as exc:
            self.logger('There was a problem: %s' % (exc))
            return
        soup = bs4.BeautifulSoup(res.text, 'lxml')
        artist = Artist()
        artist.name = soup.select('span[itemprop=name]')[0].getText().strip()
        artist.id = url.split('/')[-1]
        artist.url = url
        artist.avatar = soup.select('img.fancy-image__image')[0].get('src')
        artist.posts = self.parse_pages(url)

        self.artist = artist

    def parse_post(self, url):
        if not url.startswith(self.baseURL):
            url = self.baseURL + url
        self.logger("Parsing post: " + url)
        res = self.session.get(url)
        if res.status_code == 504:
            self.logger("Got server timout, retrying...")
            sleep(5)
            return self.parse_post(url)
        try:
            res.raise_for_status()
        except Exception as exc:
            self.logger('There was a problem: %s' % (exc))
            return None
        soup = bs4.BeautifulSoup(res.text, 'lxml')
        post = Post()
        post.title = soup.select('h1.post__title')[0].getText().strip()
        post.url = url
        post.timestamp = soup.select('time.timestamp')[0].get('datetime')
        if soup.select('div.post__content'):
            post.content = soup.select('div.post__content')[0].getText()
            # get links from content
            post.links = re.findall(r'(https?://[^\s]+)', post.content)
        else:
            post.content = ''
        if soup.select('div.post__files'):
            post.files = [self.baseURL + file.get('href') for file in
                          soup.select('div.post__files')[0].select('a')]
        else:
            post.files = []
        if soup.select('ul.post__attachments'):
            post.downloads = [self.baseURL + down.get('href') for down in
                              soup.select('ul.post__attachments')[0].select('a')]
        else:
            post.downloads = []
        return post

    def download(self, update_progress=None):
        progress = {
            "percent"      : 0,
            "total_percent": 0,
            }
        update_progress(progress)
        counter = 0
        if self.download_location[-1] != "\\": self.download_location += "\\"
        for post in self.artist.posts:
            self.logger("Downloading post: " + post.title)
            post.download(self.download_location + self.artist.name + "\\", update_progress, progress, self)
            counter += 1
            progress["total_percent"] = int((counter / self.artist.total_posts) * 100)

    def parse_pages(self, current_page):
        posts = []
        while True:
            res = self.session.get(current_page)
            try:
                res.raise_for_status()
            except Exception as exc:
                self.logger('There was a problem: %s' % (exc))
                return
            soup = bs4.BeautifulSoup(res.text, 'lxml')

            posts_url = [post.select('a')[0].get('href') for post in soup.select('article.post-card')]
            with ThreadPoolExecutor(max_workers=5) as executor:
                posts += executor.map(self.parse_post, posts_url)

            next_page = soup.select_one('a[title="Next page"]')
            if next_page:
                current_page = self.baseURL + next_page.get('href')
            else:
                return posts


def parse_url(url):
    # parse urls
    downloadable = re.search(r'^https://kemono\.party/([^/]+)/user/([^/]+)', url)
    if not downloadable:
        return None
    return downloadable.group(0)


if __name__ == '__main__':
    print('Kemono Downloader')
    print('=================')
    print('')
    url = input('Enter the URL of the artist: ')
    dl = Downloader()
    dl.get_user(url)
    print('Artist: ' + dl.artist.name)
    print('Total posts: ' + str(dl.artist.total_posts))
