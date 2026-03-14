#!/usr/bin/env python3
"""
Script to generate an RSS feed for the Hanaregumi Live News page.
"""

import re
import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from bs4 import BeautifulSoup

NEWS_URL = "https://www.hanaregumi.jp/news_category/live"


def fetch_live_news(url: str) -> list[dict]:
    """Fetch and parse Live News articles from the Hanaregumi website."""
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching page: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    articles = []

    for a in soup.find_all("a", href=re.compile(r"hanaregumi\.jp/news/\d+")):
        time_tag = a.find("time")
        title_tag = a.find("div", class_="c_title")
        if not time_tag or not title_tag:
            continue

        # "2026.03.11 Wed" → "2026.03.11"
        date_str = time_tag.get_text(strip=True).split()[0]
        try:
            date_obj = datetime.strptime(date_str, "%Y.%m.%d").replace(tzinfo=timezone.utc)
        except ValueError:
            continue

        articles.append({
            "title": title_tag.get_text(strip=True),
            "link": a["href"],
            "pubDate": date_obj.strftime("%a, %d %b %Y %H:%M:%S +0000"),
        })

    return articles


def generate_rss(articles: list[dict]) -> ET.Element:
    """Generate an RSS 2.0 XML element from article data."""
    rss = ET.Element("rss", version="2.0", attrib={"xmlns:atom": "http://www.w3.org/2005/Atom"})
    channel = ET.SubElement(rss, "channel")

    ET.SubElement(channel, "title").text = "ハナレグミ Live News"
    ET.SubElement(channel, "link").text = NEWS_URL
    ET.SubElement(channel, "description").text = "ハナレグミ公式サイトのLiveニュース一覧"
    ET.SubElement(channel, "language").text = "ja"
    ET.SubElement(channel, "lastBuildDate").text = datetime.now(timezone.utc).strftime(
        "%a, %d %b %Y %H:%M:%S +0000"
    )
    ET.SubElement(
        channel, "atom:link",
        href="https://zeero.github.io/unofficial-rss-feeds/hanaregumi-live.xml",
        rel="self",
        type="application/rss+xml",
    )

    for article in articles:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = article["title"]
        ET.SubElement(item, "link").text = article["link"]
        ET.SubElement(item, "description").text = article["title"]
        ET.SubElement(item, "guid", isPermaLink="true").text = article["link"]
        ET.SubElement(item, "pubDate").text = article["pubDate"]

    return rss


def main():
    print("Starting Hanaregumi Live News RSS generation...")

    os.makedirs("dist", exist_ok=True)
    output_path = "dist/hanaregumi-live.xml"

    print(f"Fetching {NEWS_URL} ...")
    articles = fetch_live_news(NEWS_URL)
    if not articles:
        print("No articles found. Exiting.")
        return
    print(f"Found {len(articles)} articles.")

    rss = generate_rss(articles)
    ET.indent(rss, space="  ", level=0)
    xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(rss, encoding="unicode")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml_str)

    print(f"RSS feed generated: {output_path}")


if __name__ == "__main__":
    main()
