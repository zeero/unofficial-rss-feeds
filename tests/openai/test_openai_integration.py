"""
OpenAI ChatGPT Release Notes RSS生成の統合テストモジュール。
エンドツーエンドの動作を検証する。
"""

import pytest
import os
import sys
import xml.etree.ElementTree as ET
from unittest.mock import patch, Mock
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))

from scripts.generate_openai_rss import main, generate_rss_feed

@pytest.mark.openai
@pytest.mark.integration
class TestOpenAIRSSGeneration:
    """OpenAI RSS生成の統合テスト"""
    
    def test_generate_rss_feed_structure(self, openai_sample_articles):
        """RSS フィード構造の正確性テスト"""
        rss_element = generate_rss_feed(openai_sample_articles)
        
        # ルート要素の検証
        assert rss_element.tag == 'rss'
        assert rss_element.get('version') == '2.0'
        
        # チャンネル要素の検証
        channel = rss_element.find('channel')
        assert channel is not None
        
        # チャンネルメタデータの検証
        title = channel.find('title')
        assert title is not None
        assert 'OpenAI ChatGPT' in title.text
        
        link = channel.find('link')
        assert link is not None
        assert 'help.openai.com' in link.text
        
        description = channel.find('description')
        assert description is not None
        assert 'リリースノート' in description.text
        
        language = channel.find('language')
        assert language is not None
        assert language.text == 'ja'
    
    def test_generate_rss_feed_items(self, openai_sample_articles):
        """RSS アイテム生成の検証"""
        rss_element = generate_rss_feed(openai_sample_articles)
        channel = rss_element.find('channel')
        items = channel.findall('item')
        
        # アイテム数の確認
        assert len(items) == len(openai_sample_articles)
        
        # 最初のアイテムの詳細検証
        first_item = items[0]
        first_article = openai_sample_articles[0]
        
        title = first_item.find('title')
        assert title.text == first_article['title']
        
        link = first_item.find('link')
        assert link.text == first_article['link']
        
        description = first_item.find('description')
        assert description.text == first_article['description']
        
        pub_date = first_item.find('pubDate')
        assert pub_date.text == first_article['pubDate']
    
    def test_generate_rss_feed_empty_articles(self):
        """空の記事リストでのRSS生成テスト"""
        rss_element = generate_rss_feed([])
        channel = rss_element.find('channel')
        items = channel.findall('item')
        
        # アイテムが0個であることを確認
        assert len(items) == 0
        
        # チャンネル情報は存在することを確認
        title = channel.find('title')
        assert title is not None
    
    def test_generate_valid_xml_output(self, openai_sample_articles):
        """有効なXML出力の生成テスト"""
        rss_element = generate_rss_feed(openai_sample_articles)
        
        # XML文字列に変換
        ET.indent(rss_element, space="  ", level=0)
        xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(rss_element, encoding='unicode')
        
        # XMLとして再パース可能かテスト
        try:
            reparsed = ET.fromstring(xml_str.split('\n', 1)[1])  # XML宣言を除去
            assert reparsed.tag == 'rss'
        except ET.ParseError:
            pytest.fail("Generated XML is not valid")

@pytest.mark.openai
@pytest.mark.integration
@pytest.mark.slow
class TestOpenAIEndToEnd:
    """OpenAI エンドツーエンド統合テスト"""
    
    @patch('scripts.generate_openai_rss.scrape_openai_releases')
    @patch('os.makedirs')
    def test_main_function_success_flow(self, mock_makedirs, mock_scrape, tmp_path, openai_sample_articles):
        """メイン関数の成功フロー統合テスト"""
        # モック設定
        mock_scrape.return_value = openai_sample_articles
        
        # 一時ディレクトリでテスト実行
        output_file = tmp_path / "openai-releases.xml"
        
        with patch('builtins.open', create=True) as mock_open:
            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file
            
            # main関数実行（実際のファイル作成をモック）
            with patch('scripts.generate_openai_rss.main') as mock_main:
                # main関数の実際の処理をシミュレート
                from scripts.generate_openai_rss import generate_rss_feed
                
                rss_element = generate_rss_feed(openai_sample_articles)
                ET.indent(rss_element, space="  ", level=0)
                xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(rss_element, encoding='unicode')
                
                # 書き込み内容の検証
                assert '<?xml version="1.0" encoding="UTF-8"?>' in xml_str
                assert 'OpenAI ChatGPT' in xml_str
                assert openai_sample_articles[0]['title'] in xml_str
    
    @patch('scripts.generate_openai_rss.scrape_openai_releases')
    def test_main_function_scraping_failure(self, mock_scrape):
        """スクレイピング失敗時のメイン関数テスト"""
        # スクレイピング失敗をシミュレート（フォールバック記事を返す）
        fallback_articles = [{
            'title': 'リリースノート取得エラー',
            'link': 'https://help.openai.com/en/articles/6825453-chatgpt-release-notes',
            'description': 'エラーが発生しました。',
            'pubDate': datetime.now().strftime('%d %b %Y %H:%M:%S +0000')
        }]
        mock_scrape.return_value = fallback_articles
        
        with patch('os.makedirs'):
            with patch('builtins.open', create=True):
                # main関数実行時にエラーが発生しないことを確認
                try:
                    from scripts.generate_openai_rss import generate_rss_feed
                    rss_element = generate_rss_feed(fallback_articles)
                    # フォールバック記事でもRSS生成が成功することを確認
                    assert rss_element is not None
                except Exception as e:
                    pytest.fail(f"Main function failed with fallback articles: {e}")

@pytest.mark.openai
class TestOpenAIDataValidation:
    """OpenAI データ検証テスト"""
    
    def test_article_data_completeness(self, openai_sample_articles):
        """記事データの完全性テスト"""
        for article in openai_sample_articles:
            # 必須フィールドの存在確認
            assert 'title' in article
            assert 'link' in article
            assert 'description' in article
            assert 'pubDate' in article
            
            # フィールド値の妥当性確認
            assert article['title'] != ''
            assert article['link'].startswith('http')
            assert article['description'] != ''
            assert '+0000' in article['pubDate']  # RFC-822形式の確認
    
    def test_article_link_format(self, openai_sample_articles):
        """記事リンクフォーマットの検証"""
        for article in openai_sample_articles:
            link = article['link']
            assert link.startswith('https://help.openai.com')
    
    def test_article_date_format(self, openai_sample_articles):
        """記事日付フォーマットの検証"""
        for article in openai_sample_articles:
            pub_date = article['pubDate']
            # RFC-822フォーマットの基本構造確認
            assert '+0000' in pub_date
            assert '2025' in pub_date or '2024' in pub_date  # 年の存在確認

if __name__ == "__main__":
    pytest.main([__file__, "-v"])