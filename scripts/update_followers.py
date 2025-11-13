import re
import requests
from bs4 import BeautifulSoup

html_path = "Info/index.html"

# Your channel/user ID(s)
CHANNELS = {
    'YouTube': {
        'url_re': r'https://www.youtube.com/@([^"\']+)',
        'api': lambda username: get_youtube_subscribers(username)
    },
    'Twitch': {
        'url_re': r'https://www.twitch.tv/([^"\']+)',
        'api': lambda username: get_twitch_followers(username)
    },
    # Add TikTok, FB, IG, Discord as needed...
}

def get_youtube_subscribers(username):
    # TODO: Use YouTube Data API or scrape
    # Example below is placeholder
    # To use the API: https://developers.google.com/youtube/v3
    return '123k'  # <--- replace this with actual logic

def get_twitch_followers(username):
    # TODO: (Twitch API needs OAuth client)
    return '69.2k'

def main():
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
    soup = BeautifulSoup(html, 'html.parser')
    changed = False

    for social, info in CHANNELS.items():
        for a in soup.find_all('a', href=True):
            match = re.match(info['url_re'], a['href'])
            if match:
                username = match.group(1)
                count = info['api'](username)
                span = a.find('span', class_='icon-followers')
                if span and span.text != count:
                    print(f"Updating {social} follower count for {username}: {span.text} -> {count}")
                    span.string = count
                    changed = True

    if changed:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(str(soup))
    else:
        print("No changes needed.")

if __name__ == "__main__":
    main()
