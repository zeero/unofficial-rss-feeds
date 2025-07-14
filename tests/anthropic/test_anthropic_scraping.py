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
    extract_articles_from_dom
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
        
        # 1回目の呼び出し（ChromeDriverManager）は失敗、2回目（システムChrome）は成功
        mock_driver = Mock()
        mock_chrome.side_effect = [Exception("First call failed"), mock_driver]
        
        result = setup_driver()
        
        # 2回呼ばれることを確認（最初はService付き、次はオプションのみ）
        assert mock_chrome.call_count == 2
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