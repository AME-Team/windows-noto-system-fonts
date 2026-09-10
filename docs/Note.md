# Note

はい、**可能です**。Noto Sans JP のフォントファイル（`NOTOSANSJP-VF.TTF` など）を、Windows がシステムフォントとして認識するフォント名（`Meiryo`、`Meiryo UI`、`Yu Gothic UI` など）で**フォント名を偽装してインストール**することで、実体は Noto Sans JP ながらシステムからはメイリオなどとして扱わせることができます。 [prograshi](https://prograshi.com/pc/windows-system-font/)

## 方法：フォント名を書き換えて再インストール

### 1. 元フォントのバックアップと無効化

まず、既存の `Meiryo`、`Meiryo UI`、`Yu Gothic UI` を無効化またはリネームします。

- `C:\Windows\Fonts` を開く
- `meiryo.ttc`、`meiryo.ttl`、`YuGothic-Regular.ttc` などを別フォルダにバックアップ
- 元のフォントファイルをリネーム（例：`meiryo.ttc.bak`）

> 注意：システムフォントは使用中のため、セーフモードまたは別の OS から操作するか、後述するレジストリ置換と組み合わせて使います。

### 2. Noto Sans JP のフォント名を書き換える

フォントファイル内部の**フォントファミリー名**を `Meiryo` などに書き換えるには、フォント編集ツールを使います。

#### 推奨ツール

- **FontForge**（無料・OSS）
- **High-Logic FontCreator**（有料・体験版あり）
- **TTX/FontTools**（Python、コマンドライン）

#### FontForge での手順（例：Noto Sans JP → Meiryo 偽装）

1. FontForge を起動し、`NOTOSANSJP-VF.TTF` を開く
2. `Element` → `Font Info` を選択
3. `PS Names` タブで以下を変更：
   - `Family Name`: `Meiryo`
   - `Name for Humans`: `Meiryo`
   - `Fontname`: `Meiryo-NotoFake`
4. `TTF Names` タブでも同様に `Meiryo` に設定
5. `File` → `Generate Fonts` で新しい `.ttf` または `.ttc` を出力

> 注意：可変フォント（VF）をそのまま使う場合、一部ツールで扱いが難しいことがあります。その場合は静的フォント版の Noto Sans JP（Regular, Medium など）を使うことを推奨します。 [tech.guitarrapc](https://tech.guitarrapc.com/?page=1767016800)

### 3. 偽装フォントをインストール

生成したフォントファイルを `C:\Windows\Fonts` にコピーし、インストールします。

- エクスプローラーで右クリック → 「インストール」
- または管理者権限で `copy` コマンド使用

### 4. フォントキャッシュをリセット

```powershell
Stop-Service FontCache -Force
Start-Service FontCache
```

または `C:\Windows\ServiceProfiles\LocalService\AppData\Local\FontCache` を削除後、再起動。

## 注意点

- **システム安定性**: フォント名を偽装すると、一部アプリでレンダリング崩れや互換性問題が起きる可能性があります。
- **Windows Update で復元される**: 更新プログラム適用時にシステムフォントが復元される可能性があります。その場合は再度設定し直す必要があります。
- **ライセンス**: Noto Sans JP は SIL Open Font License で配布されており、改変・再配布は許可されていますが、フォント名変更は自己責任で行ってください。 [prograshi](https://prograshi.com/pc/windows-system-font/)

## 現実的な代替案

フォント名偽装は技術的に可能ですが、**レジストリの FontSubstitutes で置換設定する方が安全で保守性が高い**です。

- フォントファイル自体は純正のまま
- 設定変更だけで元に戻せる
- Windows Update 影響を受けにくい

「逆の発想」は面白いですが、実用面ではレジストリ置換＋Noto Sans JP 優先設定が現実的です。
