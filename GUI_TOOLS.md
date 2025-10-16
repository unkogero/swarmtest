# Docker Swarm GUI管理ツール

Docker SwarmをWebブラウザから視覚的に管理・監視できるツールを紹介します。

---

## 1. Portainer (推奨)

### 概要
- **最も人気のあるDocker管理GUI**
- Docker、Docker Swarm、Kubernetesに対応
- 無料版（Community Edition）で十分な機能
- 日本語対応

### 主な機能
- サービス、タスク、ノードの一覧表示
- サービスのスケーリング（GUIでレプリカ数変更）
- ログのリアルタイム表示
- コンテナのターミナルアクセス
- イメージ管理
- ネットワーク・ボリューム管理
- ユーザー・アクセス管理

### インストール

**Windows (PowerShellまたはコマンドプロンプト):**
```powershell
# Portainerコンテナ起動
docker run -d `
  -p 9000:9000 `
  -p 8000:8000 `
  --name portainer `
  --restart=always `
  -v //var/run/docker.sock:/var/run/docker.sock `
  -v portainer_data:/data `
  portainer/portainer-ce:latest
```

**Linux/Mac:**
```bash
# Portainerコンテナ起動
docker run -d \
  -p 9000:9000 \
  -p 8000:8000 \
  --name portainer \
  --restart=always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data \
  portainer/portainer-ce:latest
```

**Swarmサービスとしてデプロイ (Linux/Mac):**
```bash
docker service create \
  --name portainer \
  --publish 9000:9000 \
  --publish 8000:8000 \
  --constraint 'node.role==manager' \
  --mount type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock \
  --mount type=volume,src=portainer_data,dst=/data \
  portainer/portainer-ce:latest
```

### アクセス方法

1. ブラウザで http://localhost:9000 にアクセス
2. 初回アクセス時に管理者アカウント作成
   - ユーザー名: admin
   - パスワード: 12文字以上を設定
3. 環境選択で「Docker」を選択
4. 「Connect」をクリック

### 主な使い方

#### サービス一覧表示
1. 左メニュー「Swarm」→「Services」
2. サービス名、レプリカ数、イメージが一覧表示される

#### サービスのスケーリング
1. サービスをクリック
2. 「Scaling/Placement」タブ
3. 「Replicas」の数値を変更
4. 「Update service」をクリック

#### ログ確認
1. サービスをクリック
2. 「Logs」タブ
3. リアルタイムでログが流れる

#### ノード管理
1. 左メニュー「Swarm」→「Nodes」
2. ノードの状態、リソース使用率を確認

---

## 2. Swarmpit

### 概要
- **Swarm専用の軽量GUI**
- シンプルで使いやすい
- リソース使用率の可視化

### インストール

```bash
# Swarmpit用ネットワーク作成
docker network create --driver overlay swarmpit-net

# Swarmpitデプロイ
docker service create \
  --name swarmpit \
  --network swarmpit-net \
  --publish 888:8080 \
  --constraint 'node.role==manager' \
  --mount type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock \
  swarmpit/swarmpit:latest
```

### アクセス方法
- ブラウザで http://localhost:888 にアクセス
- 初回アクセス時にアカウント作成

### 主な機能
- サービス、タスク、ノードの視覚的管理
- CPU/メモリ使用率のグラフ表示
- サービスログの表示
- スタック管理

---

## 3. Docker Swarm Visualizer

### 概要
- **ノードとコンテナの配置を視覚化**
- シンプルな表示専用ツール
- リアルタイム更新

### インストール

```bash
docker service create \
  --name viz \
  --publish 8080:8080 \
  --constraint 'node.role==manager' \
  --mount type=bind,src=/var/run/docker.sock,dst=/var/run/docker.sock \
  dockersamples/visualizer:latest
```

### アクセス方法
- ブラウザで http://localhost:8080 にアクセス

### 表示内容
- 各ノードとその上で動作しているコンテナ
- コンテナ名、イメージ名
- リアルタイムで更新

### 用途
- デモやプレゼンテーション
- ノード間の配置確認
- スケーリングの視覚的確認

---

## 4. Grafana + Prometheus (監視特化)

### 概要
- **本格的なメトリクス監視**
- CPU、メモリ、ネットワークの詳細グラフ
- アラート設定可能

### インストール (簡易版)

```bash
# Prometheusデプロイ
docker service create \
  --name prometheus \
  --publish 9090:9090 \
  --constraint 'node.role==manager' \
  prom/prometheus:latest

# Grafanaデプロイ
docker service create \
  --name grafana \
  --publish 3000:3000 \
  grafana/grafana:latest
```

### アクセス方法
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000
  - 初期ユーザー名: admin
  - 初期パスワード: admin

---

## ツール比較

| ツール | 用途 | 難易度 | リソース | 推奨度 |
|:---|:---|:---:|:---:|:---:|
| **Portainer** | 総合管理 | 低 | 中 | ★★★★★ |
| **Swarmpit** | Swarm管理 | 低 | 低 | ★★★★☆ |
| **Visualizer** | 配置確認 | 最低 | 最低 | ★★★☆☆ |
| **Grafana/Prometheus** | 監視・分析 | 高 | 高 | ★★★★☆ |

---

## 実践例: Portainerでサービス管理

### 1. テストサービスをデプロイ

```bash
# Swarm初期化
docker swarm init

# サンプルサービス作成
docker service create \
  --name web \
  --replicas 3 \
  --publish 8080:80 \
  nginx:alpine
```

### 2. Portainerで確認

1. http://localhost:9000 にアクセス
2. 左メニュー「Swarm」→「Services」
3. `web` サービスをクリック
4. 以下の情報が確認できる：
   - レプリカ数: 3/3
   - 使用イメージ: nginx:alpine
   - ポート: 8080→80
   - 各タスクの状態とノード配置

### 3. スケーリング

1. 「Scaling/Placement」タブ
2. Replicas: `3` → `5` に変更
3. 「Update service」クリック
4. リアルタイムで2つのレプリカが追加される様子が見える

### 4. ログ確認

1. 「Logs」タブ
2. 全レプリカのログが統合表示される
3. 特定のタスクだけフィルタリング可能

---

## トラブルシューティング

### Portainerにアクセスできない

```bash
# コンテナ状態確認
docker ps | grep portainer

# ポート確認
netstat -ano | findstr :9000  # Windows
lsof -i :9000                # Linux/Mac

# 再起動
docker restart portainer
```

### Windowsでパスエラーが出る

Git Bashではなく、**PowerShellまたはコマンドプロンプト**で実行してください。

```powershell
# PowerShellの例
docker run -d `
  -p 9000:9000 `
  --name portainer `
  -v //var/run/docker.sock:/var/run/docker.sock `
  -v portainer_data:/data `
  portainer/portainer-ce:latest
```

### サービスが表示されない

Swarmモードが有効か確認：
```bash
docker node ls
```

エラーが出る場合：
```bash
docker swarm init
```

---

## クリーンアップ

### Portainer削除

```bash
# コンテナ停止・削除
docker stop portainer
docker rm portainer

# データボリューム削除（オプション）
docker volume rm portainer_data
```

### Visualizer削除

```bash
docker service rm viz
```

---

## 推奨構成

### 開発・テスト環境
- **Portainer** (総合管理)
- **Visualizer** (配置確認)

### 本番環境
- **Portainer** (管理)
- **Grafana + Prometheus** (監視)

### デモ・プレゼン
- **Visualizer** (視覚的インパクト)

---

## 参考リンク

- [Portainer公式サイト](https://www.portainer.io/)
- [Swarmpit公式サイト](https://swarmpit.io/)
- [Docker Swarm Visualizer GitHub](https://github.com/dockersamples/docker-swarm-visualizer)
- [Prometheus公式サイト](https://prometheus.io/)
- [Grafana公式サイト](https://grafana.com/)
