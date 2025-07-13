#!/usr/bin/env python3
"""
RSS Feed Generator for Anthropic News

This script replaces the GeminiCLI dependency by:
1. Crawling https://www.anthropic.com/news for articles
2. Extracting article information (title, date, URL, description)
3. Translating content to Japanese (basic translation)
4. Generating RSS 2.0 XML format
5. Saving to dist/anthropic-news.xml
"""

import os
import sys
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import xml.etree.ElementTree as ET
from urllib.parse import urljoin, urlparse
import re
from typing import List, Dict, Optional


class JapaneseTranslator:
    """Basic Japanese translation using keyword mapping"""
    
    TRANSLATIONS = {
        # Common AI/Tech terms
        'AI': 'AI',
        'artificial intelligence': '人工知能',
        'machine learning': '機械学習',
        'deep learning': 'ディープラーニング',
        'neural network': 'ニューラルネットワーク',
        'model': 'モデル',
        'training': 'トレーニング',
        'data': 'データ',
        'algorithm': 'アルゴリズム',
        'technology': '技術',
        'research': '研究',
        'development': '開発',
        'innovation': 'イノベーション',
        'breakthrough': 'ブレークスルー',
        'advancement': '進歩',
        'improvement': '改善',
        'update': 'アップデート',
        'release': 'リリース',
        'announcement': '発表',
        'news': 'ニュース',
        'today': '今日',
        'new': '新しい',
        'latest': '最新の',
        'introduces': '導入',
        'launched': 'ローンチ',
        'available': '利用可能',
        'company': '会社',
        'team': 'チーム',
        'product': '製品',
        'service': 'サービス',
        'feature': '機能',
        'capability': '能力',
        'performance': 'パフォーマンス',
        'safety': '安全性',
        'security': 'セキュリティ',
        'privacy': 'プライバシー',
        'ethics': '倫理',
        'responsible': '責任ある',
        'partnership': 'パートナーシップ',
        'collaboration': 'コラボレーション',
        'claude': 'Claude',
        'anthropic': 'Anthropic',
    }
    
    @classmethod
    def translate(cls, text: str) -> str:
        """Basic keyword-based translation to Japanese"""
        if not text:
            return text
            
        translated = text
        for english, japanese in cls.TRANSLATIONS.items():
            # Case-insensitive replacement
            pattern = re.compile(re.escape(english), re.IGNORECASE)
            translated = pattern.sub(japanese, translated)
        
        return translated


class AnthropicNewsScraper:
    """Scraper for Anthropic news page"""
    
    def __init__(self):
        self.base_url = "https://www.anthropic.com"
        self.news_url = "https://www.anthropic.com/news"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def fetch_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch and parse a web page"""
        try:
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            return BeautifulSoup(response.content, 'html.parser')
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def extract_articles(self) -> List[Dict[str, str]]:
        """Extract articles from Anthropic news page"""
        soup = self.fetch_page(self.news_url)
        if not soup:
            return self._get_fallback_articles()
        
        articles = []
        
        # Try multiple selectors for article detection
        article_selectors = [
            'article',
            '.news-item',
            '.post',
            '.article',
            '[data-testid="article"]',
            '.card',
            '.content-item'
        ]
        
        for selector in article_selectors:
            elements = soup.select(selector)
            if elements:
                print(f"Found {len(elements)} articles using selector: {selector}")
                for element in elements[:10]:  # Limit to 10 articles
                    article = self._extract_article_info(element)
                    if article:
                        articles.append(article)
                break
        
        # Fallback: look for links containing certain keywords
        if not articles:
            print("Trying fallback: looking for news-related links")
            links = soup.find_all('a', href=True)
            for link in links:
                href = link.get('href', '')
                text = link.get_text(strip=True)
                
                if any(keyword in href.lower() or keyword in text.lower() 
                       for keyword in ['news', 'blog', 'post', 'announcement', 'update']):
                    
                    full_url = urljoin(self.base_url, href)
                    if full_url != self.news_url and text:
                        article = {
                            'title': text[:100],  # Limit title length
                            'link': full_url,
                            'description': f"記事の詳細については、リンク先をご確認ください。",
                            'pub_date': datetime.now().strftime('%d %b %Y %H:%M:%S +0000')
                        }
                        articles.append(article)
                        
                        if len(articles) >= 5:  # Limit fallback articles
                            break
        
        if not articles:
            return self._get_fallback_articles()
        
        return articles
    
    def _extract_article_info(self, element) -> Optional[Dict[str, str]]:
        """Extract article information from an HTML element"""
        try:
            # Try to find title
            title_selectors = ['h1', 'h2', 'h3', '.title', '.headline', 'a']
            title = None
            for selector in title_selectors:
                title_elem = element.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if title:
                        break
            
            if not title:
                return None
            
            # Try to find link
            link = None
            link_elem = element.find('a', href=True)
            if link_elem:
                link = urljoin(self.base_url, link_elem['href'])
            else:
                # If no link found, use news page as fallback
                link = self.news_url
            
            # Try to find description
            description_selectors = ['.description', '.excerpt', '.summary', 'p']
            description = "記事の詳細については、リンク先をご確認ください。"
            for selector in description_selectors:
                desc_elem = element.select_one(selector)
                if desc_elem:
                    desc_text = desc_elem.get_text(strip=True)
                    if desc_text and len(desc_text) > 20:  # Ensure meaningful description
                        description = desc_text[:200] + "..." if len(desc_text) > 200 else desc_text
                        break
            
            # Try to find date
            date_selectors = ['.date', '.published', 'time', '[datetime]']
            pub_date = datetime.now().strftime('%d %b %Y %H:%M:%S +0000')
            for selector in date_selectors:
                date_elem = element.select_one(selector)
                if date_elem:
                    date_text = date_elem.get_text(strip=True)
                    if date_text:
                        try:
                            # Try to parse various date formats
                            parsed_date = self._parse_date(date_text)
                            if parsed_date:
                                pub_date = parsed_date.strftime('%d %b %Y %H:%M:%S +0000')
                                break
                        except:
                            continue
            
            # Translate title and description to Japanese
            title_jp = JapaneseTranslator.translate(title)
            description_jp = JapaneseTranslator.translate(description)
            
            return {
                'title': title_jp,
                'link': link,
                'description': description_jp,
                'pub_date': pub_date
            }
            
        except Exception as e:
            print(f"Error extracting article info: {e}")
            return None
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string into datetime object"""
        date_formats = [
            '%Y-%m-%d',
            '%B %d, %Y',
            '%b %d, %Y',
            '%d %B %Y',
            '%d %b %Y',
            '%Y/%m/%d',
            '%m/%d/%Y',
            '%d/%m/%Y'
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str.strip(), fmt)
            except ValueError:
                continue
        
        return None
    
    def _get_fallback_articles(self) -> List[Dict[str, str]]:
        """Generate fallback articles when scraping fails"""
        return [{
            'title': 'Anthropic公式サイトで最新ニュースをご確認ください',
            'link': self.news_url,
            'description': 'ウェブスクレイピングが一時的に利用できません。最新のAnthropicニュースについては、公式サイトをご確認ください。',
            'pub_date': datetime.now().strftime('%d %b %Y %H:%M:%S +0000')
        }]


class RSSGenerator:
    """RSS 2.0 XML generator"""
    
    def __init__(self):
        self.channel_info = {
            'title': 'Anthropic News',
            'link': 'https://www.anthropic.com/news',
            'description': 'Anthropic公式サイトのニュースをもとに自動生成された非公式RSSフィードです'
        }
    
    def generate_rss(self, articles: List[Dict[str, str]]) -> str:
        """Generate RSS 2.0 XML from articles"""
        # Create root RSS element
        rss = ET.Element('rss')
        rss.set('version', '2.0')
        
        # Create channel
        channel = ET.SubElement(rss, 'channel')
        
        # Add channel info
        ET.SubElement(channel, 'title').text = self.channel_info['title']
        ET.SubElement(channel, 'link').text = self.channel_info['link']
        ET.SubElement(channel, 'description').text = self.channel_info['description']
        ET.SubElement(channel, 'language').text = 'ja'
        ET.SubElement(channel, 'lastBuildDate').text = datetime.now().strftime('%d %b %Y %H:%M:%S +0000')
        
        # Add articles as items
        for article in articles:
            item = ET.SubElement(channel, 'item')
            ET.SubElement(item, 'title').text = article['title']
            ET.SubElement(item, 'link').text = article['link']
            ET.SubElement(item, 'description').text = article['description']
            ET.SubElement(item, 'pubDate').text = article['pub_date']
            ET.SubElement(item, 'guid').text = article['link']
        
        # Convert to string with XML declaration
        xml_str = ET.tostring(rss, encoding='utf-8', method='xml')
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + xml_str.decode('utf-8')


def main():
    """Main function to generate RSS feed"""
    print("Starting Anthropic News RSS generation...")
    
    # Create output directory
    os.makedirs('dist', exist_ok=True)
    
    # Scrape articles
    print("Scraping Anthropic news...")
    scraper = AnthropicNewsScraper()
    articles = scraper.extract_articles()
    
    print(f"Found {len(articles)} articles")
    for article in articles:
        print(f"- {article['title']}")
    
    # Generate RSS
    print("Generating RSS feed...")
    generator = RSSGenerator()
    rss_content = generator.generate_rss(articles)
    
    # Save to file
    output_path = 'dist/anthropic-news.xml'
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(rss_content)
    
    print(f"RSS feed generated successfully: {output_path}")
    print(f"Feed contains {len(articles)} articles")


if __name__ == '__main__':
    main()