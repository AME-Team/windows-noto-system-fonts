# 【手順書】TTX/FontTools を用いたフォント名偽装・システムフォント置き換え

本書は、`Note.md` に記載された方針に基づき、**TTX / FontTools**（Python コマンドラインツール）を使用して「Noto Sans JP」のフォント内部名（Name テーブル）をシステムフォント（例: `Meiryo` や `Yu Gothic UI`）に偽装し、Windows のシステムフォントとして置き換えるための**手動操作手順書**です。

---

## 0. 事前知識と注意事項

> [!CAUTION]
> **システムの安定性について**
> システムフォントの変更は、Windows の UI 描画や各種アプリケーションの表示に影響を与える可能性があります。
> 万が一に備え、**「元のフォントファイルのバックアップ」** および **「ロールバック手順」** を必ず確認してから作業を行ってください。

- **静的フォント（Static TTF）を使用する理由**:
  可変フォント（Variable Font: `NotoSansJP-VariableFont_wght.ttf`）は、Windows の一部の古い API（GDI / Win32）やアプリでウェイト認識や描画に問題が生じる場合があります。そのため、本手順では **静的フォント（`NotoSansJP-Regular.ttf` 等）** を使用します。
- **フォント形式について**:
  Windows 標準のメイリオは TTC（TrueType Collection: 複数ウェイトや UI 版が1つに結合された形式）ですが、TTF（単一フォント）として偽装したものを配置または登録することでも認識させることが可能です。

---

## 1. 事前準備

### 1-1. Python と FontTools の確認・インストール

PowerShell を開き、FontTools が利用可能か確認します。未インストールの場合はインストールします。

```powershell
# fonttools のインストール（既に導入済みの場合はスキップ）
pip install fonttools

# 動作確認（ヘルプが表示されれば OK）
ttx -h
```

### 1-2. Noto Sans JP の静的フォント（TTF）の解凍

作業フォルダ（例: `c:\Users\t_ame\OneDrive\Temp\20260910`）にある `Noto_Sans_JP.zip` から静的フォントを展開します。

```powershell
# PowerShell で zip を解凍
Expand-Archive -Path .\Noto_Sans_JP.zip -DestinationPath .\Noto_Sans_JP_Extracted -Force
```

展開先にある `static` フォルダ内のファイルを確認します：

- 通常ウェイト: `NotoSansJP-Regular.ttf`
- 太字ウェイト: `NotoSansJP-Bold.ttf`

※本手順では、基本となる **Regular** を例に進めます。Bold も同様の手順で作成可能です。

---

## 2. TTX でフォントメタ情報（name テーブル）を抽出

フォントファイル内部の「フォント名」「ファミリー名」などが格納されている `name` テーブルのみを XML として書き出します。

```powershell
# static フォルダに移動
cd Noto_Sans_JP_Extracted\static

# name テーブルのみを XML (NotoSansJP-Regular.ttx) に書き出し
ttx -t name NotoSansJP-Regular.ttf
```

実行後、同じフォルダに `NotoSansJP-Regular.ttx` が生成されます。

---

## 3. XML ファイルの編集（フォント名の偽装）

生成された `NotoSansJP-Regular.ttx` をテキストエディタ（VS Code やメモ帳）で開きます。

### 3-1. 書き換える主な Name ID の役割

- **`nameID="1"`**: フォントファミリー名（例: `Meiryo`）
- **`nameID="2"`**: スタイル・サブファミリー名（例: `Regular`）
- **`nameID="4"`**: フルネーム（例: `Meiryo`）
- **`nameID="6"`**: PostScript 名（例: `Meiryo`）※半角英数字のみ
- **`langID="0x409"`**: 英語 (米国)
- **`langID="0x411"`**: 日本語

### 3-2. 具体的な書き換え例（Meiryo 偽装の場合）

`<name>` ～ `</name>` タグ内の主要な `namerecord` を以下のように編集します。
（Windows で認識されやすいよう、英語表記 `0x409` と日本語表記 `0x411` を定義します）

```xml
  <name>
    <namerecord nameID="0" platformID="3" platEncID="1" langID="0x409">
      (c) 2014-2021 Adobe (http://www.adobe.com/), with Reserved Font Name 'Source'.
    </namerecord>

    <!-- Family Name (英語・日本語) -->
    <namerecord nameID="1" platformID="3" platEncID="1" langID="0x409">
      Meiryo
    </namerecord>
    <namerecord nameID="1" platformID="3" platEncID="1" langID="0x411">
      メイリオ
    </namerecord>

    <!-- Subfamily Name -->
    <namerecord nameID="2" platformID="3" platEncID="1" langID="0x409">
      Regular
    </namerecord>
    <namerecord nameID="2" platformID="3" platEncID="1" langID="0x411">
      標準
    </namerecord>

    <!-- Unique font identifier -->
    <namerecord nameID="3" platformID="3" platEncID="1" langID="0x409">
      FakeMeiryo-NotoSansJP-Regular
    </namerecord>

    <!-- Full Font Name -->
    <namerecord nameID="4" platformID="3" platEncID="1" langID="0x409">
      Meiryo
    </namerecord>
    <namerecord nameID="4" platformID="3" platEncID="1" langID="0x411">
      メイリオ
    </namerecord>

    <!-- Version -->
    <namerecord nameID="5" platformID="3" platEncID="1" langID="0x409">
      Version 2.004-Fake
    </namerecord>

    <!-- PostScript Name (空白なし英数字) -->
    <namerecord nameID="6" platformID="3" platEncID="1" langID="0x409">
      Meiryo
    </namerecord>
    
    <!-- ※下部にあるその他のレコード（ライセンスや作者情報等）はそのままで構いません -->
  </name>
```

> [!TIP]
> **「Yu Gothic UI」や「Meiryo UI」に偽装したい場合**
>
> - **Meiryo UI**:
>   `nameID="1"` および `nameID="4"` の英語名を `Meiryo UI`、日本語名を `Meiryo UI`（または `メイリオ UI`）、`nameID="6"` を `MeiryoUI` に設定します。
> - **Yu Gothic UI**:
>   `nameID="1"` および `nameID="4"` の英語名を `Yu Gothic UI`、日本語名を `游ゴシック UI`、`nameID="6"` を `YuGothicUI-Regular` に設定します。

編集後、ファイルを保存します。

---

## 4. TTX でフォントファイルの再構築（コンパイル）

元の `NotoSansJP-Regular.ttf` に、編集した XML（`NotoSansJP-Regular.ttx`）を差し込んで新しい TTF ファイルを出力します。

```powershell
# -m で元フォントを指定、-o で出力ファイル名を指定
ttx -m NotoSansJP-Regular.ttf -o Meiryo_Fake.ttf NotoSansJP-Regular.ttx
```

出力された `Meiryo_Fake.ttf` をダブルクリックすると、Windows のフォントビューアーが開き、フォント名が **「メイリオ」** または **「Meiryo」** と認識されていることが確認できます。

---

## 5. 元のシステムフォントのバックアップ

システム変更前に、必ず元のフォントファイルを安全な場所に退避してください。

```powershell
# バックアップフォルダを作成
New-Item -ItemType Directory -Path "C:\FontBackup" -Force

# Meiryo 関連ファイルのバックアップ
Copy-Item "C:\Windows\Fonts\meiryo*.ttc" -Destination "C:\FontBackup\" -Force

# （游ゴシックも対象にする場合）
Copy-Item "C:\Windows\Fonts\YuGoth*.ttc" -Destination "C:\FontBackup\" -Force
```

---

## 6. システムへの適用（シェルスクリプトによる一発置き換え）

通常起動中の Windows ではシステムフォントが常時使用中のためロックされており、直接の上書きやリネームができません。
そのため、**Windows 回復環境（WinRE）のコマンドプロンプト** または **セーフモード** からシェルを実行します。

短いパスで迷わず実行できるよう、**`C:\Temp\`** に必要なフォントとスクリプトを一式配置しています。

### 手順

1. **Windows 回復環境（コマンドプロンプト）で起動**:
   - スタートメニューの電源ボタンを開き、`Shift` キーを押しながら「再起動」をクリックします。
   - 青い画面が表示されたら、「トラブルシューティング」→「詳細オプション」→「コマンド プロンプト」を選択します。

2. **スクリプトを1行実行**:
   黒いコマンドプロンプトが開いたら、以下の **1行だけ** を入力して Enter を押します。

   ```cmd
   C:\Temp\replace.bat
   ```

   ※自動的に所有権取得、バックアップ作成（`.bak`）、フォントの配置が行われます。

3. **PC を通常再起動**:
   「置き換えが完了しました！」と表示されたら、`exit` と入力して通常通り Windows を起動します。

---

## 7. フォントキャッシュのクリアと再起動

Windows が通常起動したら、`C:\Temp` フォルダ内の **`clear_cache.bat`** を右クリックし、**「管理者として実行」** してください。

処理完了後、PC をもう一度再起動すれば完了です。

---

## 8. 元に戻す手順（ロールバック）

万が一元のフォントに戻したい場合も、回復環境のコマンドプロンプトから以下の **1行だけ** を実行します。

```cmd
C:\Temp\restore.bat
```
