# Docker Swarm テストガイド

## 目次
1. [環境構築](#環境構築)
2. [テストケース一覧](#テストケース一覧)
3. [テスト実施手順](#テスト実施手順)
4. [クリーンアップ](#クリーンアップ)

---

## 環境構築

### 前提条件
- Dockerがインストールされていること
- ポート8080が使用可能であること

### 初期セットアップ

```bash
# 1. Swarmモード初期化
docker swarm init

# 2. イメージビルド
docker build -t swarm-web:latest .

# 3. マルチノード環境構築（オプション）
docker run -d --privileged --name worker1 --hostname worker1 docker:dind

# worker1にイメージをコピー
docker save swarm-web:latest | docker exec -i worker1 docker load

# worker1をSwarmクラスタに参加
MANAGER_IP=$(docker network inspect bridge --format='{{(index .IPAM.Config 0).Gateway}}')
JOIN_TOKEN=$(docker swarm join-token worker -q)
docker exec worker1 docker swarm join --token ${JOIN_TOKEN} ${MANAGER_IP}:2377

# 4. ノード確認
docker node ls
```

**期待結果:**
```
ID                            HOSTNAME         STATUS    AVAILABILITY   MANAGER STATUS   ENGINE VERSION
xxxxxxxxxxxxxxxxxxxxx *       docker-desktop   Ready     Active         Leader           28.x.x
xxxxxxxxxxxxxxxxxxxxx         worker1          Ready     Active                          28.x.x
```

---

## テストケース一覧

| # | テスト項目 | 目的 |
|:---|:---|:---|
| TC-01 | 基本デプロイメント | サービスの基本的なデプロイと動作確認 |
| TC-02 | ローリングアップデート | 無停止更新の動作確認 |
| TC-03 | スケーリング | レプリカ数の増減確認 |
| TC-04 | マルチノード負荷分散 | 複数ノードへの自動分散確認 |
| TC-05 | コンテナ異常終了 | 同一ノードでの自動再起動確認 |
| TC-06 | ヘルスチェック失敗 | ヘルスチェック失敗時の挙動確認 |
| TC-07 | ノード障害 | ノード障害時のフェイルオーバー確認 |
| TC-08 | 配置制約 | 特定ノードへの配置制御確認 |
| TC-09 | グローバルモード | 全ノード配置の確認 |

---

## テスト実施手順

### TC-01: 基本デプロイメント

**目的:** サービスの基本的なデプロイと動作確認

**実施手順:**
```bash
# サービスデプロイ
docker stack deploy -c docker-compose.yml swarm-test

# サービス状態確認
docker service ls

# タスク一覧確認
docker service ps swarm-test_web
```

**期待結果:**
- サービスが正常にデプロイされる
- REPLICAS が `3/3` になる
- 全タスクが `Running` 状態

**確認コマンド:**
```bash
docker service ls | grep swarm-test_web
```

**期待出力例:**
```
ID             NAME             MODE         REPLICAS   IMAGE              PORTS
xxxxx          swarm-test_web   replicated   3/3        swarm-web:latest   *:8080->5000/tcp
```

**動作確認:**
```bash
# Webアクセステスト
curl http://localhost:8080
```

---

### TC-02: ローリングアップデート

**目的:** 無停止でサービスを更新できることを確認

**実施手順:**
```bash
# 1. アプリケーション更新（バージョン表記を変更）
# app.pyの以下の行を変更:
# v2.0 → v3.0

# 2. イメージ再ビルド
docker build -t swarm-web:latest .

# 3. ローリングアップデート実行
docker service update --force swarm-test_web
```

**期待結果:**
- `parallelism: 1` の設定により、1つずつ順次更新される
- 各更新の間に10秒の遅延がある
- 更新中も他のレプリカがリクエストを処理し続ける
- 全レプリカが新バージョンに更新される

**確認コマンド:**
```bash
# 更新中の進捗確認
docker service ps swarm-test_web

# 完了後の確認
curl http://localhost:8080 | grep "v3.0"
```

**期待出力:**
```
overall progress: 1 out of 3 tasks  # 1つ目更新中
overall progress: 2 out of 3 tasks  # 2つ目更新中
overall progress: 3 out of 3 tasks  # 3つ目更新中
verify: Service converged
```

---

### TC-03: スケーリング

**目的:** レプリカ数を動的に変更できることを確認

**実施手順:**
```bash
# 1. スケールアップ（3→5）
docker service scale swarm-test_web=5

# 2. 状態確認
docker service ls

# 3. スケールダウン（5→2）
docker service scale swarm-test_web=2

# 4. 最終確認
docker service ps swarm-test_web --filter "desired-state=running"
```

**期待結果:**
- スケールアップ: 2つのレプリカが追加される
- スケールダウン: 3つのレプリカが削除される
- サービスは中断なく継続

**確認コマンド:**
```bash
docker service ls | grep swarm-test_web | awk '{print $4}'
```

**期待出力:**
```
2/2  # スケールダウン後
```

---

### TC-04: マルチノード負荷分散

**目的:** 複数ノード間で自動的に負荷分散されることを確認

**前提条件:** worker1ノードが追加済み

**実施手順:**
```bash
# 1. レプリカ数を増やす
docker service scale swarm-test_web=8

# 2. ノードごとの配置確認
docker service ps swarm-test_web --filter "desired-state=running" \
  --format "table {{.Name}}\t{{.Node}}\t{{.CurrentState}}"

# 3. ノード別集計
docker service ps swarm-test_web --filter "desired-state=running" \
  --format "{{.Node}}" | sort | uniq -c
```

**期待結果:**
- 8つのレプリカが2ノードに分散配置される
- 各ノードに約4つずつ配置される（Spread戦略）

**期待出力例:**
```
      4 docker-desktop
      4 worker1
```

---

### TC-05: コンテナ異常終了

**目的:** コンテナがクラッシュした場合、同一ノードで再起動されることを確認

**実施手順:**
```bash
# 1. worker1上で動作中のコンテナIDを取得
CONTAINER_ID=$(docker exec worker1 docker ps --filter "name=swarm-test_web" \
  --format "{{.ID}}" | head -1)

# 2. 異常終了前の状態を記録
docker service ps swarm-test_web --filter "name=swarm-test_web.3" \
  --format "table {{.Name}}\t{{.Node}}\t{{.CurrentState}}"

# 3. コンテナを強制終了
docker exec worker1 docker kill ${CONTAINER_ID}

# 4. 5秒待機
sleep 5

# 5. 異常終了後の状態を確認
docker service ps swarm-test_web --filter "name=swarm-test_web.3" \
  --format "table {{.Name}}\t{{.Node}}\t{{.CurrentState}}\t{{.Error}}"
```

**期待結果:**
- コンテナが異常終了する
- **同じノード（worker1）**で自動的に再起動される
- エラーログに `task: non-zero exit (137)` が記録される

**期待出力例:**
```
NAME                   NODE      CURRENT STATE            ERROR
swarm-test_web.3       worker1   Running 5 seconds ago
 \_ swarm-test_web.3   worker1   Failed 10 seconds ago    "task: non-zero exit (137)"
```

---

### TC-06: ヘルスチェック失敗

**目的:** ヘルスチェック失敗時も同一ノードで再起動されることを確認

**実施手順:**
```bash
# 1. ヘルスチェック失敗テスト用イメージビルド
docker build -f Dockerfile.unhealthy -t unhealthy-app:latest .

# worker1にもコピー
docker save unhealthy-app:latest | docker exec -i worker1 docker load

# 2. テストサービス作成（30秒後にヘルスチェック失敗）
docker service create --name unhealthy-test \
  --replicas 2 \
  --health-cmd "python -c \"import urllib.request; urllib.request.urlopen('http://localhost:5000/health')\"" \
  --health-interval 5s \
  --health-retries 2 \
  --health-start-period 5s \
  unhealthy-app:latest

# 3. 初期配置確認
docker service ps unhealthy-test --format "table {{.Name}}\t{{.Node}}\t{{.CurrentState}}"

# 4. 35秒待機（ヘルスチェック失敗を待つ）
sleep 35

# 5. 失敗後の状態確認
docker service ps unhealthy-test --format "table {{.Name}}\t{{.Node}}\t{{.CurrentState}}"
```

**期待結果:**
- 30秒経過後、ヘルスチェックが失敗する
- コンテナが自動的に再起動される
- **同じノード**で再起動される

**期待出力例:**
```
NAME                   NODE             CURRENT STATE
unhealthy-test.1       docker-desktop   Running 2 seconds ago
 \_ unhealthy-test.1   docker-desktop   Failed 10 seconds ago
unhealthy-test.2       worker1          Running 1 second ago
 \_ unhealthy-test.2   worker1          Failed 11 seconds ago
```

---

### TC-07: ノード障害

**目的:** ノード障害時に他のノードへフェイルオーバーされることを確認

**実施手順:**
```bash
# 1. 障害前の配置確認
docker service ps swarm-test_web --filter "desired-state=running" \
  --format "{{.Node}}" | sort | uniq -c

# 2. worker1を停止（ノード障害をシミュレート）
docker stop worker1

# 3. ノード状態確認
docker node ls

# 4. 15秒待機（再スケジューリングを待つ）
sleep 15

# 5. 障害後の配置確認
docker service ps swarm-test_web --filter "desired-state=running" \
  --format "{{.Node}}" | sort | uniq -c

# 6. 詳細確認
docker service ps swarm-test_web --format "table {{.Name}}\t{{.Node}}\t{{.DesiredState}}\t{{.CurrentState}}"
```

**期待結果:**
- worker1がDownになる
- worker1上のタスクが終了する
- docker-desktopに全タスクが再配置される
- サービスのレプリカ数が維持される

**期待出力:**
```
# 障害前
      4 docker-desktop
      4 worker1

# 障害後
      8 docker-desktop
```

**ノード復旧テスト:**
```bash
# 1. worker1再起動
docker start worker1

# 2. 5秒待機
sleep 5

# 3. ノード状態確認
docker node ls

# 4. 配置確認（自動では再分散されない）
docker service ps swarm-test_web --filter "desired-state=running" \
  --format "{{.Node}}" | sort | uniq -c

# 5. 手動再分散
docker service update --force swarm-test_web

# 6. 再分散後の確認
docker service ps swarm-test_web --filter "desired-state=running" \
  --format "{{.Node}}" | sort | uniq -c
```

**期待結果:**
- worker1が復旧する
- 自動では再分散されない（全タスクがdocker-desktopのまま）
- `--force`更新後、再び均等分散される

---

### TC-08: 配置制約

**目的:** 特定ノードにのみサービスを配置できることを確認

**実施手順:**
```bash
# 1. ノードにラベル追加
docker node update --label-add type=frontend worker1

# 2. ラベル確認
docker node inspect worker1 --format '{{json .Spec.Labels}}' | python -m json.tool

# 3. 配置制約付きサービス作成
docker service create --name nginx-frontend \
  --constraint 'node.labels.type==frontend' \
  --replicas 3 \
  nginx:alpine

# 4. 配置確認
docker service ps nginx-frontend --format "table {{.Name}}\t{{.Node}}\t{{.CurrentState}}"

# 5. ノード別集計
docker service ps nginx-frontend --format "{{.Node}}" | sort | uniq -c
```

**期待結果:**
- 全レプリカがworker1にのみ配置される
- docker-desktopには配置されない

**期待出力:**
```
      3 worker1
```

---

### TC-09: グローバルモード

**目的:** 全ノードに必ず1つずつタスクが配置されることを確認

**実施手順:**
```bash
# 1. グローバルモードサービス作成
docker service create --name monitor \
  --mode global \
  alpine ping 8.8.8.8

# 2. 配置確認
docker service ps monitor --format "table {{.Name}}\t{{.Node}}\t{{.CurrentState}}"

# 3. ノード別集計
docker service ps monitor --format "{{.Node}}" | sort | uniq -c
```

**期待結果:**
- 各ノードに1つずつタスクが配置される
- ノード数とタスク数が一致する

**期待出力:**
```
      1 docker-desktop
      1 worker1
```

---

## クリーンアップ

### 全サービスの停止と削除

```bash
# 1. 全サービス削除
docker service rm $(docker service ls -q)

# または個別削除
docker service rm swarm-test_web
docker service rm unhealthy-test
docker service rm nginx-frontend
docker service rm monitor

# 2. スタック削除
docker stack rm swarm-test

# 3. worker1コンテナ停止・削除
docker stop worker1
docker rm worker1

# 4. Swarmモード終了
docker swarm leave --force

# 5. 未使用イメージ削除
docker image rm swarm-web:latest unhealthy-app:latest

# 6. 確認
docker service ls
docker node ls
```

**期待結果:**
- 全サービスが削除される
- Swarmモードが無効化される
- `Error response from daemon: This node is not a swarm manager.` が表示される

---

## トラブルシューティング

### イメージが見つからない場合
```bash
# イメージ再ビルド
docker build -t swarm-web:latest .

# worker1にコピー
docker save swarm-web:latest | docker exec -i worker1 docker load
```

### ポート競合の場合
```bash
# docker-compose.ymlのポート変更
# ports: "8080:5000" → "8081:5000"

# または既存サービスを削除
docker service rm swarm-test_web
```

### ノードがDownのまま復旧しない場合
```bash
# ノードを強制削除
docker node rm worker1 --force

# worker1コンテナ再作成
docker rm worker1
docker run -d --privileged --name worker1 --hostname worker1 docker:dind
# 再度join処理を実施
```

---

## テスト結果サマリー

| TC | テスト項目 | 結果 | 備考 |
|:---|:---|:---:|:---|
| TC-01 | 基本デプロイメント | ✅ | 3レプリカが正常起動 |
| TC-02 | ローリングアップデート | ✅ | 1つずつ10秒間隔で更新 |
| TC-03 | スケーリング | ✅ | 動的な増減が可能 |
| TC-04 | マルチノード負荷分散 | ✅ | 4:4で均等分散 |
| TC-05 | コンテナ異常終了 | ✅ | 同一ノードで再起動 |
| TC-06 | ヘルスチェック失敗 | ✅ | 同一ノードで再起動 |
| TC-07 | ノード障害 | ✅ | 他ノードへフェイルオーバー |
| TC-08 | 配置制約 | ✅ | 指定ノードのみに配置 |
| TC-09 | グローバルモード | ✅ | 全ノードに1つずつ配置 |

---

## 重要な発見事項

### コンテナ再起動時のノード配置ルール

1. **コンテナ異常終了**: 同一ノードで再起動
2. **ヘルスチェック失敗**: 同一ノードで再起動
3. **ノード障害**: 別の健全なノードに再配置

### 自動vs手動の挙動

- **ノード障害→復旧**: 自動では元のノードに戻らない
- **再分散が必要な場合**: `docker service update --force` を実行

### ヘルスチェックの役割

- コンテナレベルの健全性監視
- ノード選択には直接影響しない
- 異常検知後の再起動トリガーとして機能
