#!/usr/bin/env python3
"""
Script to generate OpenAI ChatGPT Release Notes RSS feed by scraping their help page.
Leverages structured HTML format for efficient extraction.
"""

import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime
import os
import sys
from urllib.parse import urljoin
import time
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

def parse_openai_date(date_text):
    """Parse OpenAI date format and convert to RSS format."""
    # OpenAI uses formats like "June 24, 2025", "May 15, 2025", etc.
    try:
        # Clean up the date text
        date_text = date_text.strip()
        
        # Try different date formats
        date_formats = [
            '%B %d, %Y',    # June 24, 2025
            '%b %d, %Y',    # Jun 24, 2025
            '%m/%d/%Y',     # 06/24/2025
            '%Y-%m-%d'      # 2025-06-24
        ]
        
        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_text, fmt)
                return dt.strftime('%d %b %Y %H:%M:%S +0000')
            except ValueError:
                continue
        
        # If parsing fails, return current date
        print(f"Failed to parse date: {date_text}")
        return datetime.now().strftime('%d %b %Y %H:%M:%S +0000')
        
    except Exception as e:
        print(f"Error parsing date '{date_text}': {e}")
        return datetime.now().strftime('%d %b %Y %H:%M:%S +0000')

def extract_openai_articles(page_source, base_url):
    """Extract articles from OpenAI ChatGPT release notes HTML structure."""
    soup = BeautifulSoup(page_source, 'html.parser')
    articles = []
    
    # Find the main content area
    content_area = soup.find('div', class_='prose')
    if not content_area:
        print("Could not find content area")
        return articles
    
    # Find all date headers (h1 tags with dates)
    date_headers = content_area.find_all('h1')
    
    for date_header in date_headers:
        date_text = date_header.get_text(strip=True)
        
        # Skip if this doesn't look like a date
        if not re.search(r'\d{4}', date_text):
            continue
        
        # Parse the date
        pub_date = parse_openai_date(date_text)
        
        # Find all h2 headers (feature updates) between this date and the next date
        current_element = date_header.find_next_sibling()
        feature_sections = []
        
        while current_element:
            if current_element.name == 'h1':
                # Reached next date section, stop
                break
            elif current_element.name == 'h2':
                feature_sections.append(current_element)
            current_element = current_element.find_next_sibling()
        
        # Process each feature section
        for feature_header in feature_sections:
            feature_title = feature_header.get_text(strip=True)
            
            # Extract description from following paragraphs
            description_parts = []
            current_element = feature_header.find_next_sibling()
            
            while current_element and current_element.name not in ['h1', 'h2']:
                if current_element.name == 'p':
                    text = current_element.get_text(strip=True)
                    if text and text != '':
                        description_parts.append(text)
                elif current_element.name == 'ul':
                    # Extract key points from lists
                    list_items = current_element.find_all('li')
                    for li in list_items[:2]:  # Limit to first 2 items
                        text = li.get_text(strip=True)
                        if text:
                            description_parts.append(f"• {text}")
                current_element = current_element.find_next_sibling()
            
            # Build description
            description = ' '.join(description_parts[:3])  # Limit to first 3 parts
            if len(description) > 300:
                description = description[:300] + "..."
            elif not description:
                description = "詳細については、リンク先をご確認ください。"
            
            # Apply translation
            title_ja = translate_simple(f"{date_text}: {feature_title}")
            description_ja = translate_simple(description)
            
            # Create article link (use the specific release notes URL)
            article_link = base_url
            
            articles.append({
                'title': title_ja,
                'link': article_link,
                'description': description_ja,
                'pubDate': pub_date
            })
    
    return articles

def scrape_openai_releases():
    """Scrape OpenAI ChatGPT release notes page."""
    url = "https://help.openai.com/en/articles/6825453-chatgpt-release-notes"
    driver = None
    
    try:
        print("Setting up Chrome driver...")
        driver = setup_driver()
        
        print(f"Loading page: {url}")
        driver.get(url)
        
        # Wait for content to load
        print("Waiting for page content to load...")
        wait = WebDriverWait(driver, 30)
        
        # Wait for the main content area to appear
        try:
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "prose")))
        except TimeoutException:
            print("Timeout waiting for content area, proceeding with current state...")
        
        # Add additional wait to ensure content is fully loaded
        time.sleep(3)
        
        # Extract articles from HTML structure
        print("Extracting articles from page content...")
        articles = extract_openai_articles(driver.page_source, url)
        
        # If no articles found, create fallback
        if not articles:
            print("No articles found, creating fallback article...")
            articles = [{
                'title': '最新リリースノートについては公式サイトをご確認ください',
                'link': url,
                'description': 'OpenAI公式サイトでChatGPTの最新リリースノートをご確認いただけます。',
                'pubDate': datetime.now().strftime('%d %b %Y %H:%M:%S +0000')
            }]
        
        print(f"Successfully extracted {len(articles)} articles")
        return articles[:20]  # Limit to 20 articles
        
    except Exception as e:
        print(f"Error scraping OpenAI releases: {e}")
        # Return fallback article in case of scraping failure
        return [{
            'title': 'リリースノート取得エラー - 公式サイトをご確認ください',
            'link': url,
            'description': 'リリースノートの取得中にエラーが発生しました。最新情報については OpenAI 公式サイトをご確認ください。',
            'pubDate': datetime.now().strftime('%d %b %Y %H:%M:%S +0000')
        }]
    
    finally:
        if driver:
            driver.quit()

def translate_simple(text):
    """Simple translation using keyword replacement."""
    # 長い単語から順に置換して部分一致の問題を回避
    translations = [
        ('release notes', 'リリースノート'),
        ('artificial intelligence', '人工知能'),
        ('machine learning', '機械学習'),
        ('announcement', '発表'),
        ('research', '研究'),
        ('release', 'リリース'),
        ('update', 'アップデート'),
        ('improvement', '改善'),
        ('enhancement', '強化'),
        ('feature', '機能'),
        ('capability', '機能'),
        ('performance', 'パフォーマンス'),
        ('quality', '品質'),
        ('experience', '体験'),
        ('interface', 'インターフェース'),
        ('support', 'サポート'),
        ('available', '利用可能'),
        ('users', 'ユーザー'),
        ('model', 'モデル'),
        ('version', 'バージョン'),
        ('beta', 'ベータ'),
        ('latest', '最新'),
        ('news', 'ニュース'),
        ('blog', 'ブログ'),
        ('post', '投稿'),
        ('new', '新しい'),
        ('ChatGPT', 'ChatGPT'),
        ('OpenAI', 'OpenAI'),
        ('GPT-4', 'GPT-4'),
        ('AI', 'AI')
    ]
    
    translated = text
    for en, ja in translations:
        translated = translated.replace(en, ja)
    
    return translated

def generate_rss_feed(articles):
    """Generate RSS 2.0 XML feed from articles."""
    rss = ET.Element('rss', version='2.0')
    channel = ET.SubElement(rss, 'channel')
    
    # Channel metadata
    title = ET.SubElement(channel, 'title')
    title.text = 'OpenAI ChatGPT Release Notes'
    
    link = ET.SubElement(channel, 'link')
    link.text = 'https://help.openai.com/en/articles/6825453-chatgpt-release-notes'
    
    description = ET.SubElement(channel, 'description')
    description.text = 'OpenAI ChatGPTの公式リリースノートをもとに自動生成された非公式RSSフィードです'
    
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
    print("Starting OpenAI ChatGPT Release Notes RSS generation...")
    
    # Create dist directory if it doesn't exist
    os.makedirs('dist', exist_ok=True)
    
    # Scrape articles
    print("Scraping OpenAI release notes...")
    articles = scrape_openai_releases()
    print(f"Found {len(articles)} articles")
    
    # Generate RSS feed
    print("Generating RSS feed...")
    rss_element = generate_rss_feed(articles)
    
    # Create XML string with proper formatting
    ET.indent(rss_element, space="  ", level=0)
    xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(rss_element, encoding='unicode')
    
    # Write to file
    output_path = 'dist/openai-releases.xml'
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