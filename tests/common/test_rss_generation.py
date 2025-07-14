#!/usr/bin/env python3
"""
テストモジュール: RSS生成機能の共通ユニットテスト
全RSSフィード生成サービスで共有される機能をテスト
"""

import pytest
import xml.etree.ElementTree as ET
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from scripts.generate_anthropic_rss import (
    translate_simple,
    format_date,
    generate_rss_feed
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
    
    def test_partial_match_handling(self):
        """部分一致問題のテスト (news vs new)"""
        text = "This is news about new features"
        result = translate_simple(text)
        
        # "news"が正しく"ニュース"に翻訳され、"new"が"新しい"に翻訳される
        assert "ニュース" in result
        assert "新しい" in result
        # "新しいs"のような誤った翻訳がないことを確認
        assert "新しいs" not in result


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
    
    def test_rss_feed_validation(self):
        """生成されたRSSフィードの妥当性検証"""
        sample_articles = [
            {
                'title': 'Validation Test',
                'link': 'https://example.com/test',
                'description': 'Test description',
                'pubDate': '01 Jan 2023 12:00:00 +0000'
            }
        ]
        
        rss_element = generate_rss_feed(sample_articles)
        
        # RSS 2.0仕様に準拠していることを確認
        assert rss_element.tag == 'rss'
        assert rss_element.get('version') == '2.0'
        
        channel = rss_element.find('channel')
        assert channel is not None
        
        # 必須要素の存在確認
        required_elements = ['title', 'link', 'description']
        for element_name in required_elements:
            element = channel.find(element_name)
            assert element is not None
            assert element.text is not None
            assert len(element.text.strip()) > 0
        
        # アイテムの妥当性確認
        items = channel.findall('item')
        assert len(items) == 1
        
        item = items[0]
        for element_name in required_elements + ['pubDate']:
            element = item.find(element_name)
            assert element is not None
            assert element.text is not None
            assert len(element.text.strip()) > 0
    
    def test_unicode_handling(self):
        """Unicode文字の処理テスト"""
        articles = [{
            'title': 'Claude 4の発表 - 最新のAI技術',
            'link': 'https://example.com/japanese',
            'description': 'Anthropicが新しいClaude 4モデルを発表しました。日本語対応も強化されています。',
            'pubDate': '01 Jan 2023 12:00:00 +0000'
        }]
        
        rss_element = generate_rss_feed(articles)
        channel = rss_element.find("channel")
        item = channel.find("item")
        
        # 日本語が正しく処理されることを確認
        title = item.find("title").text
        description = item.find("description").text
        
        assert "Claude 4の発表" in title
        assert "最新のAI技術" in title
        assert "日本語対応" in description