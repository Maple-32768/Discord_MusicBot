import json

import youtube_dl


def main():
    ydl_opts = {'format': 'bestaudio'}

    url = 'https://www.youtube.com/watch?v=ZDh8mDYsr2U&list=PLu4ytgqlZUA7NooOOfleLaOfjnryMDPKz&index=3'
    try:
        with youtube_dl.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            info['request_type'] = 'youtube_dl'
        with open('youtube_utility/video_in_list.json', 'w', encoding='utf-8') as f:
            json.dump(info, fp=f, indent=4)
    except youtube_dl.DownloadError:
        print('Error')
        return


if __name__ == '__main__':
    main()
