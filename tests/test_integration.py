#!/usr/bin/env python3
"""
テストモジュール: 統合テスト（モック使用）
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
import os
import sys
import xml.etree.ElementTree as ET

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from scripts.generate_anthropic_rss import main


class TestMainFunction:
    """main関数の統合テスト"""
    
    @patch('scripts.generate_anthropic_rss.scrape_anthropic_news')
    @patch('scripts.generate_anthropic_rss.os.makedirs')
    def test_successful_rss_generation(self, mock_makedirs, mock_scrape):
        """正常なRSS生成の統合テスト"""
        # スクレイピング結果をモック
        mock_articles = [
            {
                'title': 'Test Article 1',
                'link': 'https://www.anthropic.com/news/test-1',
                'description': 'Test description 1',
                'pubDate': '01 Jan 2023 12:00:00 +0000'
            },
            {
                'title': 'Test Article 2',
                'link': 'https://www.anthropic.com/news/test-2',
                'description': 'Test description 2',
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
                
                # 各アイテムの内容確認
                assert items[0].find('title').text == 'Test Article 1'
                assert items[0].find('link').text == 'https://www.anthropic.com/news/test-1'
                assert items[1].find('title').text == 'Test Article 2'
                assert items[1].find('link').text == 'https://www.anthropic.com/news/test-2'
                
            finally:
                os.chdir(original_cwd)
    
    @patch('scripts.generate_anthropic_rss.scrape_anthropic_news')
    @patch('scripts.generate_anthropic_rss.os.makedirs')
    def test_empty_articles_handling(self, mock_makedirs, mock_scrape):
        """記事が空の場合の処理テスト"""
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
                
            finally:
                os.chdir(original_cwd)
    
    @patch('scripts.generate_anthropic_rss.scrape_anthropic_news')
    @patch('scripts.generate_anthropic_rss.os.makedirs')
    def test_scraping_failure_handling(self, mock_makedirs, mock_scrape):
        """スクレイピング失敗時の処理テスト"""
        # スクレイピングでエラーが発生
        mock_scrape.side_effect = Exception("Scraping failed")
        
        with tempfile.TemporaryDirectory() as temp_dir:
            original_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                
                # エラーが発生してもmain関数は例外を上げない
                with pytest.raises(Exception) as exc_info:
                    main()
                
                assert "Scraping failed" in str(exc_info.value)
                
            finally:
                os.chdir(original_cwd)
    
    @patch('scripts.generate_anthropic_rss.scrape_anthropic_news')
    def test_file_writing_with_unicode(self, mock_scrape):
        """Unicode文字を含むRSSファイルの書き込みテスト"""
        # 日本語を含む記事データ
        mock_articles = [
            {
                'title': 'Claude 4の発表 - 最新のAI技術',
                'link': 'https://www.anthropic.com/news/claude-4-japanese',
                'description': 'Anthropicが新しいClaude 4モデルを発表しました。日本語対応も強化されています。',
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
                
                # 日本語が正しく含まれていることを確認
                assert 'Claude 4の発表' in rss_content
                assert '最新のAI技術' in rss_content
                assert 'Anthropic' in rss_content
                assert '日本語対応' in rss_content
                
                # XML として正しく解析できることを確認
                root = ET.fromstring(rss_content)
                channel = root.find('channel')
                item = channel.find('item')
                assert '最新のAI技術' in item.find('title').text
                
            finally:
                os.chdir(original_cwd)


class TestEndToEndWorkflow:
    """エンドツーエンドワークフローのテスト"""
    
    @patch('scripts.generate_anthropic_rss.setup_driver')
    @patch('scripts.generate_anthropic_rss.extract_articles_from_json')
    def test_complete_workflow_mock(self, mock_extract_json, mock_setup_driver):
        """完全なワークフローのモックテスト"""
        # Seleniumドライバーのモック
        mock_driver = Mock()
        mock_driver.page_source = """
        <html>
            <head>
                <script type="application/json">
                {
                    "articles": [
                        {
                            "title": "Workflow Test Article",
                            "slug": {"current": "/news/workflow-test"},
                            "publishedOn": "2023-12-25T10:30:00Z",
                            "description": "This is a workflow test article"
                        }
                    ]
                }
                </script>
            </head>
        </html>
        """
        mock_setup_driver.return_value = mock_driver
        
        # JSON抽出のモック
        mock_articles = [
            {
                'title': 'Workflow Test Article',
                'link': 'https://www.anthropic.com/news/workflow-test',
                'description': 'This is a workflow test article',
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
                
                assert 'Workflow Test Article' in rss_content
                assert 'https://www.anthropic.com/news/workflow-test' in rss_content
                
            finally:
                os.chdir(original_cwd)
    
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
        
        # RSS生成関数を直接テスト
        from scripts.generate_anthropic_rss import generate_rss_feed
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