# ピッチスカウト - デプロイメントガイド

> AI声域分析＆楽曲推薦アプリケーションの本番環境構築手順

## 📋 目次

- [1. システム要件定義](#1-システム要件定義)
- [2. 必須スペック](#2-必須スペック)
- [3. 事前準備](#3-事前準備)
- [4. デプロイ手順](#4-デプロイ手順)
- [5. 運用・監視](#5-運用監視)
- [6. トラブルシューティング](#6-トラブルシューティング)

---

## 1. システム要件定義

### 1.1 プロダクト概要

**プロダクト名**: ピッチスカウト

**コンセプト**: AIを活用した声域分析と楽曲マッチングサービス

**主な機能**:
- 🎤 マイク録音による声域分析
- 🎵 カラオケ音源からのボーカル分離・分析
- 📁 音声ファイルアップロード対応
- 🔍 地声/裏声の自動分類（6指標スコアリング）
- 🎶 3,900曲・260アーティストの音域データベース検索
- 👤 ユーザー認証・プロファイル管理
- 📊 分析履歴の保存・追跡
- ⭐ お気に入り楽曲管理

### 1.2 システムアーキテクチャ

```
┌─────────────────┐
│   ユーザー      │
└────────┬────────┘
         │
    [Internet]
         │
┌────────▼────────┐
│  フロントエンド  │ React 19 + TypeScript
│  (静的ホスティング) │ Tailwind CSS
└────────┬────────┘
         │ REST API
┌────────▼────────┐
│  バックエンド    │ FastAPI (Python)
│  (アプリサーバー) │ Uvicorn
└────┬────┬───────┘
     │    │
     │    └──────────┐
     │               │
┌────▼─────┐  ┌─────▼──────┐
│ SQLite   │  │ Supabase   │
│ (楽曲DB) │  │ (認証/ユーザーDB) │
└──────────┘  └────────────┘

[AI/ML処理]
├─ CREPE (ピッチ検出)
├─ Demucs (ボーカル分離)
├─ librosa (スペクトル分析)
└─ scikit-learn (声質分類)
```

### 1.3 技術スタック

| レイヤー | 技術 | バージョン |
|----------|------|-----------|
| **フロントエンド** | React | 19.2.4 |
| | TypeScript | 4.9.5 |
| | Tailwind CSS | 3.4.17 |
| | Axios | 1.13.5 |
| **バックエンド** | Python | 3.10+ |
| | FastAPI | 0.115.0 |
| | Uvicorn | 0.30.0 |
| **音声処理** | CREPE (PyTorch) | - |
| | Demucs | latest |
| | librosa | 0.10.2 |
| | noisereduce | latest |
| **AI/ML** | PyTorch | 2.5.1 |
| | torchvision | 2.5.1 |
| | scikit-learn | 1.4.0+ |
| **データベース** | SQLite | 3.x |
| | Supabase (PostgreSQL) | 2.28.0 |
| **認証** | Supabase Auth | 2.28.0 |

---

## 2. 必須スペック

### 2.1 ハードウェア要件

#### 最小スペック（開発/小規模）
- **CPU**: 4コア以上 (Intel Core i5 / AMD Ryzen 5 相当)
- **メモリ**: 8GB RAM
- **ストレージ**: 20GB 空き容量
- **GPU**: 不要（CPU処理可能、ただし処理時間増）

#### 推奨スペック（本番環境）
- **CPU**: 8コア以上 (Intel Xeon / AMD EPYC)
- **メモリ**: 16GB RAM以上
- **ストレージ**: 50GB SSD（音声ファイル一時保存用）
- **GPU**: NVIDIA GPU（CUDA対応）推奨
  - VRAM 4GB以上
  - Demucsの処理が3-5倍高速化
  - 同時リクエスト処理時に有効
- **ネットワーク**: 100Mbps以上の安定した接続

#### クラウド推奨インスタンス例

**AWS EC2**:
- 最小: `t3.medium` (2 vCPU, 4GB RAM) + EBS 20GB
- 推奨: `c5.2xlarge` (8 vCPU, 16GB RAM) + EBS 50GB
- GPU推奨: `g4dn.xlarge` (4 vCPU, 16GB RAM, NVIDIA T4)

**Google Cloud Compute Engine**:
- 最小: `e2-standard-2` (2 vCPU, 8GB RAM)
- 推奨: `n2-standard-4` (4 vCPU, 16GB RAM)
- GPU推奨: `n1-standard-4` + NVIDIA Tesla T4

**Azure Virtual Machines**:
- 最小: `Standard_B2s` (2 vCPU, 4GB RAM)
- 推奨: `Standard_D4s_v3` (4 vCPU, 16GB RAM)
- GPU推奨: `Standard_NC4as_T4_v3` (4 vCPU, 28GB RAM, NVIDIA T4)

### 2.2 ソフトウェア要件

#### OS
- **Linux**: Ubuntu 20.04 LTS / 22.04 LTS（推奨）
- **macOS**: 12.0 (Monterey) 以降
- **Windows**: Windows 10/11 + WSL2

#### ランタイム
- **Python**: 3.10, 3.11, 3.12（3.10以上必須）
- **Node.js**: 16.x, 18.x, 20.x（フロントエンドビルド用）
- **npm**: 8.x以上

#### システムパッケージ（Linux）
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y \
    python3-dev \
    python3-pip \
    ffmpeg \
    libsndfile1 \
    build-essential
```

### 2.3 外部サービス

#### Supabase（必須）
- **プラン**: Free / Pro / Team
- **用途**: ユーザー認証、プロファイル、分析履歴、お気に入り
- **データベース**: PostgreSQL (Supabaseが提供)
- **必要な情報**:
  - Project URL
  - Anon Key
  - Service Role Key（管理用、オプション）

**料金目安**:
- Free tier: 500MB DB, 2GB bandwidth/month（開発用）
- Pro tier: $25/month〜（本番推奨）

### 2.4 処理時間の目安

| 機能 | 処理時間（CPU） | 処理時間（GPU） |
|------|----------------|----------------|
| マイク録音分析 | 10-30秒 | 10-20秒 |
| カラオケ音源分析（軽量） | 1-3分 | 30秒-1分 |
| カラオケ音源分析（高品質） | 3-5分 | 1-2分 |

### 2.5 ネットワーク・帯域幅

- **想定ファイルサイズ**: 
  - 録音音声: 1-5MB (WebM/WAV)
  - カラオケ音源: 3-10MB
- **同時接続**: 
  - 開発: 1-10ユーザー
  - 本番: 50-100ユーザー（負荷分散推奨）

---

## 3. 事前準備

### 3.1 Supabaseプロジェクトの作成

1. [Supabase](https://supabase.com)にアクセス
2. 「New Project」をクリック
3. プロジェクト名・リージョン・パスワードを設定
4. プロジェクト作成完了を待つ（2-3分）

5. **APIキーを取得**:
   - Settings > API から以下をコピー:
     - `Project URL`: `https://xxxxx.supabase.co`
     - `anon public key`: `eyJhbGc...`

6. **データベースセットアップ**:
   - SQL Editor を開く
   - `backend/supabase_migration.sql` の内容を全てコピー＆ペースト
   - 「Run」を実行
   - 成功確認: `user_profiles`, `analysis_history`, `favorite_songs`, `artists`, `songs` テーブルが作成されたことを確認

### 3.2 楽曲データベースの準備

リポジトリには約3,900曲の音域データを含む `songs.db` が既に含まれています。

**データを更新したい場合**:
```bash
cd backend
rm -f songs.db
python scraper.py  # 約8分、voice-key.newsからスクレイピング
```

### 3.3 ドメイン・SSL証明書（本番環境）

- **ドメイン取得**: お名前.com、Route 53、Cloudflare など
- **SSL証明書**: Let's Encrypt（無料）、AWS Certificate Manager など
- **リバースプロキシ**: Nginx, Caddy 推奨

---

## 4. デプロイ手順

### 4.1 サーバーへの初期セットアップ

#### 4.1.1 リポジトリのクローン

```bash
# サーバーにSSH接続
ssh user@your-server-ip

# 作業ディレクトリ作成
sudo mkdir -p /opt/pitchscout
sudo chown $USER:$USER /opt/pitchscout
cd /opt/pitchscout

# リポジトリクローン
git clone https://github.com/your-org/2026_team11.git
cd 2026_team11
```

#### 4.1.2 システムパッケージのインストール

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y \
    python3.11 python3.11-venv python3.11-dev \
    python3-pip \
    ffmpeg \
    libsndfile1 \
    build-essential \
    nginx \
    supervisor
```

### 4.2 バックエンドのデプロイ

#### 4.2.1 Python環境のセットアップ

```bash
cd backend

# 仮想環境の作成
python3.11 -m venv venv
source venv/bin/activate

# 依存関係のインストール
pip install --upgrade pip
pip install -r requirements.txt

# PyTorch with CUDA (GPU使用時)
# GPUがある場合は以下を実行（CUDA 12.4対応版）
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
```

#### 4.2.2 環境変数の設定

```bash
cd /opt/pitchscout/2026_team11/backend
cp .env.example .env
nano .env  # または vim .env
```

`.env` ファイルを編集:

```env
# Supabase設定（必須）
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# JWT設定（必須・本番環境では強力なランダム文字列に変更）
JWT_SECRET=your-super-secure-random-jwt-secret-change-this-in-production

# オプション設定
# ENVIRONMENT=production
# LOG_LEVEL=info
```

**重要**: `JWT_SECRET` は本番環境では必ず変更してください:
```bash
# ランダムな秘密鍵を生成
python3 -c "import secrets; print(secrets.token_urlsafe(64))"
```

#### 4.2.3 動作確認

```bash
cd /opt/pitchscout/2026_team11/backend
source venv/bin/activate

# テスト起動
uvicorn main:app --host 0.0.0.0 --port 8000

# 別ターミナルで確認
curl http://localhost:8000/health
# 期待: {"status":"ok"}
```

#### 4.2.4 Supervisor によるプロセス管理

```bash
sudo nano /etc/supervisor/conf.d/pitchscout-backend.conf
```

設定内容:

```ini
[program:pitchscout-backend]
command=/opt/pitchscout/2026_team11/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
directory=/opt/pitchscout/2026_team11/backend
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/pitchscout-backend.log
stdout_logfile_maxbytes=50MB
stdout_logfile_backups=10
environment=PATH="/opt/pitchscout/2026_team11/backend/venv/bin"
```

起動:

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start pitchscout-backend
sudo supervisorctl status
```

### 4.3 フロントエンドのデプロイ

#### 4.3.1 環境変数の設定

```bash
cd /opt/pitchscout/2026_team11/frontend
cp .env.example .env.production
nano .env.production
```

```env
REACT_APP_SUPABASE_URL=https://your-project.supabase.co
REACT_APP_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
REACT_APP_API_URL=https://api.your-domain.com
```

#### 4.3.2 APIエンドポイントの設定

`src/api.ts` を編集して本番APIエンドポイントを設定:

```typescript
const API = axios.create({
  baseURL: process.env.REACT_APP_API_URL || "https://api.your-domain.com",
  timeout: TIMEOUT_MS,
});
```

#### 4.3.3 ビルド

```bash
cd /opt/pitchscout/2026_team11/frontend

# Node.js依存関係のインストール
npm install

# プロダクションビルド
npm run build

# ビルド成果物は build/ ディレクトリに生成される
ls -la build/
```

#### 4.3.4 静的ファイルの配信（Nginx）

```bash
sudo nano /etc/nginx/sites-available/pitchscout
```

Nginx設定:

```nginx
# フロントエンド（静的ファイル）
server {
    listen 80;
    server_name your-domain.com www.your-domain.com;

    root /opt/pitchscout/2026_team11/frontend/build;
    index index.html;

    # React Router対応
    location / {
        try_files $uri $uri/ /index.html;
    }

    # 静的ファイルのキャッシュ
    location /static/ {
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
}

# バックエンドAPI
server {
    listen 80;
    server_name api.your-domain.com;

    client_max_body_size 50M;  # ファイルアップロード上限

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # タイムアウト設定（音声処理に時間がかかるため）
        proxy_connect_timeout 300s;
        proxy_send_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

有効化と再起動:

```bash
sudo ln -s /etc/nginx/sites-available/pitchscout /etc/nginx/sites-enabled/
sudo nginx -t  # 設定チェック
sudo systemctl restart nginx
```

#### 4.3.5 SSL証明書の設定（Let's Encrypt）

```bash
# Certbotのインストール
sudo apt-get install -y certbot python3-certbot-nginx

# SSL証明書の取得（自動でNginx設定も更新）
sudo certbot --nginx -d your-domain.com -d www.your-domain.com
sudo certbot --nginx -d api.your-domain.com

# 自動更新の確認
sudo certbot renew --dry-run
```

### 4.4 デプロイ後の確認

```bash
# バックエンドの確認
curl https://api.your-domain.com/health
# 期待: {"status":"ok"}

# フロントエンドの確認
curl -I https://your-domain.com
# 期待: HTTP/2 200

# 楽曲検索APIのテスト
curl "https://api.your-domain.com/songs?limit=5"
```

ブラウザで `https://your-domain.com` にアクセスして動作確認。

---

## 5. 運用・監視

### 5.1 ログ管理

```bash
# バックエンドログの確認
sudo tail -f /var/log/pitchscout-backend.log

# Nginxログ
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Supervisorログ
sudo supervisorctl tail -f pitchscout-backend
```

### 5.2 バックアップ

#### SQLiteデータベース（songs.db）

```bash
# 毎日バックアップ（cronで自動化）
cp /opt/pitchscout/2026_team11/backend/songs.db \
   /opt/backups/songs_$(date +%Y%m%d).db

# 古いバックアップの削除（30日以上前）
find /opt/backups -name "songs_*.db" -mtime +30 -delete
```

#### Supabaseデータ

Supabaseダッシュボードから定期的にバックアップ:
- Database > Backups で手動バックアップ
- Proプラン以上で自動バックアップ機能あり

### 5.3 アップデート手順

```bash
cd /opt/pitchscout/2026_team11

# 1. 最新コードの取得
git pull origin main  # または develop

# 2. バックエンドの更新
cd backend
source venv/bin/activate
pip install -r requirements.txt
sudo supervisorctl restart pitchscout-backend

# 3. フロントエンドの更新
cd ../frontend
npm install
npm run build
sudo systemctl restart nginx

# 4. 動作確認
curl https://api.your-domain.com/health
```

### 5.4 監視項目

- **CPU使用率**: Demucs処理時に急増（正常）
- **メモリ使用率**: 8GB以上推奨
- **ディスク使用量**: `uploads/`, `separated/` ディレクトリの定期クリーンアップ
- **APIレスポンスタイム**: `/analyze` 10-30秒、`/analyze-karaoke` 1-3分
- **エラーログ**: 500エラーの監視

### 5.5 一時ファイルのクリーンアップ

音声処理で生成される一時ファイルを定期削除:

```bash
# cronで毎日実行
crontab -e
```

追加:
```cron
# 毎日深夜2時に24時間以上前のファイルを削除
0 2 * * * find /opt/pitchscout/2026_team11/backend/uploads -type f -mtime +1 -delete
0 2 * * * find /opt/pitchscout/2026_team11/backend/separated -type f -mtime +1 -delete
```

---

## 6. トラブルシューティング

### 6.1 よくある問題

#### エラー: "SUPABASE_URLとSUPABASE_KEYを.envファイルに設定してください"

**原因**: 環境変数が読み込まれていない

**対処**:
```bash
cd /opt/pitchscout/2026_team11/backend
cat .env  # 設定を確認
sudo supervisorctl restart pitchscout-backend
```

#### エラー: "ModuleNotFoundError: No module named 'xxx'"

**原因**: Python依存関係が不足

**対処**:
```bash
cd /opt/pitchscout/2026_team11/backend
source venv/bin/activate
pip install -r requirements.txt
sudo supervisorctl restart pitchscout-backend
```

#### エラー: "CUDA out of memory"

**原因**: GPU VRAMが不足

**対処**:
1. Demucsの軽量モード使用（デフォルトで有効）
2. ワーカー数を減らす（Supervisorの `--workers` を1に）
3. より大きいGPUインスタンスに移行

#### 分析処理が遅い

**対処**:
- GPU環境の使用
- Demucs軽量モード（`htdemucs_6s`）がデフォルトで有効か確認
- CPU/メモリ使用率の監視
- インスタンスタイプのアップグレード

#### 502 Bad Gateway (Nginx)

**原因**: バックエンドが起動していない

**対処**:
```bash
sudo supervisorctl status pitchscout-backend
sudo supervisorctl start pitchscout-backend
sudo tail -f /var/log/pitchscout-backend.log
```

### 6.2 パフォーマンスチューニング

#### バックエンド
- **ワーカー数**: CPU コア数に応じて調整（2-4推奨）
- **GPU使用**: CUDA環境でDemucsが最大5倍高速化
- **ファイルキャッシュ**: Redis導入で分析結果をキャッシュ（将来実装）

#### フロントエンド
- **CDN**: CloudFlare, AWS CloudFrontで静的ファイル配信
- **画像最適化**: WebP形式の使用
- **コード分割**: React.lazy()で遅延ロード

### 6.3 セキュリティ対策

- [x] Supabase Row Level Security (RLS)有効化
- [ ] レート制限（nginx limit_req）
- [ ] CORS設定の最適化（本番ドメインのみ許可）
- [ ] APIキーのローテーション（定期的に更新）
- [ ] ファイルアップロードの検証強化
- [ ] HTTPS強制（HTTP→HTTPSリダイレクト）

---

## 7. コスト見積もり

### 開発環境（小規模）

| 項目 | サービス | 月額 |
|------|---------|------|
| サーバー | AWS t3.medium | $30 |
| ストレージ | EBS 20GB | $2 |
| Supabase | Free tier | $0 |
| ドメイン | お名前.com | $1 |
| SSL | Let's Encrypt | $0 |
| **合計** | | **$33/月** |

### 本番環境（中規模・100ユーザー/日）

| 項目 | サービス | 月額 |
|------|---------|------|
| サーバー | AWS c5.2xlarge | $250 |
| GPU（オプション） | g4dn.xlarge | $400 |
| ストレージ | EBS 100GB | $10 |
| 転送量 | 100GB/月 | $9 |
| Supabase | Pro | $25 |
| CDN | CloudFlare Pro | $20 |
| ドメイン・SSL | Route 53 | $1 |
| **合計（CPU）** | | **$315/月** |
| **合計（GPU）** | | **$715/月** |

### コスト削減Tips

1. **開発/本番環境の分離**: 開発は小規模インスタンス
2. **オートスケーリング**: 夜間・休日はインスタンス縮小
3. **スポットインスタンス**: AWSスポットで最大70%削減
4. **リザーブドインスタンス**: 1年契約で30-40%削減
5. **Supabase Free tier**: 月500MBまで無料

---

## 8. チェックリスト

### デプロイ前
- [ ] Supabaseプロジェクト作成完了
- [ ] Supabase DBマイグレーション実行完了
- [ ] `.env`ファイル設定（バックエンド）
- [ ] `.env.production`設定（フロントエンド）
- [ ] `JWT_SECRET`を強力なランダム文字列に変更
- [ ] ドメイン取得・DNS設定完了
- [ ] SSL証明書取得完了

### デプロイ後
- [ ] バックエンドヘルスチェックOK
- [ ] フロントエンドアクセスOK
- [ ] ユーザー登録・ログイン動作確認
- [ ] マイク録音→分析の動作確認
- [ ] カラオケ音源分析の動作確認
- [ ] 楽曲検索の動作確認
- [ ] Supervisor自動起動確認
- [ ] ログ出力確認
- [ ] バックアップ設定完了

### 運用開始後
- [ ] 監視ツール導入（オプション）
- [ ] アラート設定（ディスク・メモリ）
- [ ] 定期バックアップ自動化
- [ ] 一時ファイルクリーンアップ自動化

---

## 9. サポート・お問い合わせ

- **GitHub Issues**: https://github.com/your-org/2026_team11/issues
- **ドキュメント**: [README.md](README.md)
- **セットアップガイド**: [backend/SETUP_GUIDE.md](backend/SETUP_GUIDE.md)

---

**最終更新**: 2026年2月19日
