# PythonPhotoEditor

画像編集ツール

## 概要

PythonPhotoEditorは、Pythonで開発されたシンプルな画像編集ツールです。基本的な画像処理機能を提供します。

## 主な機能

- 画像の読み込みと保存（JPEG, PNG, HEIC形式対応）
- ドラッグ&ドロップによる画像の読み込み
- 指定領域の塗りつぶし（多角形選択）
- 彩度（鮮やかさ）の調整
- ウィンドウサイズに合わせた画像表示（レスポンシブ対応）
- 編集履歴（元に戻す/やり直す）機能
- ショートカットキー対応（Ctrl+Z, Ctrl+Shift+Z, Ctrl+S）

## インストール方法

1. リポジトリをクローン:

    ```bash
    git clone https://github.com/TaroNakasendo/PythonPhotoEditor.git
    cd PythonPhotoEditor
    ```

2. 依存パッケージをインストール:

    ```bash
    uv init
    uv add -r requirements.txt
    ```

## 必要なライブラリ

- tkinter
- tkinterdnd2
- Pillow
- pillow_heif

## 使い方

```bash
uv run hello.py
```

### 基本操作

- **画像を開く**: ファイルメニューから「開く」を選択、または画像ファイルをウィンドウにドラッグ&ドロップ
- **領域の選択**: 左クリックで頂点を指定して多角形を作成
- **塗りつぶし**: 右クリックで選択した領域を塗りつぶし
- **色の選択**: 「色を選択」ボタンをクリックしてカラーピッカーから色を指定
- **彩度調整**: 右上のスライダーで画像の鮮やかさを調整
- **元に戻す**: Ctrl+Z または編集メニューから「元に戻す」
- **やり直す**: Ctrl+Shift+Z または編集メニューから「やり直す」
- **保存**: Ctrl+S またはファイルメニューから「保存」

## 開発環境

- Python 3.8+
- Pillow 9.0+
- tkinterdnd2 0.3.0+
- pillow_heif 0.4.0+
- Claude Desktop
- Windows/Linux/macOS

## ライセンス

MIT License

## 貢献方法

1. リポジトリをフォーク
2. 新しいブランチを作成 (`git checkout -b feature/your-feature`)
3. 変更をコミット (`git commit -am 'Add some feature'`)
4. ブランチをプッシュ (`git push origin feature/your-feature`)
5. プルリクエストを作成

## 作者

[Taro Nakasendo] - [imac@big.jp]

## Copyright

Copyright 2025 Taro Nakasendo
