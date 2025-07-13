# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

RSS フィードを提供していないウェブサイト向けの非公式 RSS フィード生成プロジェクト。現在は Anthropic ニュース用の RSS フィードを生成している。

## 開発コマンド

### 依存関係のインストール
```bash
pip install -r requirements.txt
```

### RSS フィード生成（ローカル実行）
```bash
python scripts/generate_anthropic_rss.py
```
生成されたファイル: `dist/anthropic-news.xml`

## アーキテクチャ

### GitHub Actions ワークフロー
- `.github/workflows/rss-anthropic-news.yml`: RSS フィード生成とGitHub Pagesへのデプロイを自動化
- 手動実行（workflow_dispatch）または定期実行（cron）で実行可能
- 生成されたRSSファイルは`dist/`ディレクトリに保存され、GitHub Pagesで公開される

### RSS生成スクリプト
- `scripts/generate_anthropic_rss.py`: メインの RSS 生成ロジック
- BeautifulSoup を使用して https://www.anthropic.com/news をスクレイピング
- 記事情報を収集し、RSS 2.0 形式の XML ファイルを生成
- 簡易的な日本語翻訳機能を内蔵（キーワード置換）

### 出力
- `dist/anthropic-news.xml`: 生成された RSS フィード
- GitHub Pages で公開され、RSS リーダーで購読可能

## 技術スタック
- Python 3.11
- requests: HTTP リクエスト処理
- BeautifulSoup4: HTML パージング
- xml.etree.ElementTree: RSS XML 生成

## コミュニケーションガイドライン
- コミュニケーションは常に日本語で