# Docker Swarm 動作確認サンプル

## 概要
Docker Swarmの基本的な動作を確認するための簡単なWebアプリケーションです。
シングルノード・マルチノード構成の両方に対応し、以下の機能を学習できます：
- サービスのデプロイと負荷分散
- ローリングアップデート
- ヘルスチェックと自動再起動
- ノード障害時のフェイルオーバー
- 配置制約とグローバルモード

## プロジェクト構成
```
swarm/
├── app.py                 # Flask Webアプリケーション（メイン）
├── unhealthy-app.py       # ヘルスチェックテスト用アプリ
├── Dockerfile             # メインアプリのイメージ定義
├── Dockerfile.unhealthy   # テスト用アプリのイメージ定義
├── requirements.txt       # Python依存パッケージ
├── docker-compose.yml     # Swarmデプロイ設定
├── README.md             # このファイル
├── TEST_GUIDE.md         # 詳細なテストガイド
└── placement-examples.md # 配置戦略の例
```

## 技術スタック
- Python 3.11
- Flask 3.0.0
- Docker Swarm
- Docker-in-Docker (マルチノードテスト用)

## クイックスタート

### シングルノード構成

```bash
# 1. Swarmモード初期化
docker swarm init

# 2. イメージビルド
docker build -t swarm-web:latest .

# 3. スタックデプロイ
docker stack deploy -c docker-compose.yml swarm-test

# 4. 動作確認
docker service ls
curl http://localhost:8080
```

### マルチノード構成（Docker-in-Docker使用）

```bash
# 1. Swarmモード初期化
docker swarm init

# 2. イメージビルド
docker build -t swarm-web:latest .

# 3. ワーカーノード作成
docker run -d --privileged --name worker1 --hostname worker1 docker:dind

# 4. イメージをworker1にコピー
docker save swarm-web:latest | docker exec -i worker1 docker load

# 5. worker1をSwarmに参加
MANAGER_IP=$(docker network inspect bridge --format='{{(index .IPAM.Config 0).Gateway}}')
JOIN_TOKEN=$(docker swarm join-token worker -q)
docker exec worker1 docker swarm join --token ${JOIN_TOKEN} ${MANAGER_IP}:2377

# 6. ノード確認
docker node ls

# 7. スタックデプロイ
docker stack deploy -c docker-compose.yml swarm-test

# 8. 配置確認
docker service ps swarm-test_web --format "{{.Node}}" | sort | uniq -c
```

## 基本操作

### サービス管理

```bash
# サービス一覧表示
docker service ls

# レプリカの詳細確認
docker service ps swarm-test_web

# サービスログ確認
docker service logs swarm-test_web

# スケーリング
docker service scale swarm-test_web=5

# サービス更新
docker service update --force swarm-test_web
```

### ノード管理

```bash
# ノード一覧
docker node ls

# ノードにラベル追加
docker node update --label-add env=production worker1

# ノード詳細確認
docker node inspect worker1
```

## 主要機能

### 1. ヘルスチェック
- `/health` エンドポイントでコンテナの健全性確認
- Python標準ライブラリを使用（curlが不要）
- 失敗時は自動的に再起動

### 2. ローリングアップデート
- `parallelism: 1` - 1つずつ順番に更新
- `delay: 10s` - 各更新の間に10秒待機
- 無停止でサービス更新可能

### 3. 負荷分散
- Spread戦略により複数ノードに均等分散
- ポート8080でアクセス可能
- リロードで異なるコンテナが応答

### 4. 自動フェイルオーバー
- コンテナ異常終了 → 同一ノードで再起動
- ヘルスチェック失敗 → 同一ノードで再起動
- ノード障害 → 別ノードに再配置

## テスト

詳細なテストガイドは [TEST_GUIDE.md](TEST_GUIDE.md) を参照してください。

### テストケース概要

| # | テスト項目 | 説明 |
|:---|:---|:---|
| TC-01 | 基本デプロイメント | サービスの基本動作確認 |
| TC-02 | ローリングアップデート | 無停止更新の確認 |
| TC-03 | スケーリング | レプリカ数の動的変更 |
| TC-04 | マルチノード負荷分散 | 複数ノードへの分散確認 |
| TC-05 | コンテナ異常終了 | 同一ノードでの再起動確認 |
| TC-06 | ヘルスチェック失敗 | ヘルスチェック失敗時の挙動 |
| TC-07 | ノード障害 | フェイルオーバー確認 |
| TC-08 | 配置制約 | 特定ノードへの配置制御 |
| TC-09 | グローバルモード | 全ノード配置の確認 |

### クイックテスト

```bash
# スケーリングテスト
docker service scale swarm-test_web=8
docker service ps swarm-test_web --format "{{.Node}}" | sort | uniq -c

# 配置制約テスト
docker node update --label-add type=frontend worker1
docker service create --name test --constraint 'node.labels.type==frontend' --replicas 2 nginx:alpine
docker service ps test
```

## クリーンアップ

### すべて削除

```bash
# 全サービス削除
docker service rm $(docker service ls -q)

# スタック削除
docker stack rm swarm-test

# worker1削除
docker stop worker1
docker rm worker1

# Swarmモード終了
docker swarm leave --force
```

### 個別削除

```bash
# 特定サービス削除
docker service rm swarm-test_web

# 未使用イメージ削除
docker image rm swarm-web:latest unhealthy-app:latest
```

## 学習のポイント

### Docker Swarmの基礎
- クラスタ管理とオーケストレーション
- サービス vs タスク vs コンテナの違い
- マネージャーノードとワーカーノードの役割

### 高可用性
- レプリカによる冗長化
- 自動再起動とフェイルオーバー
- ヘルスチェックの重要性

### デプロイ戦略
- ローリングアップデートの仕組み
- 配置制約（Placement Constraints）
- レプリケートモード vs グローバルモード

### 運用
- スケーリングの方法
- ノード管理とラベル付け
- ログとトラブルシューティング

## トラブルシューティング

### サービスが起動しない

```bash
# 詳細情報確認
docker service inspect swarm-test_web

# エラーログ確認
docker service ps swarm-test_web --no-trunc

# タスクのログ確認
docker service logs swarm-test_web
```

### ヘルスチェックで失敗する

```bash
# ヘルスチェック設定確認
docker service inspect swarm-test_web --format '{{json .Spec.TaskTemplate.ContainerSpec.Healthcheck}}'

# コンテナ内でヘルスチェック手動実行
docker exec <container_id> python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')"
```

### ポート競合

```bash
# ポート使用状況確認
netstat -ano | findstr :8080  # Windows
lsof -i :8080                # Linux/Mac

# docker-compose.ymlでポート変更
# ports: "8081:5000"
```

### イメージが見つからない

```bash
# イメージ一覧確認
docker images | grep swarm-web

# 再ビルド
docker build -t swarm-web:latest .

# worker1にコピー
docker save swarm-web:latest | docker exec -i worker1 docker load
```

### ノードがDownのまま

```bash
# ノード削除
docker node rm worker1 --force

# コンテナ再作成
docker stop worker1
docker rm worker1
docker run -d --privileged --name worker1 --hostname worker1 docker:dind

# 再度join
MANAGER_IP=$(docker network inspect bridge --format='{{(index .IPAM.Config 0).Gateway}}')
JOIN_TOKEN=$(docker swarm join-token worker -q)
docker exec worker1 docker swarm join --token ${JOIN_TOKEN} ${MANAGER_IP}:2377
```

## 参考資料

- [Docker Swarm公式ドキュメント](https://docs.docker.com/engine/swarm/)
- [TEST_GUIDE.md](TEST_GUIDE.md) - 詳細なテスト手順
- [placement-examples.md](placement-examples.md) - 配置戦略の例

## ライセンス

このプロジェクトはテスト・学習目的で作成されています。

## 注意事項

- Docker-in-Dockerを使用したマルチノード構成は**テスト目的のみ**です
- 本番環境では実際の複数マシンまたはVMを使用してください
- ネットワーク設定は環境に応じて調整が必要な場合があります
