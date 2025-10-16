# 本番運用でのデプロイ方法

## デプロイ方法の比較

Docker Swarmの本番運用では主に**2つのデプロイ方法**があります。

---

## 方法1: `docker stack deploy` (docker-compose.yml使用) ✅ **推奨**

### コマンド
```bash
docker stack deploy -c docker-compose.yml mystack
```

### 特徴

#### メリット ✅
1. **Infrastructure as Code (IaC)**
   - すべての設定がYAMLファイルに記述
   - Gitでバージョン管理可能
   - レビュー・監査が容易

2. **複数サービスの一括管理**
   - web, api, db, cache など複数サービスを一度にデプロイ
   - サービス間の依存関係を定義可能

3. **宣言的な管理**
   - 「あるべき状態」を定義
   - Docker Swarmが自動的に現在の状態と比較して更新

4. **環境変数・Secret管理**
   - `.env`ファイルで環境ごとの設定管理
   - Docker Secretとの統合

5. **再現性が高い**
   - 同じYAMLファイルで他の環境に展開可能
   - ステージング → 本番 の移行が容易

#### デメリット ❌
1. **YAMLの編集が必要**
   - イメージタグの更新にはファイル編集が必要
   - 緊急時は手間がかかる

2. **Stack全体が対象**
   - 1サービスだけ更新する場合も全体を再デプロイ
   - （実際には変更されたサービスのみ更新されるが）

### 使用ケース

- ✅ **通常の本番デプロイ（最推奨）**
- ✅ **新機能のリリース**
- ✅ **設定変更（環境変数、レプリカ数など）**
- ✅ **複数サービスの同時更新**
- ✅ **初回デプロイ**

### 実践例

#### docker-compose.yml
```yaml
version: '3.8'

services:
  web:
    image: myregistry.com/web:v1.2.3
    deploy:
      replicas: 4
      update_config:
        parallelism: 1
        delay: 10s
        failure_action: rollback
        order: start-first
      rollback_config:
        parallelism: 1
        delay: 5s
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
    environment:
      - DATABASE_URL=${DATABASE_URL}
    secrets:
      - db_password
    networks:
      - frontend

  api:
    image: myregistry.com/api:v2.0.1
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
    networks:
      - frontend
      - backend

secrets:
  db_password:
    external: true

networks:
  frontend:
  backend:
```

#### デプロイ手順
```bash
# 1. Gitから最新のdocker-compose.ymlを取得
git pull origin main

# 2. 環境変数ファイルを用意
cat > .env <<EOF
DATABASE_URL=postgres://db:5432/myapp
EOF

# 3. デプロイ実行
docker stack deploy -c docker-compose.yml production

# 出力:
# Creating network production_frontend
# Creating network production_backend
# Creating service production_web
# Creating service production_api

# 4. 状態確認
docker stack ps production
```

#### 更新時の手順
```bash
# 1. docker-compose.ymlのイメージタグを更新
# image: myregistry.com/web:v1.2.3
# ↓
# image: myregistry.com/web:v1.2.4

# 2. Gitにコミット
git add docker-compose.yml
git commit -m "Update web to v1.2.4"
git push

# 3. 本番環境で再デプロイ
docker stack deploy -c docker-compose.yml production

# 出力:
# Updating service production_web (id: xyz123)
# （変更されたサービスのみローリングアップデート）

# 4. 更新状況確認
docker service ps production_web
```

---

## 方法2: `docker service update` (コマンド直接実行)

### コマンド
```bash
docker service update --image myregistry.com/web:v1.2.4 production_web
```

### 特徴

#### メリット ✅
1. **緊急時の迅速な対応**
   - 1コマンドで即座に実行
   - YAMLファイル編集不要

2. **単一サービスのみ更新**
   - 他のサービスに影響なし
   - 最小限の変更

3. **柔軟な更新パラメータ**
   - 更新ごとに異なる設定を適用可能
   - 一時的な設定変更に便利

#### デメリット ❌
1. **Infrastructure as Codeから外れる**
   - YAMLファイルと実際の状態が乖離
   - Git履歴に残らない

2. **再現性が低い**
   - 同じ状態を他の環境に展開しにくい
   - どの設定でデプロイしたか不明確

3. **監査証跡が不完全**
   - コマンド履歴に頼ることになる
   - レビュープロセスを経ない

### 使用ケース

- ✅ **緊急のホットフィックス**
- ✅ **一時的なスケールアウト**
- ✅ **トラブル時の迅速なロールバック**
- ✅ **実験的な設定変更**

### 実践例

#### イメージ更新
```bash
# 緊急でセキュリティパッチを適用
docker service update --image myregistry.com/web:v1.2.4-hotfix production_web
```

#### スケール調整
```bash
# 急なトラフィック増加に対応
docker service update --replicas 8 production_web

# 落ち着いたら元に戻す
docker service update --replicas 4 production_web
```

#### 環境変数追加
```bash
# デバッグモードを一時的に有効化
docker service update --env-add DEBUG=true production_web

# 後で削除
docker service update --env-rm DEBUG production_web
```

---

## 本番運用での推奨フロー

### 標準デプロイ手順（最推奨）

```bash
# === CI/CDパイプライン ===

# 1. イメージビルド
docker build -t myregistry.com/web:${VERSION} .

# 2. レジストリにプッシュ
docker push myregistry.com/web:${VERSION}

# 3. docker-compose.yml更新（自動またはPR）
sed -i "s|image: myregistry.com/web:.*|image: myregistry.com/web:${VERSION}|" docker-compose.yml

# 4. Gitにコミット
git add docker-compose.yml
git commit -m "Deploy web ${VERSION}"
git push

# === 本番環境 ===

# 5. 本番サーバーでGitから取得
git pull origin main

# 6. デプロイ実行
docker stack deploy -c docker-compose.yml production

# 7. 状態確認
docker stack ps production
docker service ps production_web

# 8. ヘルスチェック
curl https://production-web.example.com/health
```

### 緊急ロールバック手順

#### パターンA: Gitで管理されている場合（推奨）
```bash
# 1. 前のバージョンにGitで戻す
git revert HEAD
# または
git checkout HEAD~1 docker-compose.yml

# 2. 再デプロイ
docker stack deploy -c docker-compose.yml production
```

#### パターンB: 緊急時（最速）
```bash
# 1. docker service rollback で即座にロールバック
docker service rollback production_web

# 2. 後でGitも整合させる
git revert HEAD
git push
```

---

## 環境別の推奨デプロイ方法

| 環境 | 推奨方法 | 理由 |
|:---|:---|:---|
| **本番 (Production)** | `docker stack deploy` | IaC、監査証跡、再現性 |
| **ステージング (Staging)** | `docker stack deploy` | 本番と同じ手順で検証 |
| **開発 (Development)** | `docker stack deploy` または `docker service update` | 柔軟性重視、どちらでもOK |
| **ローカル検証** | `docker service update` | 迅速な試行錯誤 |

---

## 実際の本番運用例

### 例1: 大規模WebサービスのCI/CD

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      # 1. イメージビルド
      - name: Build Docker image
        run: |
          docker build -t myregistry.com/web:${{ github.sha }} .

      # 2. レジストリにプッシュ
      - name: Push to registry
        run: |
          docker push myregistry.com/web:${{ github.sha }}

      # 3. docker-compose.yml更新
      - name: Update docker-compose.yml
        run: |
          sed -i "s|image: myregistry.com/web:.*|image: myregistry.com/web:${{ github.sha }}|" docker-compose.yml
          git add docker-compose.yml
          git commit -m "Deploy ${{ github.sha }}"
          git push

      # 4. 本番デプロイ
      - name: Deploy to production
        run: |
          ssh production-server "cd /opt/app && git pull && docker stack deploy -c docker-compose.yml production"
```

### 例2: Blue-Green デプロイ

```bash
# Blue環境（現在の本番）
docker stack deploy -c docker-compose.yml production-blue

# Green環境（新バージョン）を並行デプロイ
docker stack deploy -c docker-compose-green.yml production-green

# 動作確認後、ロードバランサーを切り替え
# 切り替え後、Blue環境を削除
docker stack rm production-blue

# Green環境をBlueにリネーム
docker stack deploy -c docker-compose-green.yml production-blue
docker stack rm production-green
```

---

## ベストプラクティス

### 1. YAMLファイルのバージョン管理
```bash
# Gitで管理
git add docker-compose.yml
git commit -m "Update to v1.2.4"
git tag v1.2.4
git push --tags
```

### 2. 環境ごとのファイル分離
```
project/
├── docker-compose.yml          # 共通設定
├── docker-compose.prod.yml     # 本番用オーバーライド
├── docker-compose.staging.yml  # ステージング用
└── .env.example                # 環境変数のサンプル
```

```bash
# 本番デプロイ
docker stack deploy \
  -c docker-compose.yml \
  -c docker-compose.prod.yml \
  production

# ステージングデプロイ
docker stack deploy \
  -c docker-compose.yml \
  -c docker-compose.staging.yml \
  staging
```

### 3. イメージタグの管理

❌ **非推奨: latestタグ**
```yaml
services:
  web:
    image: myregistry.com/web:latest  # 何のバージョンか不明
```

✅ **推奨: セマンティックバージョニング**
```yaml
services:
  web:
    image: myregistry.com/web:v1.2.4  # 明確なバージョン
```

✅ **より推奨: Git SHA**
```yaml
services:
  web:
    image: myregistry.com/web:abc123def  # コミットと紐付け
```

✅ **最推奨: ダイジェスト**
```yaml
services:
  web:
    image: myregistry.com/web@sha256:abc123...  # 完全に不変
```

### 4. デプロイ前のチェックリスト

- [ ] 新イメージがレジストリにプッシュ済み
- [ ] ステージング環境でテスト完了
- [ ] docker-compose.ymlの構文チェック (`docker-compose config`)
- [ ] ロールバック手順の確認
- [ ] 監視ダッシュボードの準備
- [ ] 関係者への通知

### 5. デプロイ後の確認

```bash
# 1. サービス状態確認
docker service ps production_web

# 2. ログ確認
docker service logs production_web --tail 100

# 3. ヘルスチェック
curl https://api.example.com/health

# 4. メトリクス確認
# - レスポンスタイム
# - エラー率
# - CPU/メモリ使用率
```

---

## まとめ

### 結論

**本番運用では `docker stack deploy` が推奨**

理由:
- ✅ Infrastructure as Code (IaC)
- ✅ Gitでバージョン管理
- ✅ 再現性が高い
- ✅ 監査証跡が明確
- ✅ レビュープロセスを経る
- ✅ 複数サービスを統一的に管理

**`docker service update` は緊急時のみ**

使用場面:
- ⚡ 緊急ホットフィックス
- ⚡ 一時的なスケール調整
- ⚡ 迅速なロールバック
- ⚡ 実験的な変更

### 推奨デプロイフロー

```
開発 → Gitにコミット → CI/CD → イメージビルド → レジストリプッシュ
→ docker-compose.yml更新 → Gitにコミット → 本番サーバーでGit Pull
→ docker stack deploy → 監視 → 問題あればGitで戻して再deploy
```

### 最も重要なポイント

**「本番環境の状態 = Gitのdocker-compose.yml」を維持する**

これにより:
- 現在の状態が常に明確
- 履歴が完全に追跡可能
- 障害時の復旧が容易
- 他の環境への展開が簡単
