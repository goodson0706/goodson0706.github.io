import re
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime

# Paths
html_path = "Info/index.html"          # source to scan for social links
followers_js_path = "js/followers-data.js"  # file the frontend now reads

SOCIAL_SITES = [
    {
        "name": "YouTube",
        "url_re": r'https://www\.youtube\.com/@([^"\'/]+)',
        "fetch": lambda user: get_youtube_followers(user)
    },
    {
        "name": "Twitch",
        "url_re": r'https://www\.twitch\.tv/([^"\'/]+)',
        "fetch": lambda user: get_twitch_followers(user)
    },
    {
        "name": "TikTok",
        "url_re": r'https://www\.tiktok\.com/@([^"\'/]+)',
        "fetch": lambda user: get_tiktok_followers(user)
    },
    {
        "name": "Facebook",
        "url_re": r'https://www\.facebook\.com/([^"\'/]+)',
        "fetch": lambda user: get_facebook_followers(user)
    },
    {
        "name": "Instagram",
        "url_re": r'https://www\.instagram\.com/([^"\'/]+)',
        "fetch": lambda user: get_instagram_followers(user)
    },
    {
        "name": "Discord",
        "url_re": r'https://discord\.gg/([^"\'/]+)',
        "fetch": lambda code: get_discord_members(code)
    }
]

def get_youtube_followers(username):
    url = f"https://www.youtube.com/@{username}"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(resp.text, "html.parser")
    # Look for "<span ...>130K subscribers</span>"
    for span in soup.find_all("span"):
        if span.text and "subscribers" in span.text:
            match = re.search(r"([\d.,kK]+)\s*subscribers", span.text)
            if match:
                return match.group(1)
    # Fallback: og:description
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
    # Look for "<p ...>71.7K followers</p>"
    p_tags = soup.find_all("p", class_="CoreText-sc-1txzju1-0 gtJaaB")
    for p in p_tags:
        if "followers" in p.text:
            match = re.search(r"([\d.,KMk]+)\s*followers", p.text)
            if match:
                return match.group(1)
    # Fallback: search script/json in page
    match = re.search(r'"followersCount":(\d+)', resp.text)
    if match:
        count = int(match.group(1))
        return k_format(count)
    return "?"

def get_tiktok_followers(username):
    url = f"https://www.tiktok.com/@{username}"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(resp.text, "html.parser")
    # Look for "<strong title='Followers' data-e2e='followers-count'>12.7K</strong>"
    strong = soup.find("strong", {"title": "Followers", "data-e2e": "followers-count"})
    if strong and strong.text.strip():
        return strong.text.strip()
    return "?"

def get_facebook_followers(username):
    url = f"https://www.facebook.com/{username}"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(resp.text, "html.parser")
    # Look for <a> containing "followers" and a <strong> inside
    a_tags = soup.find_all("a")
    for a in a_tags:
        if a.text and "followers" in a.text.lower():
            strong = a.find("strong")
            if strong and strong.text.strip():
                return strong.text.strip()
    # Fallback: regex search in text
    match = re.search(r'([\d.,kK]+)\s+followers', resp.text, re.IGNORECASE)
    if match:
        return match.group(1)
    return "?"

def get_instagram_followers(username):
    url = f"https://www.instagram.com/{username}/"
    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(resp.text, "html.parser")
    # Look for meta property="og:description"
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
            if count is not None:
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

def build_followers_js(followers):
    """Return the JavaScript content for followers-data.js."""
    header = f"/* Auto-generated by scripts/update_followers.py on {datetime.utcnow().isoformat()}Z - DO NOT EDIT */\n"
    # Build JS object lines; ensure keys and values are JSON-escaped strings
    pairs = []
    for k, v in followers.items():
        pairs.append(f"  {json.dumps(k)}: {json.dumps(v)}")
    body = "{\n" + ",\n".join(pairs) + "\n};\n"
    return header + "window.followersData = " + body

def main():
    # parse Info/index.html to find social anchors
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
    except FileNotFoundError:
        print(f"Source HTML not found at {html_path}")
        return

    soup = BeautifulSoup(html, "html.parser")
    followers = {}

    # For each anchor, match against known social site URL patterns and fetch
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        for site in SOCIAL_SITES:
            m = re.match(site["url_re"], href)
            if m:
                identifier = m.group(1)
                # Avoid fetching same site multiple times
                if site["name"] in followers:
                    continue
                try:
                    count = site["fetch"](identifier)
                except Exception as e:
                    print(f"Error fetching {site['name']} ({identifier}): {e}")
                    count = "?"
                followers[site["name"]] = count
                print(f"Found {site['name']} ({identifier}) -> {count}")

    if not followers:
        print("No social links found in html; nothing to write.")
        return

    js_content = build_followers_js(followers)

    # Write only if the contents changed
    try:
        existing = None
        try:
            with open(followers_js_path, "r", encoding="utf-8") as f:
                existing = f.read()
        except FileNotFoundError:
            existing = None

        if existing != js_content:
            with open(followers_js_path, "w", encoding="utf-8") as f:
                f.write(js_content)
            print(f"Wrote updated followers to {followers_js_path}")
        else:
            print("followers-data.js is up to date; no changes made.")
    except Exception as e:
        print(f"Error writing {followers_js_path}: {e}")

if __name__ == "__main__":
    main()
