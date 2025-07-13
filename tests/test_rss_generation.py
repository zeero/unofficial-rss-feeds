#!/usr/bin/env python3
"""
テストモジュール: RSS生成機能のユニットテスト
"""

import pytest
import xml.etree.ElementTree as ET
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.generate_anthropic_rss import (
    translate_simple,
    format_date,
    generate_rss_feed,
    extract_article_from_object,
    find_articles_in_json,
    extract_articles_from_dom
)


class TestTranslateSimple:
    """translate_simple関数のテスト"""
    
    def test_basic_translation(self):
        """基本的な翻訳テスト"""
        text = "This is the latest AI research news"
        result = translate_simple(text)
        
        assert "最新" in result  # latest -> 最新
        assert "AI" in result    # AI remains AI
        assert "研究" in result  # research -> 研究
        assert "ニュース" in result  # news -> ニュース
    
    def test_anthropic_keywords(self):
        """Anthropic関連キーワードの翻訳テスト"""
        text = "Anthropic announces new Claude update release"
        result = translate_simple(text)
        
        assert "Anthropic" in result
        assert "Claude" in result
        assert "リリース" in result
        assert "アップデート" in result
    
    def test_no_translation_needed(self):
        """翻訳不要なテキストのテスト"""
        text = "テストメッセージ"
        result = translate_simple(text)
        assert result == text
    
    def test_empty_string(self):
        """空文字列のテスト"""
        result = translate_simple("")
        assert result == ""


class TestFormatDate:
    """format_date関数のテスト"""
    
    def test_iso_format(self):
        """ISO形式の日付フォーマットテスト"""
        date_str = "2023-12-25T10:30:00Z"
        result = format_date(date_str)
        assert "25 Dec 2023" in result
        assert "+0000" in result
    
    def test_invalid_date(self):
        """無効な日付フォーマットのテスト"""
        date_str = "invalid-date"
        result = format_date(date_str)
        
        # 現在日時のフォーマットが返されることを確認
        assert "+0000" in result
        assert len(result.split()) == 5  # "DD MMM YYYY HH:MM:SS +0000"
    
    def test_various_formats(self):
        """様々な日付フォーマットのテスト"""
        test_cases = [
            "2023-12-25",
            "2023-12-25T10:30:00",
            "25 Dec 2023",
            "December 25, 2023"
        ]
        
        for date_str in test_cases:
            result = format_date(date_str)
            assert "+0000" in result
            assert len(result) > 10


class TestGenerateRssFeed:
    """generate_rss_feed関数のテスト"""
    
    def test_empty_articles(self):
        """記事が空の場合のテスト"""
        articles = []
        rss_element = generate_rss_feed(articles)
        
        # RSS構造の基本チェック
        assert rss_element.tag == "rss"
        assert rss_element.get("version") == "2.0"
        
        channel = rss_element.find("channel")
        assert channel is not None
        
        # チャンネルメタデータの確認
        title = channel.find("title")
        assert title is not None
        assert title.text == "Anthropic News"
        
        # アイテムが存在しないことを確認
        items = channel.findall("item")
        assert len(items) == 0
    
    def test_single_article(self):
        """単一記事のRSS生成テスト"""
        articles = [{
            'title': 'テスト記事',
            'link': 'https://example.com/test',
            'description': 'テスト記事の説明',
            'pubDate': '01 Jan 2023 12:00:00 +0000'
        }]
        
        rss_element = generate_rss_feed(articles)
        channel = rss_element.find("channel")
        items = channel.findall("item")
        
        assert len(items) == 1
        
        item = items[0]
        assert item.find("title").text == "テスト記事"
        assert item.find("link").text == "https://example.com/test"
        assert item.find("description").text == "テスト記事の説明"
        assert item.find("pubDate").text == "01 Jan 2023 12:00:00 +0000"
    
    def test_multiple_articles(self):
        """複数記事のRSS生成テスト"""
        articles = [
            {
                'title': '記事1',
                'link': 'https://example.com/1',
                'description': '記事1の説明',
                'pubDate': '01 Jan 2023 12:00:00 +0000'
            },
            {
                'title': '記事2',
                'link': 'https://example.com/2',
                'description': '記事2の説明',
                'pubDate': '02 Jan 2023 12:00:00 +0000'
            }
        ]
        
        rss_element = generate_rss_feed(articles)
        channel = rss_element.find("channel")
        items = channel.findall("item")
        
        assert len(items) == 2
        assert items[0].find("title").text == "記事1"
        assert items[1].find("title").text == "記事2"


class TestExtractArticleFromObject:
    """extract_article_from_object関数のテスト"""
    
    def test_valid_article_object(self):
        """有効な記事オブジェクトのテスト"""
        obj = {
            'title': 'Test Article',
            'slug': {'current': '/news/test-article'},
            'publishedOn': '2023-12-25T10:30:00Z',
            'description': 'This is a test article description'
        }
        
        result = extract_article_from_object(obj)
        
        assert result is not None
        assert 'Test Article' in result['title']
        assert result['link'] == 'https://www.anthropic.com/news/test-article'
        assert '25 Dec 2023' in result['pubDate']
        assert 'test article' in result['description'].lower()
    
    def test_missing_title(self):
        """タイトルが欠如している場合のテスト"""
        obj = {
            'slug': {'current': '/news/test'},
            'publishedOn': '2023-12-25T10:30:00Z'
        }
        
        result = extract_article_from_object(obj)
        assert result is None
    
    def test_missing_slug(self):
        """スラッグが欠如している場合のテスト"""
        obj = {
            'title': 'Test Article',
            'publishedOn': '2023-12-25T10:30:00Z'
        }
        
        result = extract_article_from_object(obj)
        assert result is None
    
    def test_string_slug(self):
        """文字列形式のスラッグのテスト"""
        obj = {
            'title': 'Test Article',
            'slug': 'test-article',
            'publishedOn': '2023-12-25T10:30:00Z'
        }
        
        result = extract_article_from_object(obj)
        
        assert result is not None
        assert result['link'] == 'https://www.anthropic.com/news/test-article'
    
    def test_no_published_date(self):
        """公開日が欠如している場合のテスト"""
        obj = {
            'title': 'Test Article',
            'slug': {'current': '/news/test'}
        }
        
        result = extract_article_from_object(obj)
        
        assert result is not None
        assert '+0000' in result['pubDate']  # 現在日時が設定される


class TestFindArticlesInJson:
    """find_articles_in_json関数のテスト"""
    
    def test_simple_article_structure(self):
        """シンプルな記事構造のテスト"""
        data = {
            'title': 'Test Article',
            'slug': {'current': '/news/test'},
            'publishedOn': '2023-12-25T10:30:00Z'
        }
        
        articles = find_articles_in_json(data)
        
        assert len(articles) == 1
        assert 'Test Article' in articles[0]['title']
    
    def test_nested_article_structure(self):
        """ネストした記事構造のテスト"""
        data = {
            'pageData': {
                'articles': [
                    {
                        'title': 'Article 1',
                        'slug': {'current': '/news/article-1'},
                        'publishedOn': '2023-12-25T10:30:00Z'
                    },
                    {
                        'title': 'Article 2',
                        'slug': {'current': '/news/article-2'},
                        'publishedOn': '2023-12-24T10:30:00Z'
                    }
                ]
            }
        }
        
        articles = find_articles_in_json(data)
        
        assert len(articles) == 2
        titles = [article['title'] for article in articles]
        assert any('Article 1' in title for title in titles)
        assert any('Article 2' in title for title in titles)
    
    def test_no_articles_found(self):
        """記事が見つからない場合のテスト"""
        data = {
            'metadata': {
                'version': '1.0',
                'timestamp': '2023-12-25'
            }
        }
        
        articles = find_articles_in_json(data)
        assert len(articles) == 0


class TestExtractArticlesFromDom:
    """extract_articles_from_dom関数のテスト"""
    
    def test_news_links_extraction(self):
        """ニュースリンクの抽出テスト"""
        html_content = """
        <html>
            <body>
                <a href="/news/claude-4-announcement">Introducing Claude 4</a>
                <a href="/news/anthropic-funding">Anthropic raises funding</a>
                <a href="/about">About us</a>
                <a href="/news/ai-safety">AI Safety research</a>
            </body>
        </html>
        """
        
        articles = extract_articles_from_dom(html_content, "https://www.anthropic.com/news")
        
        assert len(articles) >= 3  # 3つのニュースリンクが見つかるはず
        
        links = [article['link'] for article in articles]
        assert any('/news/claude-4-announcement' in link for link in links)
        assert any('/news/anthropic-funding' in link for link in links)
        assert any('/news/ai-safety' in link for link in links)
        
        # About usリンクは含まれていないことを確認
        assert not any('/about' in link for link in links)
    
    def test_duplicate_removal(self):
        """重複記事の除去テスト"""
        html_content = """
        <html>
            <body>
                <a href="/news/same-article">Same Article Title</a>
                <a href="/news/same-article">Same Article Title</a>
                <a href="/news/different-article">Different Article</a>
            </body>
        </html>
        """
        
        articles = extract_articles_from_dom(html_content, "https://www.anthropic.com/news")
        
        # 重複が除去されて2記事になるはず
        assert len(articles) == 2
        
        links = [article['link'] for article in articles]
        unique_links = set(links)
        assert len(unique_links) == 2
    
    def test_empty_html(self):
        """空のHTMLのテスト"""
        html_content = "<html><body></body></html>"
        
        articles = extract_articles_from_dom(html_content, "https://www.anthropic.com/news")
        
        assert len(articles) == 0