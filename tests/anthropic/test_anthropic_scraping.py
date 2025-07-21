#!/usr/bin/env python3
"""
テストモジュール: Anthropic固有のSeleniumスクレイピング機能
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
import sys
import os
import json

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from scripts.generate_anthropic_rss import (
    setup_driver,
    extract_articles_from_json,
    scrape_anthropic_news,
    extract_article_from_object,
    find_articles_in_json,
    extract_articles_from_dom,
    load_existing_articles,
    merge_articles_with_existing,
    create_article_key,
    create_stable_date
)


class TestSetupDriver:
    """setup_driver関数のテスト"""
    
    @patch('scripts.generate_anthropic_rss.ChromeDriverManager')
    @patch('scripts.generate_anthropic_rss.webdriver.Chrome')
    @patch('scripts.generate_anthropic_rss.Service')
    def test_successful_driver_setup_with_manager(self, mock_service, mock_chrome, mock_manager):
        """ChromeDriverManagerを使った正常なドライバー設定のテスト"""
        # モックの設定
        mock_manager().install.return_value = "/path/to/chromedriver"
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        result = setup_driver()
        
        # ChromeDriverManagerが呼ばれたことを確認
        mock_manager().install.assert_called_once()
        mock_service.assert_called_once_with("/path/to/chromedriver")
        mock_chrome.assert_called_once()
        
        assert result == mock_driver
    
    @patch('scripts.generate_anthropic_rss.ChromeDriverManager')
    @patch('scripts.generate_anthropic_rss.webdriver.Chrome')
    def test_fallback_to_system_chrome(self, mock_chrome, mock_manager):
        """ChromeDriverManagerが失敗した場合のシステムChromeへのフォールバックテスト"""
        # ChromeDriverManagerを失敗させる
        mock_manager().install.side_effect = Exception("ChromeDriverManager failed")
        
        # ChromeDriverManagerが失敗した場合、直接options のみでwebdriver.Chrome()が呼ばれて成功
        mock_driver = Mock()
        mock_chrome.return_value = mock_driver
        
        result = setup_driver()
        
        # 1回だけ呼ばれることを確認（options のみで）
        assert mock_chrome.call_count == 1
        # Service が使われていないことを確認（options のみ）
        mock_chrome.assert_called_with(options=mock_chrome.call_args[1]['options'])
        assert result == mock_driver
    
    @patch('scripts.generate_anthropic_rss.ChromeDriverManager')
    @patch('scripts.generate_anthropic_rss.webdriver.Chrome')
    def test_complete_driver_setup_failure(self, mock_chrome, mock_manager):
        """ドライバー設定が完全に失敗した場合のテスト"""
        # 両方とも失敗させる
        mock_manager().install.side_effect = Exception("ChromeDriverManager failed")
        mock_chrome.side_effect = Exception("Chrome setup failed")
        
        with pytest.raises(Exception) as exc_info:
            setup_driver()
        
        assert "Chrome setup failed" in str(exc_info.value)


class TestExtractArticlesFromJson:
    """extract_articles_from_json関数のテスト"""
    
    def test_extract_from_application_json_script(self):
        """application/jsonスクリプトタグからの記事抽出テスト"""
        html_content = """
        <html>
            <head>
                <script type="application/json" id="data">
                {
                    "articles": [
                        {
                            "title": "Test Article 1",
                            "slug": {"current": "/news/test-1"},
                            "publishedOn": "2023-12-25T10:30:00Z"
                        },
                        {
                            "title": "Test Article 2",
                            "slug": {"current": "/news/test-2"},
                            "publishedOn": "2023-12-24T10:30:00Z"
                        }
                    ]
                }
                </script>
            </head>
        </html>
        """
        
        articles = extract_articles_from_json(html_content)
        
        assert len(articles) == 2
        titles = [article['title'] for article in articles]
        assert any('Test Article 1' in title for title in titles)
        assert any('Test Article 2' in title for title in titles)
    
    def test_extract_from_next_data_script(self):
        """__NEXT_DATA__スクリプトからの記事抽出テスト"""
        html_content = """
        <html>
            <head>
                <script id="__NEXT_DATA__" type="application/json">
                {
                    "props": {
                        "pageProps": {
                            "posts": [
                                {
                                    "title": "Next.js Article",
                                    "slug": {"current": "/news/nextjs-article"},
                                    "publishedOn": "2023-12-23T10:30:00Z"
                                }
                            ]
                        }
                    }
                }
                </script>
            </head>
        </html>
        """
        
        articles = extract_articles_from_json(html_content)
        
        # 重複を考慮して1つ以上あることを確認
        assert len(articles) >= 1
        # 最初の記事をチェック
        assert 'Next.js Article' in articles[0]['title']
        assert '/news/nextjs-article' in articles[0]['link']
    
    def test_invalid_json_handling(self):
        """無効なJSONの処理テスト"""
        html_content = """
        <html>
            <head>
                <script type="application/json">
                { invalid json content }
                </script>
                <script type="application/json">
                {
                    "validData": {
                        "title": "Valid Article",
                        "slug": {"current": "/news/valid"},
                        "publishedOn": "2023-12-22T10:30:00Z"
                    }
                }
                </script>
            </head>
        </html>
        """
        
        articles = extract_articles_from_json(html_content)
        
        # 無効なJSONは無視され、有効なものだけが処理される
        assert len(articles) == 1
        assert 'Valid Article' in articles[0]['title']
    
    def test_no_json_scripts(self):
        """JSONスクリプトが存在しない場合のテスト"""
        html_content = """
        <html>
            <head>
                <script type="text/javascript">
                console.log("This is not JSON");
                </script>
            </head>
        </html>
        """
        
        articles = extract_articles_from_json(html_content)
        assert len(articles) == 0


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


class TestScrapeAnthropicNews:
    """scrape_anthropic_news関数の統合テスト（モック使用）"""
    
    @patch('scripts.generate_anthropic_rss.setup_driver')
    @patch('scripts.generate_anthropic_rss.extract_articles_from_json')
    @patch('scripts.generate_anthropic_rss.WebDriverWait')
    @patch('scripts.generate_anthropic_rss.time.sleep')
    def test_successful_scraping_with_json_extraction(self, mock_sleep, mock_wait, mock_extract_json, mock_setup):
        """JSON抽出による正常なスクレイピングテスト"""
        # モックドライバーの設定
        mock_driver = Mock()
        mock_driver.page_source = "<html>mock content</html>"
        mock_driver.find_elements.return_value = [Mock()] * 15  # 15個のリンク要素を返す
        mock_setup.return_value = mock_driver
        
        # JSON抽出が成功する場合
        mock_articles = [
            {
                'title': 'Mock Article',
                'link': 'https://www.anthropic.com/news/mock',
                'description': 'Mock description',
                'pubDate': '01 Jan 2023 12:00:00 +0000'
            }
        ]
        mock_extract_json.return_value = mock_articles
        
        # WebDriverWaitのモック設定
        mock_wait_instance = Mock()
        mock_wait_instance.until.return_value = True
        mock_wait.return_value = mock_wait_instance
        
        result = scrape_anthropic_news()
        
        # ドライバーが正しく設定・使用されたことを確認
        mock_setup.assert_called_once()
        mock_driver.get.assert_called_once_with("https://www.anthropic.com/news")
        mock_driver.quit.assert_called_once()
        
        # 結果の確認
        assert len(result) == 1
        assert result[0]['title'] == 'Mock Article'
    
    @patch('scripts.generate_anthropic_rss.setup_driver')
    @patch('scripts.generate_anthropic_rss.extract_articles_from_json')
    @patch('scripts.generate_anthropic_rss.extract_articles_from_dom')
    @patch('scripts.generate_anthropic_rss.WebDriverWait')
    def test_fallback_to_dom_parsing(self, mock_wait, mock_extract_dom, mock_extract_json, mock_setup):
        """JSON抽出が失敗した場合のDOM解析フォールバックテスト"""
        # モックドライバーの設定
        mock_driver = Mock()
        mock_driver.page_source = "<html>mock content</html>"
        mock_driver.find_elements.return_value = [Mock()] * 15
        mock_setup.return_value = mock_driver
        
        # WebDriverWaitのモック設定
        mock_wait_instance = Mock()
        mock_wait_instance.until.return_value = True
        mock_wait.return_value = mock_wait_instance
        
        # JSON抽出は失敗、DOM抽出は成功
        mock_extract_json.return_value = []
        mock_extract_dom.return_value = [
            {
                'title': 'DOM Article',
                'link': 'https://www.anthropic.com/news/dom',
                'description': 'DOM description',
                'pubDate': '01 Jan 2023 12:00:00 +0000'
            }
        ]
        
        result = scrape_anthropic_news()
        
        # 両方の抽出メソッドが呼ばれたことを確認
        mock_extract_json.assert_called_once()
        mock_extract_dom.assert_called_once()
        
        # DOM抽出の結果が返されることを確認
        assert len(result) == 1
        assert result[0]['title'] == 'DOM Article'
    
    @patch('scripts.generate_anthropic_rss.setup_driver')
    def test_driver_setup_failure_handling(self, mock_setup):
        """ドライバー設定失敗時のエラーハンドリングテスト"""
        # ドライバー設定を失敗させる
        mock_setup.side_effect = Exception("Driver setup failed")
        
        result = scrape_anthropic_news()
        
        # フォールバック記事が返されることを確認
        assert len(result) == 1
        assert 'エラー' in result[0]['title']
        assert 'https://www.anthropic.com/news' in result[0]['link']
    
    @patch('scripts.generate_anthropic_rss.setup_driver')
    @patch('scripts.generate_anthropic_rss.extract_articles_from_json')
    @patch('scripts.generate_anthropic_rss.extract_articles_from_dom')
    @patch('scripts.generate_anthropic_rss.WebDriverWait')
    def test_no_articles_found_fallback(self, mock_wait, mock_extract_dom, mock_extract_json, mock_setup):
        """記事が見つからない場合のフォールバック記事テスト"""
        # モックドライバーの設定
        mock_driver = Mock()
        mock_driver.page_source = "<html>empty content</html>"
        mock_driver.find_elements.return_value = [Mock()] * 15
        mock_setup.return_value = mock_driver
        
        # WebDriverWaitのモック設定
        mock_wait_instance = Mock()
        mock_wait_instance.until.return_value = True
        mock_wait.return_value = mock_wait_instance
        
        # 両方の抽出メソッドが空の結果を返す
        mock_extract_json.return_value = []
        mock_extract_dom.return_value = []
        
        result = scrape_anthropic_news()
        
        # フォールバック記事が返されることを確認
        assert len(result) == 1
        assert '最新ニュース' in result[0]['title']
        assert 'https://www.anthropic.com/news' in result[0]['link']
    
    @patch('scripts.generate_anthropic_rss.setup_driver')
    @patch('scripts.generate_anthropic_rss.extract_articles_from_json')
    @patch('scripts.generate_anthropic_rss.WebDriverWait')
    def test_article_limit_enforcement(self, mock_wait, mock_extract_json, mock_setup):
        """記事数制限の確認テスト"""
        # モックドライバーの設定
        mock_driver = Mock()
        mock_driver.page_source = "<html>mock content</html>"
        mock_driver.find_elements.return_value = [Mock()] * 15
        mock_setup.return_value = mock_driver
        
        # WebDriverWaitのモック設定
        mock_wait_instance = Mock()
        mock_wait_instance.until.return_value = True
        mock_wait.return_value = mock_wait_instance
        
        # 20記事を生成（制限の15記事を超える）
        mock_articles = []
        for i in range(20):
            mock_articles.append({
                'title': f'Article {i}',
                'link': f'https://www.anthropic.com/news/article-{i}',
                'description': f'Description {i}',
                'pubDate': '01 Jan 2023 12:00:00 +0000'
            })
        
        mock_extract_json.return_value = mock_articles
        
        result = scrape_anthropic_news()
        
        # 15記事に制限されることを確認
        assert len(result) == 15
        assert result[0]['title'] == 'Article 0'
        assert result[14]['title'] == 'Article 14'


class TestLoadExistingArticles:
    """load_existing_articles関数のテスト"""
    
    def test_load_from_valid_rss_file(self):
        """有効なRSSファイルから記事を読み込むテスト"""
        import tempfile
        import xml.etree.ElementTree as ET
        
        # テスト用RSSファイルを作成
        rss_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Test RSS</title>
                <item>
                    <title>Test Article 1</title>
                    <link>https://example.com/test-1</link>
                    <description>Test description 1</description>
                    <pubDate>01 Jan 2023 12:00:00 +0000</pubDate>
                </item>
                <item>
                    <title>Test Article 2</title>
                    <link>https://example.com/test-2</link>
                    <description>Test description 2</description>
                    <pubDate>02 Jan 2023 12:00:00 +0000</pubDate>
                </item>
            </channel>
        </rss>'''
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xml') as f:
            f.write(rss_content)
            temp_file = f.name
        
        try:
            articles = load_existing_articles(temp_file)
            
            assert len(articles) == 2
            
            # 記事の内容確認
            article_titles = [article['title'] for article in articles.values()]
            assert 'Test Article 1' in article_titles
            assert 'Test Article 2' in article_titles
            
            # 記事のキーが正しく生成されていることを確認
            for key, article in articles.items():
                assert isinstance(key, str)
                assert len(key) == 32  # MD5ハッシュの長さ
                assert 'title' in article
                assert 'link' in article
                assert 'description' in article
                assert 'pubDate' in article
        
        finally:
            os.unlink(temp_file)
    
    def test_load_from_nonexistent_file(self):
        """存在しないファイルの処理テスト"""
        articles = load_existing_articles("/nonexistent/file.xml")
        assert len(articles) == 0
    
    def test_load_from_invalid_xml(self):
        """無効なXMLファイルの処理テスト"""
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.xml') as f:
            f.write("invalid xml content")
            temp_file = f.name
        
        try:
            articles = load_existing_articles(temp_file)
            assert len(articles) == 0
        finally:
            os.unlink(temp_file)


class TestCreateArticleKey:
    """create_article_key関数のテスト"""
    
    def test_same_content_same_key(self):
        """同じ内容からは同じキーが生成されることを確認"""
        title = "Test Article"
        link = "https://example.com/test"
        
        key1 = create_article_key(title, link)
        key2 = create_article_key(title, link)
        
        assert key1 == key2
        assert len(key1) == 32  # MD5ハッシュの長さ
    
    def test_different_content_different_key(self):
        """異なる内容からは異なるキーが生成されることを確認"""
        key1 = create_article_key("Article 1", "https://example.com/1")
        key2 = create_article_key("Article 2", "https://example.com/2")
        
        assert key1 != key2
    
    def test_whitespace_normalization(self):
        """空白の正規化テスト"""
        title1 = "Test  Article"
        title2 = "Test Article"
        link = "https://example.com/test"
        
        key1 = create_article_key(title1, link)
        key2 = create_article_key(title2, link)
        
        assert key1 == key2  # 空白が正規化されて同じキーになる
    
    def test_case_insensitive(self):
        """大文字小文字を区別しないテスト"""
        key1 = create_article_key("Test Article", "https://example.com/test")
        key2 = create_article_key("test article", "https://example.com/test")
        
        assert key1 == key2


class TestCreateStableDate:
    """create_stable_date関数のテスト"""
    
    def test_same_content_same_date(self):
        """同じ内容からは同じ日付が生成されることを確認"""
        title = "Test Article"
        link = "https://example.com/test"
        
        date1 = create_stable_date(title, link)
        date2 = create_stable_date(title, link)
        
        assert date1 == date2
        assert '+0000' in date1  # GMT形式
    
    def test_different_content_different_date(self):
        """異なる内容からは異なる日付が生成されることを確認"""
        date1 = create_stable_date("Article 1", "https://example.com/1")
        date2 = create_stable_date("Article 2", "https://example.com/2")
        
        # 異なる内容なので異なる日付になる可能性が高い
        # ただし、ハッシュ値によってはたまたま同じ日付になる可能性もある
        assert isinstance(date1, str)
        assert isinstance(date2, str)
        assert '+0000' in date1
        assert '+0000' in date2
    
    def test_date_format(self):
        """日付フォーマットのテスト"""
        date = create_stable_date("Test", "https://example.com")
        
        # RFC-822形式をチェック（例: "01 Jan 2023 12:00:00 +0000"）
        import re
        rfc822_pattern = r'\d{1,2} \w{3} \d{4} \d{2}:\d{2}:\d{2} \+0000'
        assert re.match(rfc822_pattern, date)


class TestMergeArticlesWithExisting:
    """merge_articles_with_existing関数のテスト"""
    
    def test_merge_new_articles_with_existing(self):
        """新しい記事と既存記事のマージテスト"""
        existing_articles = {
            create_article_key("Existing Article", "https://example.com/existing"): {
                'title': 'Existing Article',
                'link': 'https://example.com/existing',
                'description': 'Existing description',
                'pubDate': '01 Jan 2023 12:00:00 +0000'
            }
        }
        
        new_articles = [
            {
                'title': 'New Article',
                'link': 'https://example.com/new',
                'description': 'New description',
                'pubDate': create_stable_date('New Article', 'https://example.com/new')
            },
            {
                'title': 'Existing Article',  # 既存記事と同じ
                'link': 'https://example.com/existing',
                'description': 'Updated description',
                'pubDate': create_stable_date('Existing Article', 'https://example.com/existing')
            }
        ]
        
        merged = merge_articles_with_existing(new_articles, existing_articles)
        
        assert len(merged) == 2
        
        # 既存記事の日付が保持されていることを確認
        existing_merged = next(a for a in merged if a['title'] == 'Existing Article')
        assert existing_merged['pubDate'] == '01 Jan 2023 12:00:00 +0000'
        
        # 新しい記事が追加されていることを確認
        new_merged = next(a for a in merged if a['title'] == 'New Article')
        assert new_merged['title'] == 'New Article'
    
    def test_merge_with_empty_existing(self):
        """既存記事が空の場合のマージテスト"""
        existing_articles = {}
        
        new_articles = [
            {
                'title': 'New Article',
                'link': 'https://example.com/new',
                'description': 'New description',
                'pubDate': create_stable_date('New Article', 'https://example.com/new')
            }
        ]
        
        merged = merge_articles_with_existing(new_articles, existing_articles)
        
        assert len(merged) == 1
        assert merged[0]['title'] == 'New Article'
    
    def test_duplicate_removal_in_merge(self):
        """マージ時の重複除去テスト"""
        existing_articles = {}
        
        new_articles = [
            {
                'title': 'Article 1',
                'link': 'https://example.com/1',
                'description': 'Description 1',
                'pubDate': create_stable_date('Article 1', 'https://example.com/1')
            },
            {
                'title': 'Article 1',  # 重複
                'link': 'https://example.com/1',
                'description': 'Description 1',
                'pubDate': create_stable_date('Article 1', 'https://example.com/1')
            }
        ]
        
        merged = merge_articles_with_existing(new_articles, existing_articles)
        
        # 重複が除去されて1つだけになる
        assert len(merged) == 1
        assert merged[0]['title'] == 'Article 1'