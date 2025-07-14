#!/usr/bin/env python3
"""
pytest設定とフィクスチャ定義
全テストで共通して使用される設定とモックを定義
"""

import pytest
import sys
import os
from unittest.mock import Mock, patch
import tempfile
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


@pytest.fixture
def sample_article():
    """サンプル記事データのフィクスチャ"""
    return {
        'title': 'Test Article',
        'link': 'https://example.com/test-article',
        'description': 'This is a test article description',
        'pubDate': '01 Jan 2023 12:00:00 +0000'
    }


@pytest.fixture
def sample_articles_list():
    """複数のサンプル記事データのフィクスチャ"""
    return [
        {
            'title': 'First Article',
            'link': 'https://example.com/first',
            'description': 'First article description',
            'pubDate': '01 Jan 2023 12:00:00 +0000'
        },
        {
            'title': 'Second Article',
            'link': 'https://example.com/second',
            'description': 'Second article description',
            'pubDate': '02 Jan 2023 12:00:00 +0000'
        }
    ]


@pytest.fixture
def anthropic_sample_articles():
    """Anthropic特有のサンプル記事データ"""
    return [
        {
            'title': 'Claude 4の発表',
            'link': 'https://www.anthropic.com/news/claude-4-announcement',
            'description': 'Anthropicが新しいClaude 4モデルを発表しました',
            'pubDate': '01 Jan 2023 12:00:00 +0000'
        },
        {
            'title': 'Constitutional AI研究の進展',
            'link': 'https://www.anthropic.com/news/constitutional-ai-progress',
            'description': 'Constitutional AIの研究で新たな成果を発表',
            'pubDate': '02 Jan 2023 12:00:00 +0000'
        }
    ]


@pytest.fixture
def mock_selenium_driver():
    """Seleniumドライバーのモックフィクスチャ"""
    driver = Mock()
    driver.page_source = "<html><body>Mock content</body></html>"
    driver.find_elements.return_value = [Mock()] * 15
    driver.get = Mock()
    driver.quit = Mock()
    return driver


@pytest.fixture
def mock_webdriver_wait():
    """WebDriverWaitのモックフィクスチャ"""
    wait_mock = Mock()
    wait_instance = Mock()
    wait_instance.until.return_value = True
    wait_mock.return_value = wait_instance
    return wait_mock


@pytest.fixture
def temp_working_directory():
    """一時作業ディレクトリのフィクスチャ"""
    with tempfile.TemporaryDirectory() as temp_dir:
        original_cwd = os.getcwd()
        try:
            os.chdir(temp_dir)
            yield temp_dir
        finally:
            os.chdir(original_cwd)


@pytest.fixture
def sample_html_with_articles():
    """記事を含むHTMLサンプル"""
    return """
    <html>
        <head>
            <script type="application/json">
            {
                "articles": [
                    {
                        "title": "Sample Article from HTML",
                        "slug": {"current": "/news/sample-article"},
                        "publishedOn": "2023-12-25T10:30:00Z",
                        "description": "This is a sample article from HTML"
                    }
                ]
            }
            </script>
        </head>
        <body>
            <a href="/news/sample-article">Sample Article from HTML</a>
        </body>
    </html>
    """


@pytest.fixture
def sample_empty_html():
    """空のHTMLサンプル"""
    return "<html><head></head><body></body></html>"


@pytest.fixture
def mock_current_time():
    """現在時刻のモック"""
    return datetime(2023, 12, 25, 12, 0, 0)


@pytest.fixture(autouse=True)
def mock_print_output(capfd):
    """print出力のキャプチャフィクスチャ（自動適用）"""
    yield capfd


# マーカー定義
def pytest_configure(config):
    """pytest設定"""
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "anthropic: mark test as Anthropic-specific"
    )
    config.addinivalue_line(
        "markers", "common: mark test as common functionality"
    )


# テスト実行時の共通設定
def pytest_runtest_setup(item):
    """各テスト実行前の設定"""
    # Seleniumテストの場合は追加の設定を行う
    if "selenium" in item.nodeid.lower():
        # Seleniumテスト用の環境変数設定など
        os.environ.setdefault('SELENIUM_HEADLESS', '1')


def pytest_runtest_teardown(item):
    """各テスト実行後のクリーンアップ"""
    # テスト後のクリーンアップ処理
    pass


# カスタムアサーション関数
def assert_valid_rss_structure(rss_element):
    """RSS構造の妥当性をチェックするヘルパー関数"""
    assert rss_element.tag == 'rss'
    assert rss_element.get('version') == '2.0'
    
    channel = rss_element.find('channel')
    assert channel is not None
    
    # 必須要素の確認
    required_elements = ['title', 'link', 'description']
    for element_name in required_elements:
        element = channel.find(element_name)
        assert element is not None
        assert element.text is not None
        assert len(element.text.strip()) > 0


def assert_valid_article_structure(article):
    """記事データ構造の妥当性をチェックするヘルパー関数"""
    required_fields = ['title', 'link', 'description', 'pubDate']
    for field in required_fields:
        assert field in article
        assert article[field] is not None
        assert len(str(article[field]).strip()) > 0
    
    # URLの形式チェック
    assert article['link'].startswith('http')
    
    # 日付形式のチェック
    assert '+0000' in article['pubDate']


# pytest用のヘルパー関数をグローバルに追加
pytest.assert_valid_rss_structure = assert_valid_rss_structure
pytest.assert_valid_article_structure = assert_valid_article_structure