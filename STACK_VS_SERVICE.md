# Docker Stack と Docker Service の関係

## 概念の整理

Docker Swarmでは**階層構造**でリソースが管理されます。

```
Stack（スタック）
  ├── Service（サービス）
  │     ├── Task（タスク）
  │     │     └── Container（コンテナ）
  │     ├── Task
  │     │     └── Container
  │     └── Task
  │           └── Container
  ├── Service
  │     └── ...
  └── Network, Volume, Secret, Config
```

---

## Docker Stack とは

### 定義
**複数のサービスをグループ化して管理する単位**

### 特徴
- 複数のServiceをまとめて扱う「アプリケーション単位」
- Network, Volume, Secret, Configも含む
- docker-compose.ymlで定義

### イメージ
```
Stack = アプリケーション全体
  ├── Webサービス（nginx）
  ├── APIサービス（backend）
  ├── DBサービス（postgres）
  ├── Cacheサービス（redis）
  └── 共通ネットワーク・Secret
```

---

## Docker Service とは

### 定義
**Swarmで動作する1つのアプリケーションコンポーネント**

### 特徴
- 複数のTaskから構成される
- レプリカ数、イメージ、更新設定などを定義
- Stackの一部として、または単独で存在可能

### イメージ
```
Service = 1つのマイクロサービス
  ├── Task 1（レプリカ1）→ Container
  ├── Task 2（レプリカ2）→ Container
  ├── Task 3（レプリカ3）→ Container
  └── Task 4（レプリカ4）→ Container
```

---

## 関係図

### 全体像
```
┌─────────────────────────────────────────────────────┐
│ Stack: myapp                                        │
├─────────────────────────────────────────────────────┤
│                                                     │
│  ┌─────────────────────────────────────┐           │
│  │ Service: myapp_web                  │           │
│  ├─────────────────────────────────────┤           │
│  │ ┌─────────┐ ┌─────────┐ ┌─────────┐│           │
│  │ │ Task 1  │ │ Task 2  │ │ Task 3  ││           │
│  │ │Container│ │Container│ │Container││           │
│  │ └─────────┘ └─────────┘ └─────────┘│           │
│  └─────────────────────────────────────┘           │
│                                                     │
│  ┌─────────────────────────────────────┐           │
│  │ Service: myapp_api                  │           │
│  ├─────────────────────────────────────┤           │
│  │ ┌─────────┐ ┌─────────┐            │           │
│  │ │ Task 1  │ │ Task 2  │            │           │
│  │ │Container│ │Container│            │           │
│  │ └─────────┘ └─────────┘            │           │
│  └─────────────────────────────────────┘           │
│                                                     │
│  Network: myapp_frontend, myapp_backend            │
│  Secret: myapp_db_password                         │
└─────────────────────────────────────────────────────┘
```

---

## 作成方法の比較

### Stack経由でService作成（推奨）

#### docker-compose.yml
```yaml
version: '3.8'

services:
  web:
    image: nginx:latest
    deploy:
      replicas: 3
    networks:
      - frontend

  api:
    image: myapp:latest
    deploy:
      replicas: 2
    networks:
      - frontend
      - backend

  db:
    image: postgres:15
    deploy:
      replicas: 1
    networks:
      - backend
    secrets:
      - db_password

networks:
  frontend:
  backend:

secrets:
  db_password:
    external: true
```

#### デプロイ
```bash
# Stackとして一括デプロイ
docker stack deploy -c docker-compose.yml myapp

# 内部で以下のServiceが自動作成される:
# - myapp_web
# - myapp_api
# - myapp_db
```

#### 確認
```bash
# Stack一覧
$ docker stack ls
NAME    SERVICES
myapp   3

# Stack内のService一覧
$ docker stack services myapp
ID          NAME        MODE        REPLICAS  IMAGE
abc123      myapp_web   replicated  3/3       nginx:latest
def456      myapp_api   replicated  2/2       myapp:latest
ghi789      myapp_db    replicated  1/1       postgres:15

# 個別Serviceの詳細
$ docker service ps myapp_web
```

---

### Service単独で作成

```bash
# Service単独作成（Stackなし）
docker service create \
  --name standalone-nginx \
  --replicas 3 \
  nginx:latest

# 確認
$ docker service ls
ID          NAME               MODE        REPLICAS
abc123      myapp_web          replicated  3/3
def456      myapp_api          replicated  2/2
ghi789      myapp_db           replicated  1/1
jkl012      standalone-nginx   replicated  3/3

# standalone-nginxはStackに属していない
```

---

## 命名規則

### Stack経由で作成した場合
```
{スタック名}_{サービス名}_{レプリカ番号}

例:
myapp_web_1
myapp_web_2
myapp_api_1
```

### Service単独で作成した場合
```
{サービス名}_{レプリカ番号}

例:
standalone-nginx_1
standalone-nginx_2
```

---

## 操作コマンドの違い

### Stackレベルの操作

```bash
# Stack全体をデプロイ（作成・更新）
docker stack deploy -c docker-compose.yml myapp

# Stack内の全Service確認
docker stack services myapp

# Stack内の全Task確認
docker stack ps myapp

# Stack全体を削除（全Service, Network, Volumeを削除）
docker stack rm myapp
```

### Serviceレベルの操作

```bash
# 個別Service確認
docker service ls
docker service ps myapp_web
docker service inspect myapp_web

# 個別Service更新
docker service update --image nginx:1.25 myapp_web
docker service update --replicas 5 myapp_web

# 個別Serviceロールバック
docker service rollback myapp_web

# 個別Service削除（Stackは残る）
docker service rm myapp_web

# 個別Service作成（Stack外）
docker service create --name test nginx
```

---

## docker-compose.yml の利用

### Docker Swarmでもdocker-compose.ymlは使用される ✅

**重要:** Docker Swarmは`docker-compose.yml`を利用しますが、**すべての機能が使えるわけではありません**。

### 使える機能 ✅

#### Swarmモードで有効な項目
```yaml
version: '3.8'

services:
  web:
    image: nginx:latest           # ✅ 使える
    ports:                         # ✅ 使える
      - "8080:80"
    environment:                   # ✅ 使える
      - ENV=production
    networks:                      # ✅ 使える
      - frontend
    volumes:                       # ✅ 使える
      - data:/var/lib/data
    secrets:                       # ✅ 使える（Swarm専用機能）
      - db_password
    configs:                       # ✅ 使える（Swarm専用機能）
      - nginx_config
    deploy:                        # ✅ 使える（Swarm専用セクション）
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
      placement:
        constraints:
          - node.role==worker
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M

networks:
  frontend:
    driver: overlay              # ✅ Swarm用オーバーレイネットワーク

volumes:
  data:
    driver: local

secrets:
  db_password:
    external: true

configs:
  nginx_config:
    file: ./nginx.conf
```

### 使えない機能 ❌

#### Swarmモードで無視される項目
```yaml
services:
  web:
    build: .                      # ❌ 使えない（イメージは事前ビルド必要）
    container_name: my-nginx      # ❌ 使えない（Swarmが自動命名）
    depends_on:                   # ❌ 使えない（起動順序制御なし）
      - db
    links:                        # ❌ 使えない（非推奨機能）
      - db
    restart: always               # ❌ 使えない（deploy.restart_policyを使う）
```

### Swarm専用セクション: `deploy`

```yaml
services:
  web:
    image: nginx:latest
    deploy:                        # ← Swarmモードでのみ有効
      mode: replicated             # replicated または global
      replicas: 4                  # レプリカ数

      update_config:               # ローリングアップデート設定
        parallelism: 1             # 同時更新数
        delay: 10s                 # 更新間隔
        failure_action: rollback   # 失敗時の動作
        monitor: 5s                # 監視時間
        max_failure_ratio: 0.2     # 失敗許容率
        order: start-first         # 更新順序

      rollback_config:             # ロールバック設定
        parallelism: 1
        delay: 5s

      restart_policy:              # 再起動ポリシー
        condition: on-failure      # 再起動条件
        delay: 5s                  # 再起動遅延
        max_attempts: 3            # 最大試行回数
        window: 120s               # 監視ウィンドウ

      placement:                   # 配置制約
        constraints:
          - node.role==worker      # ワーカーノードのみ
          - node.labels.env==prod  # 特定ラベル
        preferences:
          - spread: node.labels.zone  # 分散配置

      resources:                   # リソース制限
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M

      labels:                      # サービスラベル
        - "traefik.enable=true"
```

---

## 実践例: Stackを使った本番デプロイ

### ディレクトリ構成
```
myapp/
├── docker-compose.yml          # 共通設定
├── docker-compose.prod.yml     # 本番用オーバーライド
├── docker-compose.staging.yml  # ステージング用
├── .env.prod                   # 本番環境変数
├── .env.staging                # ステージング環境変数
└── configs/
    └── nginx.conf              # 設定ファイル
```

### docker-compose.yml（共通設定）
```yaml
version: '3.8'

services:
  web:
    image: myregistry.com/web:${VERSION}
    ports:
      - "8080:80"
    networks:
      - frontend
      - backend
    configs:
      - source: nginx_config
        target: /etc/nginx/nginx.conf
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s

  api:
    image: myregistry.com/api:${VERSION}
    environment:
      - DATABASE_URL=${DATABASE_URL}
    networks:
      - backend
    secrets:
      - db_password
    deploy:
      replicas: 2

  db:
    image: postgres:15
    environment:
      - POSTGRES_PASSWORD_FILE=/run/secrets/db_password
    networks:
      - backend
    volumes:
      - db_data:/var/lib/postgresql/data
    secrets:
      - db_password
    deploy:
      replicas: 1
      placement:
        constraints:
          - node.labels.type==database

networks:
  frontend:
    driver: overlay
  backend:
    driver: overlay

volumes:
  db_data:

secrets:
  db_password:
    external: true

configs:
  nginx_config:
    file: ./configs/nginx.conf
```

### docker-compose.prod.yml（本番用）
```yaml
version: '3.8'

services:
  web:
    deploy:
      replicas: 6                # 本番は多め
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M

  api:
    deploy:
      replicas: 4                # 本番は多め
```

### デプロイスクリプト
```bash
#!/bin/bash

# 環境変数読み込み
export $(cat .env.prod | xargs)

# 本番デプロイ
docker stack deploy \
  -c docker-compose.yml \
  -c docker-compose.prod.yml \
  production

# 状態確認
docker stack ps production
docker stack services production
```

---

## Stack vs Service: 使い分け

### Stackを使うべき場合 ✅
- ✅ **本番環境のデプロイ（最推奨）**
- ✅ **複数のサービスを含むアプリケーション**
- ✅ **Infrastructure as Code (IaC) を実現したい**
- ✅ **Network, Secret, Configを含む複雑な構成**
- ✅ **環境ごとに設定を変えたい**

### Service単独を使うべき場合
- ⚙️ **単一サービスの動作確認**
- ⚙️ **一時的なテスト**
- ⚙️ **Stack外で動作する独立したサービス**
- ⚙️ **緊急時の迅速な対応**

---

## よくある質問

### Q1: Stackを削除するとServiceも削除される？
**A:** はい、削除されます。
```bash
# Stack削除（全Service, Network, Volumeも削除）
docker stack rm myapp

# myapp_web, myapp_api, myapp_db すべて削除される
```

### Q2: Stack内の1つのServiceだけ更新できる？
**A:** はい、できます。
```bash
# 方法1: docker service update（直接更新）
docker service update --image nginx:1.25 myapp_web

# 方法2: docker-compose.ymlを編集して再deploy
# → 変更されたServiceのみ更新される
docker stack deploy -c docker-compose.yml myapp
```

### Q3: Stack名とService名の関係は？
**A:** `{Stack名}_{Service名}` で自動命名されます。
```yaml
# docker-compose.yml
services:
  web:    # ← サービス名
    ...

# デプロイ
docker stack deploy -c docker-compose.yml myapp
                                          ^^^^
                                          Stack名

# 結果: myapp_web というServiceが作成される
```

### Q4: docker-composeコマンドとの違いは？
**A:** 以下の通り:

| 項目 | `docker-compose` | `docker stack deploy` |
|:---|:---|:---|
| 対象 | 単一ホスト | Swarmクラスタ（複数ホスト） |
| オーケストレーション | なし | あり（自動スケジューリング） |
| スケーリング | 手動 | 自動（レプリカ管理） |
| ローリングアップデート | なし | あり |
| ヘルスチェック | 基本的 | 高度（自動再起動） |
| 本番使用 | 非推奨 | 推奨 |

```bash
# docker-compose（開発環境向け）
docker-compose up -d

# docker stack（本番環境向け）
docker stack deploy -c docker-compose.yml myapp
```

---

## まとめ

### 階層構造
```
Stack（アプリケーション全体）
  └── Service（マイクロサービス）
        └── Task（レプリカ）
              └── Container（実際のコンテナ）
```

### 関係性
| 概念 | 説明 | 作成コマンド |
|:---|:---|:---|
| **Stack** | 複数のServiceをグループ化 | `docker stack deploy` |
| **Service** | 1つのマイクロサービス | `docker service create` または Stack経由 |
| **Task** | Serviceのレプリカ（1インスタンス） | Swarmが自動作成 |
| **Container** | 実際のDockerコンテナ | Swarmが自動作成 |

### docker-compose.ymlの利用
- ✅ Docker Swarmでも`docker-compose.yml`は使用される
- ✅ `docker stack deploy`コマンドで読み込む
- ⚠️ ただし、`build`, `container_name`, `depends_on`などは使えない
- ✅ `deploy`セクションがSwarm専用の設定

### 推奨デプロイ方法
```bash
# 本番環境: Stack経由でService管理（推奨）
docker stack deploy -c docker-compose.yml production

# テスト・緊急時: Service直接操作
docker service update --image nginx:1.25 production_web
```

**結論: Stackはアプリケーション全体、ServiceはStackを構成する個々のコンポーネント**
