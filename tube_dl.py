import json

import youtube_dl

try:
    ydl_opts = {'format': 'bestaudio'}
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info('https://open.spotify.com/track/0o6G2zLqwyffGSNZVY4jUW?si=Dt_W_F5mTe2Mpeezyz9Z3Q', download=False)
    with open('files/output.json', 'w') as f:
        f.write(json.dumps(info, indent=4))
except youtube_dl.DownloadError:
    print('Error')
