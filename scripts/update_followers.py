import re
import os
import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
from pytube import Channel

# Paths
html_path = "Info/index.html"          # source to scan for social links
followers_js_path = "Info/js/followers-data.js"  # file the frontend now reads

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
    api_key = os.environ.get('YOUTUBE_API_KEY')
    url = f"https://www.googleapis.com/youtube/v3/channels"
    params = {
        "part": "statistics",
        "id": 'UCPLcnEPw02ywXVIKR7VWnqg',
        "key": api_key
    }
    response = requests.get(url, params=params)
    data = response.json()
    count = data['items'][0]['statistics']['subscriberCount']
    if count is not None:
        return k_format(int(count))
    return "?"

def get_twitch_followers(username):
    client_id = os.environ.get('TWITCH_CLIENT_ID')
    url = "https://id.twitch.tv/oauth2/token"
    data = {
        "client_id": client_id,
        "client_secret": os.environ.get('TWITCH_CLIENT_SECRET'),
        "grant_type": "client_credentials"
    }
    resp = requests.post(url, data=data)
    access_token = resp.json()["access_token"]

    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {access_token}"
    }
    # Step 2: Get user ID
    user_url = f"https://api.twitch.tv/helix/users?login={username}"
    user_resp = requests.get(user_url, headers=headers)
    user_data = user_resp.json()
    if not user_data["data"]:
        raise Exception("Channel not found")
    user_id = user_data["data"][0]["id"]

    # Step 3: Get follower count
    followers_url = f"https://api.twitch.tv/helix/users/follows?to_id={user_id}"
    followers_resp = requests.get(followers_url, headers=headers)
    followers_data = followers_resp.json()
    print(f'followers_data: {followers_data}')
    count = followers_data["total"]
    if count is not None:
        return k_format(int(count))
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
    if n >= 1_000_000:
        s = f"{n/1_000_000:.1f}".rstrip('0').rstrip('.')
        return s + "M"
    elif n >= 1_000:
        s = f"{n/1_000:.1f}".rstrip('0').rstrip('.')
        return s + "k"
    else:
        return str(n)

def build_followers_js(followers):
    """Return the JavaScript content for followers-data.js."""
    header = f"/* Auto-generated by scripts/update_followers.py on {datetime.utcnow().isoformat()}Z - DO NOT EDIT */\n"
    # Build JS object lines; ensure keys and values are JSON-escaped strings
    pairs = []
    for k, v in followers.items():
        pairs.append(f"  {json.dumps(k.lower())}: {json.dumps(v)}")
    body = "{\n" + ",\n".join(pairs) + "\n};\n"
    return header + "window.followersData = " + body

def parse_existing_followers(js_text):
    """Extract the followers object from existing followers-data.js (if parseable)"""
    if not js_text:
        return {}
    m = re.search(r'window\.followersData\s*=\s*({[\s\S]*?});', js_text)
    if not m:
        return {}
    obj_text = m.group(1)
    try:
        # JSON should be valid since we use json.dumps when writing
        return json.loads(obj_text)
    except Exception:
        # If parsing fails, return empty to avoid accidental overwrites
        return {}

def main():
    # parse Info/index.html to find social anchors
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()
    except FileNotFoundError:
        print(f"Source HTML not found at {html_path}")
        return

    soup = BeautifulSoup(html, "html.parser")

    # Read existing followers file (if any) and parse existing map
    existing = None
    existing_map = {}
    try:
        with open(followers_js_path, "r", encoding="utf-8") as f:
            existing = f.read()
            existing_map = parse_existing_followers(existing)
    except FileNotFoundError:
        existing = None
        existing_map = {}

    # Start from existing map; we'll only overwrite when we have a non-"?" value
    updated_map = dict(existing_map)

    found_any_match = False

    # For each anchor, match against known social site URL patterns and fetch
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        for site in SOCIAL_SITES:
            m = re.match(site["url_re"], href)
            if m:
                identifier = m.group(1)
                # Avoid fetching same site multiple times
                if site["name"] in updated_map and site["name"] in existing_map and site["name"] in updated_map:
                    # We still might want to refresh if existing value is old; but to avoid double-fetch per same anchor, skip
                    pass
                try:
                    count = site["fetch"](identifier)
                except Exception as e:
                    print(f"Error fetching {site['name']} ({identifier}): {e}")
                    count = "?"

                # If fetch failed (returned "?") and we have an existing value, keep it.
                # Only update the map when we have a valid (non-"?") count.
                if count == "?":
                    if site["name"] in existing_map:
                        print(f"Found {site['name']} ({identifier}) -> ? (keeping existing: {chosen})")
                    else:
                        # No existing value to keep; skip adding this site
                        print(f"Found {site['name']} ({identifier}) -> ? (no existing value; skipping)")
                        continue
                else:
                    chosen = count
                    updated_map[site["name"]] = chosen
                    print(f"Found {site['name']} ({identifier}) -> {chosen}")

                # If we got here and chosen is defined, ensure updated_map has it
                if chosen is not None:
                    updated_map[site["name"]] = chosen
                    found_any_match = True

    # If updated_map is empty, nothing meaningful to write
    if not updated_map:
        print("No updatable social counts found; nothing to write.")
        return

    js_content = build_followers_js(updated_map)

    # Write only if the contents changed
    try:
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
