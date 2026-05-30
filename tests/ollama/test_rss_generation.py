import pytest
import os
import xml.etree.ElementTree as ET
import sys

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../'))
from scripts.generate_ollama_rss import translate_simple, parse_relative_date, fetch_ollama_models, generate_rss

@pytest.mark.ollama
@pytest.mark.unit
def test_translate_simple():
    """Test the translation logic."""
    assert "推論" in translate_simple("reasoning")
    assert "エージェントワークフロー" in translate_simple("agentic workflows")
    assert "1週間前" in translate_simple("1 week ago").replace(" ", "")
    assert "2ヶ月前" in translate_simple("2 months ago").replace(" ", "")

    # Test complex string
    original = "Gemma 4 models are designed to deliver frontier-level performance at each size."
    translated = translate_simple(original)
    assert "するように設計された" in translated
    assert "提供" in translated
    assert "フロンティアレベル" in translated
    assert "パフォーマンス" in translated

@pytest.mark.ollama
@pytest.mark.unit
def test_parse_relative_date():
    """Test relative date parsing."""
    date_str = parse_relative_date("1 week ago")
    assert "+0000" in date_str

    date_str2 = parse_relative_date("2 months ago")
    assert "+0000" in date_str2

@pytest.mark.ollama
@pytest.mark.unit
def test_generate_rss():
    """Test RSS generation from articles."""
    articles = [
        {
            "title": "test-model",
            "link": "https://ollama.com/library/test-model",
            "description": "test description (Updated: 1 week ago)",
            "pubDate": "Sat, 23 May 2026 00:00:00 +0000"
        }
    ]
    rss_element = generate_rss(articles)
    assert rss_element.tag == "rss"
    channel = rss_element.find("channel")
    assert channel.find("title").text == "Ollama Models"

    item = channel.find("item")
    assert item.find("title").text == "test-model"
    assert item.find("link").text == "https://ollama.com/library/test-model"

@pytest.mark.ollama
@pytest.mark.integration
def test_fetch_ollama_models():
    """Integration test to fetch real data (if internet is available)."""
    articles = fetch_ollama_models()
    assert isinstance(articles, list)
    if articles:
        assert "title" in articles[0]
        assert "link" in articles[0]
        assert "description" in articles[0]
        assert "pubDate" in articles[0]
        assert articles[0]["link"].startswith("https://ollama.com/library/")
