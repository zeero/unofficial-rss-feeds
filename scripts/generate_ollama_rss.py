#!/usr/bin/env python3
"""
Script to generate Ollama Models RSS feed by scraping their search page.
"""

import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
import os
import sys
import re
import hashlib

def load_existing_articles(rss_file_path):
    """Load existing articles from RSS file to preserve dates and avoid duplicates."""
    existing_articles = {}

    if not os.path.exists(rss_file_path):
        return existing_articles

    try:
        tree = ET.parse(rss_file_path)
        root = tree.getroot()

        # Find all item elements in the RSS
        for item in root.findall('.//item'):
            title_elem = item.find('title')
            link_elem = item.find('link')
            pubdate_elem = item.find('pubDate')
            description_elem = item.find('description')

            if title_elem is not None and link_elem is not None:
                title = title_elem.text or ''
                link = link_elem.text or ''
                pubdate = pubdate_elem.text if pubdate_elem is not None else ''
                description = description_elem.text if description_elem is not None else ''

                # Create unique key based on title and link
                article_key = create_article_key(title, link)
                existing_articles[article_key] = {
                    'title': title,
                    'link': link,
                    'description': description,
                    'pubDate': pubdate
                }

    except Exception as e:
        print(f"Warning: Could not load existing RSS file: {e}")

    return existing_articles

def create_article_key(title, link):
    """Create a unique key for an article based on title and link."""
    # Normalize title and link for comparison
    normalized_title = re.sub(r'\s+', ' ', title.strip().lower())
    normalized_link = link.strip().lower()

    # Create hash from normalized title and link
    content = f"{normalized_title}|{normalized_link}"
    return hashlib.md5(content.encode('utf-8')).hexdigest()

def merge_articles_with_existing(new_articles, existing_articles):
    """Merge new articles with existing ones, preserving dates for duplicates."""
    merged_articles = []
    seen_keys = set()

    for article in new_articles:
        article_key = create_article_key(article['title'], article['link'])

        if article_key in existing_articles:
            # Use existing article data to preserve the original date
            merged_article = existing_articles[article_key].copy()
            # Update description if new one is more detailed
            if len(article['description']) > len(merged_article['description']):
                merged_article['description'] = article['description']
        else:
            # This is a new article
            merged_article = article.copy()

        # Avoid duplicates in the merged list
        if article_key not in seen_keys:
            merged_articles.append(merged_article)
            seen_keys.add(article_key)

    return merged_articles

def translate_simple(text):
    """Simple translation using keyword replacement."""
    translations = [
        ('exceptional multilingual capabilities', '卓越した多言語対応能力'),
        ('significantly stronger coding capabilities', '大幅に強化されたコーディング能力'),
        ('multi-agent applications', 'マルチエージェントアプリケーション'),
        ('professional productivity', 'プロフェッショナルな生産性'),
        ('document intelligence', 'ドキュメントインテリジェンス'),
        ('multimodal understanding', 'マルチモーダル理解'),
        ('proactive autonomous execution', '積極的な自律実行'),
        ('swarm-based task orchestration', 'スウォームベースのタスクオーケストレーション'),
        ('achieves state-of-the-art', '最先端を達成'),
        ('multilingual capabilities', '多言語対応能力'),
        ('document understanding', 'ドキュメント理解'),
        ('agentic workflows', 'エージェントワークフロー'),
        ('exceptional utility', '卓越した有用性'),
        ('frontier-level', 'フロンティアレベル'),
        ('next-generation', '次世代'),
        ('flagship model', 'フラッグシップモデル'),
        ('systems engineering', 'システムエンジニアリング'),
        ('long-horizon tasks', '長期タスク'),
        ('on-device deployment', 'デバイス上での展開'),
        ('inference efficient', '推論効率が高い'),
        ('lightweight deployment', '軽量デプロイメント'),
        ('family of models', 'モデルファミリー'),
        ('designed for', '向けに設計された'),
        ('designed to', 'するように設計された'),
        ('well-suited for', 'に適した'),
        ('substantially', '大幅に'),
        ('preservation', '保存'),
        ('significantly stronger', '大幅に強化された'),
        ('predecessor', '前身'),
        ('wide margin', '大差'),
        ('enterprise-grade', 'エンタープライズグレード'),
        ('compute efficiency', '計算効率'),
        ('practical capabilities', '実用的な能力'),
        ('optimized for', '最適化された'),
        ('local development', 'ローカル開発'),
        ('communicate across', 'を越えてコミュニケーション'),
        ('harmonizes', '調和させる'),
        ('performance', 'パフォーマンス'),
        ('open-source', 'オープンソース'),
        ('reasoning', '推論'),
        ('coding', 'コーディング'),
        ('deliver', '提供'),
        ('upgrades', 'アップグレード'),
        ('previous', '以前の'),
        ('leads', 'リード'),
        ('accuracy', '精度'),
        ('complex', '複雑な'),
        ('real-world', '現実世界'),
        ('hybrid models', 'ハイブリッドモデル'),
        ('elevate', '高める'),
        ('collection of', 'コレクション'),
        ('superior', '優れた'),
        ('native', 'ネイティブ'),
        ('balances', 'バランスをとる'),
        ('Updated', '更新日'),
        ('months ago', 'ヶ月前'),
        ('month ago', 'ヶ月前'),
        ('weeks ago', '週間前'),
        ('week ago', '週間前'),
        ('days ago', '日前'),
        ('day ago', '日前'),
        ('hours ago', '時間前'),
        ('hour ago', '時間前'),
        ('minutes ago', '分前'),
        ('minute ago', '分前'),
        ('ago', '前'),
    ]

    translated = text
    # Sort translations by length of the English phrase (descending) to match longest first
    translations.sort(key=lambda x: len(x[0]), reverse=True)

    for en, ja in translations:
        # Use regex to replace whole words or specific phrases
        pattern = re.compile(re.escape(en), re.IGNORECASE)
        translated = pattern.sub(ja, translated)

    return translated

def parse_relative_date(relative_text):
    """Convert relative date like '1 week ago' to a stable date."""
    now = datetime.now(timezone.utc)

    # Default to now
    dt = now

    match = re.search(r'(\d+)\s+(year|month|week|day|hour|minute)s?\s+ago', relative_text, re.IGNORECASE)
    if match:
        amount = int(match.group(1))
        unit = match.group(2).lower()

        if unit == 'year':
            dt = now - timedelta(days=amount * 365)
        elif unit == 'month':
            dt = now - timedelta(days=amount * 30)
        elif unit == 'week':
            dt = now - timedelta(weeks=amount)
        elif unit == 'day':
            dt = now - timedelta(days=amount)
        elif unit == 'hour':
            dt = now - timedelta(hours=amount)
        elif unit == 'minute':
            dt = now - timedelta(minutes=amount)

    return dt.strftime('%a, %d %b %Y %H:%M:%S +0000')

def fetch_ollama_models():
    """Fetch and parse models from Ollama search page."""
    url = "https://ollama.com/search?sort=newest"
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching Ollama search: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    articles = []

    # Find model items - they are in <a> tags with library path
    for a in soup.find_all("a", href=re.compile(r"^/library/")):
        title_tag = a.find("span", {"x-test-search-response-title": True})
        desc_tag = a.find("p")
        updated_tag = a.find("span", {"x-test-updated": True})

        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)
        description = desc_tag.get_text(strip=True) if desc_tag else ""
        link = "https://ollama.com" + a["href"]

        relative_date = updated_tag.get_text(strip=True) if updated_tag else "just now"
        pub_date = parse_relative_date(relative_date)

        # Translate
        title_ja = title # Keep model name as is
        full_description = f"{description} (Updated: {relative_date})"
        description_ja = translate_simple(full_description)

        articles.append({
            "title": title_ja,
            "link": link,
            "description": description_ja,
            "pubDate": pub_date,
        })

    return articles

def generate_rss(articles):
    """Generate RSS 2.0 XML element from article data."""
    rss = ET.Element("rss", version="2.0", attrib={"xmlns:atom": "http://www.w3.org/2005/Atom"})
    channel = ET.SubElement(rss, "channel")

    ET.SubElement(channel, "title").text = "Ollama Models"
    ET.SubElement(channel, "link").text = "https://ollama.com/search?sort=newest"
    ET.SubElement(channel, "description").text = "Ollamaの最新モデル一覧"
    ET.SubElement(channel, "language").text = "ja"
    ET.SubElement(channel, "lastBuildDate").text = datetime.now(timezone.utc).strftime(
        "%a, %d %b %Y %H:%M:%S +0000"
    )

    for article in articles:
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = article["title"]
        ET.SubElement(item, "link").text = article["link"]
        ET.SubElement(item, "description").text = article["description"]
        ET.SubElement(item, "guid", isPermaLink="true").text = article["link"]
        ET.SubElement(item, "pubDate").text = article["pubDate"]

    return rss

def main():
    print("Starting Ollama Models RSS generation...")

    os.makedirs("dist", exist_ok=True)
    output_path = "dist/ollama-models.xml"

    # Load existing articles to preserve dates
    existing_articles = load_existing_articles(output_path)

    print("Fetching Ollama models...")
    new_articles = fetch_ollama_models()

    if not new_articles:
        print("No models found. Exiting.")
        return

    print(f"Found {len(new_articles)} models.")

    # Merge
    articles = merge_articles_with_existing(new_articles, existing_articles)

    # Sort by pubDate (though parse_relative_date makes it approximate)
    # Since we use sort=newest, the order from site is already newest first.

    rss = generate_rss(articles)
    ET.indent(rss, space="  ", level=0)
    xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(rss, encoding="unicode")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(xml_str)

    print(f"RSS feed generated: {output_path}")

if __name__ == "__main__":
    main()
