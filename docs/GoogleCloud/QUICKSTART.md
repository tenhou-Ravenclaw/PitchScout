# ピッチスカウト - クイックスタートガイド

> 最速でデプロイするための簡易手順書

**所要時間**: 30-60分

---

## 📌 このガイドについて

このドキュメントは、ピッチスカウトを**最短時間でデプロイ**するための簡易手順です。詳細な説明や本番環境向けの設定は [DEPLOYMENT.md](DEPLOYMENT.md) を参照してください。

---

## 🚀 クイックスタート（ローカル開発環境）

### 前提条件

- Python 3.10以上
- Node.js 16以上
- ffmpeg

### 1. リポジトリのクローン

```bash
git clone https://github.com/your-org/2026_team11.git
cd 2026_team11
```

### 2. Supabaseプロジェクトの準備

1. [Supabase](https://supabase.com)でプロジェクト作成
2. SQL Editorで `backend/supabase_migration.sql` を実行
3. Project URLとAnon Keyをコピー

### 3. バックエンドのセットアップ

```bash
cd backend

# 仮想環境の作成
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存関係のインストール
pip install -r requirements.txt

# 環境変数の設定
cp .env.example .env
nano .env  # SupabaseのURLとKeyを設定

# サーバー起動
uvicorn main:app --reload --port 8000
```

別ターミナルで確認:
```bash
curl http://localhost:8000/health
# 期待: {"status":"ok"}
```

### 4. フロントエンドのセットアップ

```bash
cd frontend

# 依存関係のインストール
npm install

# 環境変数の設定
cp .env.example .env
nano .env  # SupabaseのURLとKeyを設定

# 開発サーバー起動
npm start
```

ブラウザで http://localhost:3000 にアクセス

### 5. 動作確認

1. ユーザー登録
2. マイク録音で声域分析
3. 楽曲検索

---

## ☁️ 本番環境デプロイ（AWS EC2 例）

### 前提条件

- AWS EC2インスタンス（Ubuntu 22.04）
- ドメイン取得済み
- SSH接続可能

### 1. サーバーセットアップ

```bash
# EC2にSSH接続
ssh -i your-key.pem ubuntu@your-server-ip

# システムパッケージのインストール
sudo apt-get update
sudo apt-get install -y python3.11 python3.11-venv python3-pip ffmpeg \
    libsndfile1 build-essential nginx supervisor git

# 作業ディレクトリ作成
sudo mkdir -p /opt/pitchscout
sudo chown ubuntu:ubuntu /opt/pitchscout
cd /opt/pitchscout

# リポジトリクローン
git clone https://github.com/your-org/2026_team11.git
cd 2026_team11
```

### 2. バックエンドデプロイ

```bash
cd /opt/pitchscout/2026_team11/backend

# Python環境
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 環境変数設定
cp .env.example .env
nano .env  # Supabase情報を設定

# Supervisor設定
sudo nano /etc/supervisor/conf.d/pitchscout-backend.conf
```

`/etc/supervisor/conf.d/pitchscout-backend.conf`:
```ini
[program:pitchscout-backend]
command=/opt/pitchscout/2026_team11/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 2
directory=/opt/pitchscout/2026_team11/backend
user=ubuntu
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/pitchscout-backend.log
environment=PATH="/opt/pitchscout/2026_team11/backend/venv/bin"
```

起動:
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start pitchscout-backend
sudo supervisorctl status
```

### 3. フロントエンドビルド

```bash
cd /opt/pitchscout/2026_team11/frontend

# 環境変数設定（本番用）
cp .env.example .env.production
nano .env.production  # API_URL等を本番ドメインに

# api.tsを本番用に編集
nano src/api.ts
# baseURL を "https://api.your-domain.com" に変更

# ビルド
npm install
npm run build
```

### 4. Nginx設定

```bash
sudo nano /etc/nginx/sites-available/pitchscout
```

`/etc/nginx/sites-available/pitchscout`:
```nginx
# フロントエンド
server {
    listen 80;
    server_name your-domain.com;

    root /opt/pitchscout/2026_team11/frontend/build;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}

# バックエンドAPI
server {
    listen 80;
    server_name api.your-domain.com;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_connect_timeout 300s;
        proxy_read_timeout 300s;
    }
}
```

有効化:
```bash
sudo ln -s /etc/nginx/sites-available/pitchscout /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 5. SSL証明書（Let's Encrypt）

```bash
sudo apt-get install -y certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com -d api.your-domain.com
sudo certbot renew --dry-run
```

### 6. 動作確認

```bash
curl https://api.your-domain.com/health
```

ブラウザで `https://your-domain.com` にアクセス

---

## 🔧 トラブルシューティング

### バックエンドが起動しない

```bash
# ログ確認
sudo tail -f /var/log/pitchscout-backend.log

# プロセス確認
sudo supervisorctl status

# 再起動
sudo supervisorctl restart pitchscout-backend
```

### Nginxエラー

```bash
# 設定チェック
sudo nginx -t

# ログ確認
sudo tail -f /var/log/nginx/error.log

# 再起動
sudo systemctl restart nginx
```

### 環境変数が読み込まれない

```bash
# .envファイルの確認
cat /opt/pitchscout/2026_team11/backend/.env

# Supervisor再起動
sudo supervisorctl restart pitchscout-backend
```

---

## 📚 次のステップ

- ✅ 基本動作確認完了
- [ ] [DEPLOYMENT.md](DEPLOYMENT.md) で詳細な設定を確認
- [ ] バックアップ設定
- [ ] 監視・アラート設定
- [ ] パフォーマンスチューニング

---

## 💡 便利なコマンド

### サービス管理

```bash
# バックエンド
sudo supervisorctl status pitchscout-backend
sudo supervisorctl restart pitchscout-backend
sudo supervisorctl stop pitchscout-backend

# Nginx
sudo systemctl status nginx
sudo systemctl restart nginx
sudo systemctl reload nginx

# ログ確認
sudo tail -f /var/log/pitchscout-backend.log
sudo tail -f /var/log/nginx/access.log
```

### 一時ファイルの削除

```bash
# 24時間以上前の一時ファイルを削除
find /opt/pitchscout/2026_team11/backend/uploads -type f -mtime +1 -delete
find /opt/pitchscout/2026_team11/backend/separated -type f -mtime +1 -delete
```

### アップデート

```bash
cd /opt/pitchscout/2026_team11
git pull origin main

# バックエンド
cd backend
source venv/bin/activate
pip install -r requirements.txt
sudo supervisorctl restart pitchscout-backend

# フロントエンド
cd ../frontend
npm install
npm run build
sudo systemctl reload nginx
```

---

## 📞 サポート

- **GitHub Issues**: https://github.com/your-org/2026_team11/issues
- **詳細ドキュメント**: 
  - [DEPLOYMENT.md](DEPLOYMENT.md) - 詳細なデプロイ手順
  - [REQUIREMENTS.md](REQUIREMENTS.md) - 要件定義書
  - [backend/README.md](backend/README.md) - バックエンドAPI仕様
  - [backend/SETUP_GUIDE.md](backend/SETUP_GUIDE.md) - Supabaseセットアップ

---

**最終更新**: 2026年2月19日
