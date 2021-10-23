import requests
from datetime import datetime
import json


class YTVideoInfo:
    def __init__(self, video_renderer: json):
        try:
            self.video_id = video_renderer['videoId']
            self.title = video_renderer['title']['runs'][0]['text']
            uploader = video_renderer['longBylineText']['runs'][0]
            self.uploader_name = uploader['text']
            self.uploader_url = uploader['navigationEndpoint']['commandMetadata']['webCommandMetadata']['url']
        except KeyError:
            raise KeyError

    def get_video_url(self):
        return 'https://www.youtube.com/watch?v=' + self.video_id

    def get_uploader_url(self):
        return 'https://www.youtube.com' + self.uploader_url


class YTVideoDetails:
    title = None
    lengthSeconds = None
    channelId = None
    description = None
    viewCount = None
    ownerChannelName = None
    uploadDate = None
    publishDate = None
    video_id = None
    thumbnails = None
    average_rating = None
    video_formats = None
    audio_formats = None

    def __init__(self, response_data: json):
        try:
            micro_format_renderer = response_data['microformat']['playerMicroformatRenderer']
            video_details = response_data['videoDetails']
            self.title = micro_format_renderer['title']['simpleText']
            self.lengthSeconds = int(micro_format_renderer['lengthSeconds'])
            self.channelId = micro_format_renderer['externalChannelId']
            self.description = micro_format_renderer['description']['simpleText']
            self.viewCount = int(micro_format_renderer['viewCount'])
            self.ownerChannelName = micro_format_renderer['ownerChannelName']
            self.uploadDate = micro_format_renderer['uploadDate']
            self.publishDate = micro_format_renderer['publishDate']
            self.video_id = video_details['videoId']
            self.thumbnails = {'default': micro_format_renderer['thumbnail']['thumbnails'][0]['url']}
            for thumbnail in video_details['thumbnail']['thumbnails']:
                key = str(thumbnail['width']) + 'x' + str(thumbnail['height'])
                self.thumbnails[key] = thumbnail['url']
            self.average_rating = video_details['averageRating']
            self.video_formats = []
            self.audio_formats = []
            for streaming_key in ['formats', 'adaptiveFormats']:
                for form in response_data['streamingData'][streaming_key]:
                    if 'video/' in form['mimeType']:
                        self.video_formats.append(form)
                    elif 'audio/' in form['mimeType']:
                        self.audio_formats.append(form)

        except KeyError:
            raise KeyError

    def get_video_url(self):
        return 'https://www.youtube.com/watch?v=' + self.video_id

    def get_uploader_url(self):
        return 'https://www.youtube.com' + self.channelId

    def get_best_audio(self):
        best = {'bitrate': 0}
        for form in self.audio_formats:
            if best['bitrate'] <= form['bitrate']:
                best = form
        return best

    def get_all(self):
        result = ['動画リンク=' + self.get_video_url() + '\n', 'タイトル=' + self.title + '\n',
                  '視聴回数=' + str(self.viewCount) + '\n', 'アップロード者=' + self.ownerChannelName + '\n',
                  'アップロード者URL=' + self.get_uploader_url() + '\n', 'アップロード日=' + self.uploadDate + '\n',
                  '公開日=' + self.publishDate + '\n', '動画秒数=' + str(self.lengthSeconds) + '\n',
                  '平均評価値=' + str(self.average_rating) + '\n', 'サムネイルURL=' + self.thumbnails['default'] + '\n',
                  '概要欄:\n' + self.description + '\n']
        return result


class YoutubeUtility:
    @staticmethod
    def __get_var(html: str, var_name: str):
        if 'var ' + var_name + ' = ' not in html or len(var_name) == 0:
            return None
        curly_bracket = 0
        in_double_quote = False
        value = ''
        html = html[html.find(var_name) + len(var_name + ' = '):]

        for i in range(len(html)):
            c = html[i]
            if not in_double_quote:
                if c == '{':
                    curly_bracket += 1
                elif c == '}':
                    curly_bracket -= 1

            if c == '\"' and html[i - 1] != '\\':
                in_double_quote = not in_double_quote

            if c in [',', ';'] and curly_bracket == 0:
                break

            value += c
        return value

    @staticmethod
    def search_video(keyword: str):
        try:
            print('[' + str(datetime.now()) + '] Searching "' + keyword + '"...')
            response = requests.get(url='https://www.youtube.com/results?sp=EgIQAQ%253D%253D&search_query=' + keyword)
            if response.status_code != 200:
                print('[' + str(datetime.now()) + '] Could not get data by status code ' + str(response.status_code))
                return None

            content_json = json.loads(YoutubeUtility.__get_var(response.text, 'ytInitialData'))
            videos = content_json['contents']['twoColumnSearchResultsRenderer']['primaryContents'][
                'sectionListRenderer']['contents'][0]['itemSectionRenderer']['contents']
            result = []
            for i in range(len(videos)):
                v = videos[i]
                if 'videoRenderer' not in v.keys():
                    continue
                result.append(YTVideoInfo(v['videoRenderer']))

            return result
        except KeyError:
            return None

    @staticmethod
    def get_video_info(url: str):
        print('[' + str(datetime.now()) + '] Getting information on "' + url + '"...')
        response = requests.get(url=url)
        if response.status_code != 200:
            print('[' + str(datetime.now()) + '] Could not get data by status code ' + str(response.status_code))
            return None

        content_json = json.loads(YoutubeUtility.__get_var(response.text, 'ytInitialData'))
        with open('youtube_utility/ytInitialData.json', 'w') as f:
            f.write(json.dumps(content_json, indent=4))
        content_json = json.loads(YoutubeUtility.__get_var(response.text, 'ytInitialPlayerResponse'))
        with open('youtube_utility/ytInitialResponse.json', 'w') as f:
            f.write(json.dumps(content_json, indent=4))
        try:
            return YTVideoDetails(content_json)
        except KeyError:
            return None
