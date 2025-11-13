import re
import requests
from bs4 import BeautifulSoup

html_path = "Info/index.html"

SOCIAL_SITES = [
    {
        "name": "YouTube",
        "url_re": r'https://www.youtube.com/@([^"\']+)',
        "fetch": lambda user: get_youtube_followers(user)
    },
    {
        "name": "Twitch",
        "url_re": r'https://www.twitch.tv/([^"\']+)',
        "fetch": lambda user: get_twitch_followers(user)
    },
    {
        "name": "TikTok",
        "url_re": r'https://www.tiktok.com/@([^"\']+)',
        "fetch": lambda user: get_tiktok_followers(user)
    },
    {
        "name": "Facebook",
        "url_re": r'https://www.facebook.com/([^"\']+)',
        "fetch": lambda user: get_facebook_followers(user)
    },
    {
        "name": "Instagram",
        "url_re": r'https://www.instagram.com/([^"\']+)',
        "fetch": lambda user: get_instagram_followers(user)
    },
    {
        "name": "Discord",
        "url_re": r'https://discord.gg/([^"\']+)',
        "fetch": lambda code: get_discord_members(code)
    }
]

def get_youtube_followers(username):
    url = f"https://www.youtube.com/@{username}"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(resp.text, "html.parser")
    # YouTube renders sub count client-side, but it's still in the HTML in og:description sometimes
    desc = soup.find("meta", property="og:description")
    if desc and desc.get("content"):
        match = re.search(r"([\d.,]+)\s*subscribers", desc["content"])
        if match:
            return match.group(1)
    return "?"

def get_twitch_followers(username):
    url = f"https://www.twitch.tv/{username}"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(resp.text, "html.parser")
    # Try to find the followers count in meta or page scripts
    match = re.search(r'"followersCount":(\d+)', resp.text)
    if match:
        count = int(match.group(1))
        return k_format(count)
    return "?"

def get_tiktok_followers(username):
    url = f"https://www.tiktok.com/@{username}"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(resp.text, "html.parser")
    # Look for <strong title="11,300">11.3K</strong> <span>Followers</span>
    for strong in soup.find_all("strong"):
        parent = strong.parent
        if parent and parent.find("span", string=re.compile("Followers")):
            return strong.text.strip()
    return "?"

def get_facebook_followers(username):
    url = f"https://www.facebook.com/{username}"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(resp.text, "html.parser")
    # Look for "people follow this"
    match = re.search(r'([\d,]+)\s+people follow this', resp.text)
    if match:
        return match.group(1)
    return "?"

def get_instagram_followers(username):
    url = f"https://www.instagram.com/{username}/"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(resp.text, "html.parser")
    # Look for the meta property="og:description"
    desc = soup.find("meta", property="og:description")
    if desc and desc.get("content"):
        match = re.search(r"([\d.,kK]+)\s+Followers", desc["content"])
        if match:
            return match.group(1)
    return "?"

def get_discord_members(invite_code):
    url = f"https://discord.com/api/v9/invites/{invite_code}?with_counts=true"
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        if response.status_code == 200:
            data = response.json()
            count = data.get("approximate_member_count")
            if count:
                return k_format(int(count))
    except Exception as e:
        print(f'Discord scraping error: {e}')
    return "?"

def k_format(n):
    """Format a number in 'k' notation, e.g., 11000->'11k'."""
    if n > 1_000_000:
        return f"{n/1_000_000:.1f}M"
    elif n > 1_000:
        return f"{n/1_000:.1f}k"
    else:
        return str(n)

def main():
    with open(html_path, "r", encoding="utf-8") as f:
        html = f.read()
    soup = BeautifulSoup(html, "html.parser")
    changed = False

    for a in soup.find_all('a', href=True):
        for site in SOCIAL_SITES:
            match = re.match(site["url_re"], a['href'])
            if match:
                username = match.group(1)
                count = site["fetch"](username)
                span = a.find('span', class_='icon-followers')
                if span and count != '?' and span.text != count:
                    print(f"Updating {site['name']} ({username}): {span.text} -> {count}")
                    span.string = count
                    changed = True

    if changed:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(str(soup))
    else:
        print("No updates necessary.")

if __name__ == "__main__":
    main()
