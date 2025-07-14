#!/usr/bin/env python3
"""
テストモジュール: Anthropic RSS生成の統合テスト
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import sys
import xml.etree.ElementTree as ET

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from scripts.generate_anthropic_rss import main


class TestAnthropicMainFunction:
    """Anthropic RSS生成のmain関数統合テスト"""
    
    @patch('scripts.generate_anthropic_rss.scrape_anthropic_news')
    @patch('scripts.generate_anthropic_rss.os.makedirs')
    def test_successful_anthropic_rss_generation(self, mock_makedirs, mock_scrape):
        """正常なAnthropic RSS生成の統合テスト"""
        # スクレイピング結果をモック
        mock_articles = [
            {
                'title': 'Claude 4の発表',
                'link': 'https://www.anthropic.com/news/claude-4',
                'description': 'Anthropicが新しいClaude 4を発表しました',
                'pubDate': '01 Jan 2023 12:00:00 +0000'
            },
            {
                'title': 'AI安全性研究の進展',
                'link': 'https://www.anthropic.com/news/ai-safety',
                'description': 'AI安全性の研究で新たな進展がありました',
                'pubDate': '02 Jan 2023 12:00:00 +0000'
            }
        ]
        mock_scrape.return_value = mock_articles
        
        # 一時ディレクトリでテスト実行
        with tempfile.TemporaryDirectory() as temp_dir:
            # カレントディレクトリを一時ディレクトリに変更
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                
                # main関数実行
                main()
                
                # distディレクトリが作成されたことを確認
                mock_makedirs.assert_called_with('dist', exist_ok=True)
                
                # RSSファイルが生成されたことを確認
                rss_file_path = os.path.join('dist', 'anthropic-news.xml')
                assert os.path.exists(rss_file_path)
                
                # RSS内容の確認
                with open(rss_file_path, 'r', encoding='utf-8') as f:
                    rss_content = f.read()
                
                # XML形式として解析可能であることを確認
                root = ET.fromstring(rss_content)
                assert root.tag == 'rss'
                assert root.get('version') == '2.0'
                
                # チャンネル情報の確認
                channel = root.find('channel')
                assert channel is not None
                
                title = channel.find('title')
                assert title is not None
                assert title.text == 'Anthropic News'
                
                # アイテム数の確認
                items = channel.findall('item')
                assert len(items) == 2
                
                # Anthropic固有の内容確認
                assert items[0].find('title').text == 'Claude 4の発表'
                assert items[0].find('link').text == 'https://www.anthropic.com/news/claude-4'
                assert items[1].find('title').text == 'AI安全性研究の進展'
                assert items[1].find('link').text == 'https://www.anthropic.com/news/ai-safety'
                
                # 日本語が正しく含まれていることを確認
                assert 'Claude 4の発表' in rss_content
                assert 'AI安全性研究' in rss_content
                
            finally:
                os.chdir(original_cwd)
    
    @patch('scripts.generate_anthropic_rss.scrape_anthropic_news')
    @patch('scripts.generate_anthropic_rss.os.makedirs')
    def test_empty_anthropic_articles_handling(self, mock_makedirs, mock_scrape):
        """Anthropic記事が空の場合の処理テスト"""
        # 空の記事リストを返す
        mock_scrape.return_value = []
        
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                
                main()
                
                # RSSファイルが生成されることを確認
                rss_file_path = os.path.join('dist', 'anthropic-news.xml')
                assert os.path.exists(rss_file_path)
                
                # RSS内容の確認（アイテムが0個）
                with open(rss_file_path, 'r', encoding='utf-8') as f:
                    rss_content = f.read()
                
                root = ET.fromstring(rss_content)
                channel = root.find('channel')
                items = channel.findall('item')
                assert len(items) == 0
                
                # Anthropic固有のメタデータが含まれていることを確認
                assert 'Anthropic News' in rss_content
                assert 'https://www.anthropic.com/news' in rss_content
                
            finally:
                os.chdir(original_cwd)
    
    @patch('scripts.generate_anthropic_rss.scrape_anthropic_news')
    @patch('scripts.generate_anthropic_rss.os.makedirs')
    def test_anthropic_scraping_failure_handling(self, mock_makedirs, mock_scrape):
        """Anthropicスクレイピング失敗時の処理テスト"""
        # スクレイピングでエラーが発生
        mock_scrape.side_effect = Exception("Anthropic scraping failed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                
                # エラーが発生してもmain関数は例外を上げない
                with pytest.raises(Exception) as exc_info:
                    main()
                
                assert "Anthropic scraping failed" in str(exc_info.value)
                
            finally:
                os.chdir(original_cwd)
    
    @patch('scripts.generate_anthropic_rss.scrape_anthropic_news')
    def test_anthropic_unicode_handling(self, mock_scrape):
        """Anthropic特有のUnicode文字を含むRSSファイルの書き込みテスト"""
        # 日本語とAnthropic特有のキーワードを含む記事データ
        mock_articles = [
            {
                'title': 'Claude 4 リリース - Constitutional AI技術',
                'link': 'https://www.anthropic.com/news/claude-4-constitutional-ai',
                'description': 'AnthropicがConstitutional AIを使った新しいClaude 4モデルを発表。RLHF技術も改良されています。',
                'pubDate': '01 Jan 2023 12:00:00 +0000'
            }
        ]
        mock_scrape.return_value = mock_articles
        
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                
                main()
                
                # ファイルの内容確認
                rss_file_path = os.path.join('dist', 'anthropic-news.xml')
                with open(rss_file_path, 'r', encoding='utf-8') as f:
                    rss_content = f.read()
                
                # Anthropic特有の日本語+英語混在コンテンツが正しく含まれていることを確認
                assert 'Claude 4 リリース' in rss_content
                assert 'Constitutional AI技術' in rss_content
                assert 'RLHF技術' in rss_content
                assert 'Anthropic' in rss_content
                
                # XML として正しく解析できることを確認
                root = ET.fromstring(rss_content)
                channel = root.find('channel')
                item = channel.find('item')
                title = item.find('title').text
                description = item.find('description').text
                
                assert 'Constitutional AI技術' in title
                assert 'RLHF技術' in description
                
            finally:
                os.chdir(original_cwd)


class TestAnthropicEndToEndWorkflow:
    """Anthropic RSS生成のエンドツーエンドワークフローテスト"""
    
    @patch('scripts.generate_anthropic_rss.setup_driver')
    @patch('scripts.generate_anthropic_rss.extract_articles_from_json')
    def test_complete_anthropic_workflow_mock(self, mock_extract_json, mock_setup_driver):
        """完全なAnthropic RSSワークフローのモックテスト"""
        # Seleniumドライバーのモック
        mock_driver = Mock()
        mock_driver.page_source = """
        <html>
            <head>
                <script type="application/json">
                {
                    "articles": [
                        {
                            "title": "Anthropic's Latest AI Research",
                            "slug": {"current": "/news/anthropic-latest-research"},
                            "publishedOn": "2023-12-25T10:30:00Z",
                            "description": "Breakthrough in AI alignment and safety research"
                        }
                    ]
                }
                </script>
            </head>
        </html>
        """
        mock_driver.find_elements.return_value = [Mock()] * 15
        mock_setup_driver.return_value = mock_driver
        
        # JSON抽出のモック
        mock_articles = [
            {
                'title': "Anthropic's Latest AI 研究",
                'link': 'https://www.anthropic.com/news/anthropic-latest-research',
                'description': 'Breakthrough in AI alignment and safety 研究',
                'pubDate': '25 Dec 2023 10:30:00 +0000'
            }
        ]
        mock_extract_json.return_value = mock_articles
        
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                
                # main関数の実行
                main()
                
                # ドライバーが正しく呼ばれたことを確認
                mock_setup_driver.assert_called_once()
                mock_driver.get.assert_called_once_with("https://www.anthropic.com/news")
                mock_driver.quit.assert_called_once()
                
                # JSON抽出が呼ばれたことを確認
                mock_extract_json.assert_called_once()
                
                # RSSファイルが生成されたことを確認
                rss_file_path = os.path.join('dist', 'anthropic-news.xml')
                assert os.path.exists(rss_file_path)
                
                # 生成されたRSSの内容確認
                with open(rss_file_path, 'r', encoding='utf-8') as f:
                    rss_content = f.read()
                
                assert "Anthropic's Latest AI 研究" in rss_content
                assert 'https://www.anthropic.com/news/anthropic-latest-research' in rss_content
                assert 'safety 研究' in rss_content
                
                # XMLの構造確認
                root = ET.fromstring(rss_content)
                assert root.tag == 'rss'
                channel = root.find('channel')
                assert channel.find('title').text == 'Anthropic News'
                assert 'anthropic.com' in channel.find('link').text
                
            finally:
                os.chdir(original_cwd)
    
    @patch('scripts.generate_anthropic_rss.scrape_anthropic_news')
    def test_anthropic_rss_metadata_validation(self, mock_scrape):
        """生成されたAnthropic RSSのメタデータ検証"""
        # Anthropic特有の記事データ
        mock_articles = [
            {
                'title': 'Claude API Updates',
                'link': 'https://www.anthropic.com/news/claude-api-updates',
                'description': 'New features for Claude API developers',
                'pubDate': '01 Jan 2023 12:00:00 +0000'
            }
        ]
        mock_scrape.return_value = mock_articles
        
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                
                main()
                
                rss_file_path = os.path.join('dist', 'anthropic-news.xml')
                with open(rss_file_path, 'r', encoding='utf-8') as f:
                    rss_content = f.read()
                
                root = ET.fromstring(rss_content)
                channel = root.find('channel')
                
                # Anthropic固有のメタデータ確認
                assert channel.find('title').text == 'Anthropic News'
                assert channel.find('link').text == 'https://www.anthropic.com/news'
                assert 'Anthropic公式サイト' in channel.find('description').text
                assert channel.find('language').text == 'ja'
                
                # lastBuildDateが設定されていることを確認
                last_build_date = channel.find('lastBuildDate')
                assert last_build_date is not None
                assert '+0000' in last_build_date.text
                
                # 記事のURL構造がAnthropicドメインであることを確認
                items = channel.findall('item')
                for item in items:
                    link = item.find('link').text
                    assert 'anthropic.com' in link
                    assert '/news/' in link
                
            finally:
                os.chdir(original_cwd)