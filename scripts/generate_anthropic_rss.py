#!/usr/bin/env python3
"""
Script to generate Anthropic News RSS feed by scraping their news page using Selenium.
Replaces the functionality previously handled by GeminiCLI and improves article extraction.
"""

import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime
import os
import sys
from urllib.parse import urljoin
import time
import json
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager

def setup_driver():
    """Setup Chrome driver with appropriate options for both local and CI environments."""
    chrome_options = Options()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-gpu')
    chrome_options.add_argument('--window-size=1920,1080')
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    try:
        # Try to use ChromeDriverManager for automatic driver management
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except Exception as e:
        print(f"Failed to setup Chrome driver with ChromeDriverManager: {e}")
        # Fallback to system Chrome driver
        try:
            driver = webdriver.Chrome(options=chrome_options)
        except Exception as e2:
            print(f"Failed to setup system Chrome driver: {e2}")
            raise e2
    
    return driver

def extract_articles_from_json(page_source):
    """Extract article data from Next.js page JSON data."""
    articles = []
    
    # Look for JSON data in script tags that might contain article information
    soup = BeautifulSoup(page_source, 'html.parser')
    script_tags = soup.find_all('script', type='application/json')
    
    for script in script_tags:
        try:
            data = json.loads(script.get_text())
            # Search for article-like data structures
            articles_data = find_articles_in_json(data)
            if articles_data:
                articles.extend(articles_data)
        except (json.JSONDecodeError, KeyError) as e:
            continue
    
    # Also look for inline script tags with Next.js data
    script_tags_inline = soup.find_all('script', id=re.compile(r'__NEXT_DATA__'))
    for script in script_tags_inline:
        try:
            data = json.loads(script.get_text())
            articles_data = find_articles_in_json(data)
            if articles_data:
                articles.extend(articles_data)
        except (json.JSONDecodeError, KeyError) as e:
            continue
    
    return articles

def find_articles_in_json(data, path=""):
    """Recursively search for article data in JSON structure."""
    articles = []
    
    if isinstance(data, dict):
        # Look for fields that might contain article data
        if 'slug' in data and 'title' in data:
            # This looks like an article object
            article = extract_article_from_object(data)
            if article:
                articles.append(article)
        
        # Recursively search in all dictionary values
        for key, value in data.items():
            articles.extend(find_articles_in_json(value, f"{path}.{key}"))
    
    elif isinstance(data, list):
        # Search in list items
        for i, item in enumerate(data):
            articles.extend(find_articles_in_json(item, f"{path}[{i}]"))
    
    return articles

def extract_article_from_object(obj):
    """Extract article information from a JSON object."""
    try:
        # Extract title
        title = obj.get('title', '').strip()
        if not title:
            return None
        
        # Extract slug/link
        slug = obj.get('slug', {})
        if isinstance(slug, dict):
            link_path = slug.get('current', '')
        elif isinstance(slug, str):
            link_path = slug
        else:
            return None
        
        if not link_path:
            return None
        
        # Build full URL
        if link_path.startswith('/'):
            link = f"https://www.anthropic.com{link_path}"
        else:
            link = f"https://www.anthropic.com/news/{link_path}"
        
        # Extract published date
        pub_date = obj.get('publishedOn', '')
        if pub_date:
            try:
                # Parse ISO format date
                dt = datetime.fromisoformat(pub_date.replace('Z', '+00:00'))
                formatted_date = dt.strftime('%d %b %Y %H:%M:%S +0000')
            except ValueError:
                formatted_date = datetime.now().strftime('%d %b %Y %H:%M:%S +0000')
        else:
            formatted_date = datetime.now().strftime('%d %b %Y %H:%M:%S +0000')
        
        # Extract description/excerpt
        description = obj.get('description', '') or obj.get('excerpt', '') or obj.get('summary', '')
        if not description:
            description = "記事の詳細については、リンク先をご確認ください。"
        elif len(description) > 200:
            description = description[:200] + "..."
        
        # Apply simple Japanese translation
        title_ja = translate_simple(title)
        description_ja = translate_simple(description)
        
        return {
            'title': title_ja,
            'link': link,
            'description': description_ja,
            'pubDate': formatted_date
        }
    
    except Exception as e:
        print(f"Error extracting article from object: {e}")
        return None

def scrape_anthropic_news():
    """Scrape the Anthropic news page using Selenium for better JavaScript support."""
    url = "https://www.anthropic.com/news"
    driver = None
    
    try:
        print("Setting up Chrome driver...")
        driver = setup_driver()
        
        print(f"Loading page: {url}")
        driver.get(url)
        
        # Wait for content to load
        print("Waiting for page content to load...")
        wait = WebDriverWait(driver, 30)
        
        # Wait for any article elements or links to appear
        try:
            wait.until(lambda d: len(d.find_elements(By.TAG_NAME, "a")) > 10)
        except TimeoutException:
            print("Timeout waiting for page content, proceeding with current state...")
        
        # Add additional wait to ensure JavaScript has finished
        time.sleep(5)
        
        # Extract articles from JSON data first (more reliable)
        print("Extracting articles from page JSON data...")
        articles = extract_articles_from_json(driver.page_source)
        
        # If no articles found in JSON, fall back to DOM parsing
        if not articles:
            print("No articles found in JSON data, trying DOM parsing...")
            articles = extract_articles_from_dom(driver.page_source, url)
        
        # If still no articles, create fallback
        if not articles:
            print("No articles found, creating fallback article...")
            articles = [{
                'title': '最新ニュースについては公式サイトをご確認ください',
                'link': url,
                'description': 'Anthropic公式サイトで最新のニュースやアップデートをご確認いただけます。',
                'pubDate': datetime.now().strftime('%d %b %Y %H:%M:%S +0000')
            }]
        
        print(f"Successfully extracted {len(articles)} articles")
        return articles[:15]  # Limit to 15 articles
        
    except Exception as e:
        print(f"Error scraping Anthropic news: {e}")
        # Return fallback article in case of scraping failure
        return [{
            'title': 'ニュース取得エラー - 公式サイトをご確認ください',
            'link': url,
            'description': 'ニュースの取得中にエラーが発生しました。最新情報については Anthropic 公式サイトをご確認ください。',
            'pubDate': datetime.now().strftime('%d %b %Y %H:%M:%S +0000')
        }]
    
    finally:
        if driver:
            driver.quit()

def extract_articles_from_dom(page_source, base_url):
    """Fallback method to extract articles from DOM when JSON extraction fails."""
    soup = BeautifulSoup(page_source, 'html.parser')
    articles = []
    
    # Look for links that appear to be news articles
    links = soup.find_all('a', href=True)
    
    for link in links:
        href = link.get('href', '')
        text = link.get_text(strip=True)
        
        # Filter for news article links
        if (('/news/' in href or href.startswith('/news/')) and 
            text and len(text) > 10 and len(text) < 200):
            
            # Build full URL
            if href.startswith('/'):
                full_url = f"https://www.anthropic.com{href}"
            else:
                full_url = urljoin(base_url, href)
            
            # Simple Japanese translation
            title_ja = translate_simple(text)
            
            articles.append({
                'title': title_ja,
                'link': full_url,
                'description': translate_simple("記事の詳細については、リンク先をご確認ください。"),
                'pubDate': datetime.now().strftime('%d %b %Y %H:%M:%S +0000')
            })
    
    # Remove duplicates based on link
    seen_links = set()
    unique_articles = []
    for article in articles:
        if article['link'] not in seen_links:
            seen_links.add(article['link'])
            unique_articles.append(article)
    
    return unique_articles[:10]  # Limit to 10 articles

def translate_simple(text):
    """Simple translation using keyword replacement (fallback for Gemini translation)."""
    # 長い単語から順に置換して部分一致の問題を回避
    translations = [
        ('artificial intelligence', '人工知能'),
        ('machine learning', '機械学習'),
        ('announcement', '発表'),
        ('research', '研究'),
        ('release', 'リリース'),
        ('update', 'アップデート'),
        ('safety', '安全性'),
        ('latest', '最新'),
        ('news', 'ニュース'),  # "new"より前に処理
        ('blog', 'ブログ'),
        ('post', '投稿'),
        ('new', '新しい'),    # より短い単語は後に処理
        ('Anthropic', 'Anthropic'),
        ('Claude', 'Claude'),
        ('AI', 'AI')
    ]
    
    translated = text
    for en, ja in translations:
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