#!/usr/bin/env python3
"""
Script to generate Anthropic News RSS feed by scraping their news page.
Replaces the functionality previously handled by GeminiCLI.
"""

import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime
import os
import sys
from urllib.parse import urljoin
import time

def scrape_anthropic_news():
    """Scrape the Anthropic news page and extract article information."""
    url = "https://www.anthropic.com/news"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        articles = []
        
        # Look for article containers - Anthropic typically uses specific classes
        # We'll search for common patterns used in news sites
        article_selectors = [
            'article',
            '.news-item',
            '.article-item',
            '.post-item',
            '[class*="article"]',
            '[class*="news"]',
            '[class*="post"]'
        ]
        
        article_elements = []
        for selector in article_selectors:
            elements = soup.select(selector)
            if elements:
                article_elements = elements
                break
        
        # If no specific article containers found, look for links that seem like articles
        if not article_elements:
            # Look for links within the main content that could be articles
            links = soup.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                if (('/news/' in href or '/blog/' in href or '/post/' in href) and 
                    link.get_text(strip=True) and 
                    len(link.get_text(strip=True)) > 10):
                    article_elements.append(link.parent)
        
        for element in article_elements[:10]:  # Limit to 10 articles
            try:
                # Extract title
                title_elem = element.find(['h1', 'h2', 'h3', 'h4', 'a'])
                title = title_elem.get_text(strip=True) if title_elem else "No title found"
                
                # Extract link
                link_elem = element.find('a', href=True)
                if link_elem:
                    link = urljoin(url, link_elem['href'])
                else:
                    continue  # Skip if no link found
                
                # Extract date - look for time elements or date patterns
                date_elem = element.find(['time', '[datetime]']) or element.find(string=lambda text: text and any(month in text.lower() for month in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']))
                if date_elem:
                    if hasattr(date_elem, 'get'):
                        date_str = date_elem.get('datetime') or date_elem.get_text(strip=True)
                    else:
                        date_str = str(date_elem).strip()
                else:
                    date_str = datetime.now().strftime('%d %b %Y %H:%M:%S +0000')
                
                # Extract description
                desc_elem = element.find(['p', '.description', '.excerpt', '.summary'])
                description = desc_elem.get_text(strip=True)[:200] + "..." if desc_elem and desc_elem.get_text(strip=True) else "記事の詳細については、リンク先をご確認ください。"
                
                # Simple Japanese translation patterns (basic keyword replacement)
                title_ja = translate_simple(title)
                description_ja = translate_simple(description)
                
                articles.append({
                    'title': title_ja,
                    'link': link,
                    'description': description_ja,
                    'pubDate': format_date(date_str)
                })
                
            except Exception as e:
                print(f"Error processing article element: {e}")
                continue
        
        # If no articles found through DOM parsing, create a fallback article
        if not articles:
            articles.append({
                'title': '最新ニュースについては公式サイトをご確認ください',
                'link': url,
                'description': 'Anthropic公式サイトで最新のニュースやアップデートをご確認いただけます。',
                'pubDate': datetime.now().strftime('%d %b %Y %H:%M:%S +0000')
            })
        
        return articles
        
    except Exception as e:
        print(f"Error scraping Anthropic news: {e}")
        # Return fallback article in case of scraping failure
        return [{
            'title': 'ニュース取得エラー - 公式サイトをご確認ください',
            'link': url,
            'description': 'ニュースの取得中にエラーが発生しました。最新情報については Anthropic 公式サイトをご確認ください。',
            'pubDate': datetime.now().strftime('%d %b %Y %H:%M:%S +0000')
        }]

def translate_simple(text):
    """Simple translation using keyword replacement (fallback for Gemini translation)."""
    translations = {
        'Anthropic': 'Anthropic',
        'Claude': 'Claude',
        'AI': 'AI',
        'artificial intelligence': '人工知能',
        'machine learning': '機械学習',
        'research': '研究',
        'safety': '安全性',
        'announcement': '発表',
        'release': 'リリース',
        'update': 'アップデート',
        'new': '新しい',
        'latest': '最新',
        'news': 'ニュース',
        'blog': 'ブログ',
        'post': '投稿'
    }
    
    translated = text
    for en, ja in translations.items():
        translated = translated.replace(en, ja)
    
    return translated

def format_date(date_str):
    """Format date string to RFC-822 format."""
    try:
        # Try parsing various date formats
        formats = [
            '%Y-%m-%d',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%d %b %Y',
            '%B %d, %Y'
        ]
        
        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%d %b %Y %H:%M:%S +0000')
            except ValueError:
                continue
        
        # If parsing fails, return current date
        return datetime.now().strftime('%d %b %Y %H:%M:%S +0000')
        
    except Exception:
        return datetime.now().strftime('%d %b %Y %H:%M:%S +0000')

def generate_rss_feed(articles):
    """Generate RSS 2.0 XML feed from articles."""
    rss = ET.Element('rss', version='2.0')
    channel = ET.SubElement(rss, 'channel')
    
    # Channel metadata
    title = ET.SubElement(channel, 'title')
    title.text = 'Anthropic News'
    
    link = ET.SubElement(channel, 'link')
    link.text = 'https://www.anthropic.com/news'
    
    description = ET.SubElement(channel, 'description')
    description.text = 'Anthropic公式サイトのニュースをもとに自動生成された非公式RSSフィードです'
    
    language = ET.SubElement(channel, 'language')
    language.text = 'ja'
    
    last_build_date = ET.SubElement(channel, 'lastBuildDate')
    last_build_date.text = datetime.now().strftime('%d %b %Y %H:%M:%S +0000')
    
    # Add articles as items
    for article in articles:
        item = ET.SubElement(channel, 'item')
        
        item_title = ET.SubElement(item, 'title')
        item_title.text = article['title']
        
        item_link = ET.SubElement(item, 'link')
        item_link.text = article['link']
        
        item_description = ET.SubElement(item, 'description')
        item_description.text = article['description']
        
        item_pubdate = ET.SubElement(item, 'pubDate')
        item_pubdate.text = article['pubDate']
    
    return rss

def main():
    """Main function to generate the RSS feed."""
    print("Starting Anthropic News RSS generation...")
    
    # Create dist directory if it doesn't exist
    os.makedirs('dist', exist_ok=True)
    
    # Scrape articles
    print("Scraping Anthropic news...")
    articles = scrape_anthropic_news()
    print(f"Found {len(articles)} articles")
    
    # Generate RSS feed
    print("Generating RSS feed...")
    rss_element = generate_rss_feed(articles)
    
    # Create XML string with proper formatting
    ET.indent(rss_element, space="  ", level=0)
    xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(rss_element, encoding='unicode')
    
    # Write to file
    output_path = 'dist/anthropic-news.xml'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(xml_str)
    
    print(f"RSS feed generated successfully: {output_path}")
    
    # Print summary for verification
    print("\nGenerated feed summary:")
    for i, article in enumerate(articles[:3], 1):
        print(f"{i}. {article['title']}")
        print(f"   {article['link']}")
        print(f"   {article['pubDate']}")
        print()

if __name__ == "__main__":
    main()