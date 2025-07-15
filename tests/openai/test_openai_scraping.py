"""
OpenAI ChatGPT Release Notes固有のスクレイピング機能をテストするモジュール。
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import sys
import os

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from scripts.generate_openai_rss import (
    parse_openai_date,
    extract_openai_articles,
    scrape_openai_releases,
    translate_simple
)

@pytest.mark.openai
class TestOpenAIDateParsing:
    """OpenAI固有の日付フォーマット解析テスト"""
    
    def test_parse_standard_date_format(self):
        """標準的な日付フォーマットのテスト"""
        result = parse_openai_date("June 24, 2025")
        assert "24 Jun 2025" in result
        assert "+0000" in result
    
    def test_parse_abbreviated_month_format(self):
        """月の略称フォーマットのテスト"""
        result = parse_openai_date("May 15, 2025")
        assert "15 May 2025" in result
    
    def test_parse_invalid_date_returns_current(self):
        """無効な日付の場合は現在日時を返すテスト"""
        result = parse_openai_date("Invalid Date")
        current_year = str(datetime.now().year)
        assert current_year in result
    
    def test_parse_empty_date_returns_current(self):
        """空の日付の場合は現在日時を返すテスト"""
        result = parse_openai_date("")
        assert "+0000" in result

@pytest.mark.openai
class TestOpenAIHTMLStructureParsing:
    """OpenAI固有のHTML構造解析テスト"""
    
    def test_extract_articles_from_structured_html(self):
        """構造化されたHTMLからの記事抽出テスト"""
        html_content = """
        <div class="prose">
            <h1 id="h_d015741d75">June 24, 2025</h1>
            <h2 id="h_fab7aa1610"><b>Chat search connectors (Pro)</b></h2>
            <p class="no-margin">Pro users are now able to use chat search connectors.</p>
            <h2 id="h_f2f58eebf7"><b>Project file limit increased (Pro)</b></h2>
            <p class="no-margin">Projects can now support 40 uploaded files, up from 20.</p>
            <h1 id="h_9e009b6b34">June 18, 2025</h1>
            <h2 id="h_2e5af39d39"><b>ChatGPT record mode</b></h2>
            <p class="no-margin">Capture meetings, brainstorms, or voice notes.</p>
        </div>
        """
        
        articles = extract_openai_articles(html_content, "https://help.openai.com")
        
        # 3つの記事が抽出されることを確認
        assert len(articles) == 3
        
        # 最初の記事の検証
        first_article = articles[0]
        assert "Chat search connectors" in first_article['title']
        assert "Pro" in first_article['description']  # 翻訳後の内容も考慮
        assert first_article['link'] == "https://help.openai.com"
        assert "Jun 2025" in first_article['pubDate']
    
    def test_extract_articles_with_list_content(self):
        """リスト形式のコンテンツを含む記事の抽出テスト"""
        html_content = """
        <div class="prose">
            <h1 id="h_test">May 1, 2025</h1>
            <h2 id="h_feature"><b>New Features</b></h2>
            <p class="no-margin">Multiple improvements:</p>
            <ul>
                <li><p class="no-margin">Feature A improvement</p></li>
                <li><p class="no-margin">Feature B enhancement</p></li>
                <li><p class="no-margin">Feature C addition</p></li>
            </ul>
        </div>
        """
        
        articles = extract_openai_articles(html_content, "https://help.openai.com")
        
        assert len(articles) == 1
        article = articles[0]
        
        # リストアイテムが説明に含まれていることを確認（翻訳後も考慮）
        assert "• Feature A" in article['description']
        assert "• Feature B" in article['description']
    
    def test_extract_articles_empty_content(self):
        """空のコンテンツの場合のテスト"""
        html_content = "<div></div>"
        articles = extract_openai_articles(html_content, "https://help.openai.com")
        assert len(articles) == 0
    
    def test_extract_articles_no_prose_class(self):
        """prose classが見つからない場合のテスト"""
        html_content = """
        <div class="other-class">
            <h1>June 24, 2025</h1>
            <h2>Some Feature</h2>
        </div>
        """
        articles = extract_openai_articles(html_content, "https://help.openai.com")
        assert len(articles) == 0

@pytest.mark.openai
class TestOpenAITranslation:
    """OpenAI固有の翻訳機能テスト"""
    
    def test_translate_openai_specific_terms(self):
        """OpenAI固有の用語翻訳テスト"""
        text = "ChatGPT release notes with new features"
        result = translate_simple(text)
        
        assert "ChatGPT" in result
        assert "リリースノート" in result
        assert "機能" in result
    
    def test_translate_preserves_technical_terms(self):
        """技術用語が適切に保持されるテスト"""
        text = "GPT-4 model with AI capabilities"
        result = translate_simple(text)
        
        assert "GPT-4" in result
        assert "AI" in result
        assert "モデル" in result

@pytest.mark.openai
@pytest.mark.slow
class TestOpenAIWebScraping:
    """OpenAI Webスクレイピング統合テスト（実際のネットワークアクセスを含む）"""
    
    @patch('scripts.generate_openai_rss.setup_driver')
    @patch('scripts.generate_openai_rss.extract_openai_articles')
    def test_successful_scraping_with_mocked_driver(self, mock_extract, mock_setup):
        """Seleniumドライバーをモックした成功ケーステスト"""
        # モックドライバーの設定
        mock_driver = Mock()
        mock_driver.page_source = "<html><body>Mock content</body></html>"
        mock_setup.return_value = mock_driver
        
        # 記事抽出結果のモック
        mock_articles = [
            {
                'title': 'テスト記事 1',
                'link': 'https://help.openai.com/test1',
                'description': 'テスト説明 1',
                'pubDate': '01 Jun 2025 12:00:00 +0000'
            }
        ]
        mock_extract.return_value = mock_articles
        
        # テスト実行
        result = scrape_openai_releases()
        
        # 検証
        assert len(result) == 1
        assert result[0]['title'] == 'テスト記事 1'
        
        # ドライバーの適切な呼び出し確認
        mock_setup.assert_called_once()
        mock_driver.get.assert_called_once()
        mock_driver.quit.assert_called_once()
    
    @patch('scripts.generate_openai_rss.setup_driver')
    def test_scraping_failure_returns_fallback(self, mock_setup):
        """スクレイピング失敗時のフォールバック記事テスト"""
        # ドライバー設定でエラーを発生させる
        mock_setup.side_effect = Exception("Driver setup failed")
        
        result = scrape_openai_releases()
        
        # フォールバック記事が返されることを確認
        assert len(result) == 1
        assert "エラー" in result[0]['title']
        assert "公式サイト" in result[0]['description']
    
    @patch('scripts.generate_openai_rss.setup_driver')
    def test_scraping_with_no_articles_returns_fallback(self, mock_setup):
        """記事が見つからない場合のフォールバックテスト"""
        # モックドライバーの設定（記事が見つからない）
        mock_driver = Mock()
        mock_driver.page_source = "<html><body>No articles found</body></html>"
        mock_setup.return_value = mock_driver
        
        with patch('scripts.generate_openai_rss.extract_openai_articles') as mock_extract:
            mock_extract.return_value = []  # 空の記事リスト
            
            result = scrape_openai_releases()
            
            # フォールバック記事が返されることを確認
            assert len(result) == 1
            assert "最新リリースノート" in result[0]['title']

if __name__ == "__main__":
    pytest.main([__file__, "-v"])