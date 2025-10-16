# Docker Swarmのサービス仕様保存の仕組み

## サービス状態の保存場所

Docker Swarmは**Raft consensus database**（分散合意データベース）にサービスの状態を保存します。

---

## 保存されるデータ構造

### サービスオブジェクトの構造

```json
{
  "ID": "sx24qtba051pf4nbdmy17dbjv",
  "Version": {
    "Index": 249
  },
  "CreatedAt": "2025-10-16T15:31:32Z",
  "UpdatedAt": "2025-10-16T15:49:25Z",

  "Spec": {                              // ← 現在の仕様
    "Name": "test4-3",
    "TaskTemplate": {
      "ContainerSpec": {
        "Image": "swarm-web:v5.0",     // ← 現在のイメージ
        "Env": [...],
        "Mounts": [...]
      },
      "Resources": {...},
      "Placement": {...}
    },
    "Mode": {
      "Replicated": {
        "Replicas": 4
      }
    },
    "UpdateConfig": {
      "Parallelism": 1,
      "Delay": 10000000000
    }
  },

  "PreviousSpec": {                      // ← 前回の仕様（ロールバック用）
    "Name": "test4-3",
    "TaskTemplate": {
      "ContainerSpec": {
        "Image": "swarm-web:v4.0",     // ← 前回のイメージ
        "Env": [...],
        "Mounts": [...]
      },
      "Resources": {...},
      "Placement": {...}
    },
    "Mode": {
      "Replicated": {
        "Replicas": 4
      }
    },
    "UpdateConfig": {
      "Parallelism": 1,
      "Delay": 10000000000
    }
  }
}
```

---

## 確認方法

### 現在の仕様（Spec）を確認

```bash
docker service inspect test4-3 --format '{{json .Spec}}' | python -m json.tool
```

**出力例:**
```json
{
    "Name": "test4-3",
    "TaskTemplate": {
        "ContainerSpec": {
            "Image": "swarm-web:v5.0"
        }
    },
    "Mode": {
        "Replicated": {
            "Replicas": 4
        }
    }
}
```

### 前回の仕様（PreviousSpec）を確認

```bash
docker service inspect test4-3 --format '{{json .PreviousSpec}}' | python -m json.tool
```

**出力例:**
```json
{
    "Name": "test4-3",
    "TaskTemplate": {
        "ContainerSpec": {
            "Image": "swarm-web:v4.0"
        }
    },
    "Mode": {
        "Replicated": {
            "Replicas": 4
        }
    }
}
```

### 実験：現在と前回のイメージを比較

```bash
echo "現在のイメージ:"
docker service inspect test4-3 --format '{{.Spec.TaskTemplate.ContainerSpec.Image}}'

echo "前回のイメージ:"
docker service inspect test4-3 --format '{{.PreviousSpec.TaskTemplate.ContainerSpec.Image}}'
```

**実行結果:**
```
現在のイメージ:
swarm-web:v5.0

前回のイメージ:
swarm-web:v4.0
```

---

## Raft Database の保存場所

### マネージャーノードのストレージ

Docker Swarmは**マネージャーノード**にRaftデータベースを保存します。

#### Linux/Mac
```
/var/lib/docker/swarm/state.json     # Swarm状態
/var/lib/docker/swarm/raft/          # Raftデータベース
  ├── snap-v3-encrypted/             # スナップショット
  └── wal-v3-encrypted/              # Write-Ahead Log
```

#### Windows
```
C:\ProgramData\Docker\swarm\state.json
C:\ProgramData\Docker\swarm\raft\
```

### Raftデータベースの特徴

**分散合意データベース**
- 全マネージャーノードで複製される
- 過半数のノードが稼働していれば動作
- 自動的に同期・一貫性維持

**保存される情報:**
- サービス定義（Spec, PreviousSpec）
- ノード情報
- ネットワーク設定
- Secret, Config
- タスクの状態

---

## Spec と PreviousSpec の更新タイミング

### 更新の流れ

```
┌─────────────────────────────────┐
│ 初期状態                         │
├─────────────────────────────────┤
│ Spec:         v1.0              │
│ PreviousSpec: (なし)            │
└─────────────────────────────────┘
          ↓ update to v2.0
┌─────────────────────────────────┐
│ 1回目の更新後                    │
├─────────────────────────────────┤
│ Spec:         v2.0  ← 新しい    │
│ PreviousSpec: v1.0  ← 保存された │
└─────────────────────────────────┘
          ↓ update to v3.0
┌─────────────────────────────────┐
│ 2回目の更新後                    │
├─────────────────────────────────┤
│ Spec:         v3.0  ← 新しい    │
│ PreviousSpec: v2.0  ← v1.0は消える │
└─────────────────────────────────┘
          ↓ rollback
┌─────────────────────────────────┐
│ ロールバック後                   │
├─────────────────────────────────┤
│ Spec:         v2.0  ← 復元      │
│ PreviousSpec: v3.0  ← 入れ替わり │
└─────────────────────────────────┘
```

### 重要なポイント

**1. PreviousSpecは1世代前のみ**
- 2世代以上前の履歴は保存されない
- v3.0からv1.0に直接ロールバック不可

**2. 更新のたびに上書きされる**
```
v1.0 → v2.0 → v3.0 → v4.0
     (v1.0は消失)
          (v2.0は消失)
               (v3.0は消失)
```

**3. ロールバックで前後が入れ替わる**
```
rollback実行前:
  Spec:         v3.0
  PreviousSpec: v2.0

rollback実行後:
  Spec:         v2.0
  PreviousSpec: v3.0  ← 入れ替わる
```

---

## イメージダイジェストの保存

### イメージの参照方法

Docker Swarmは**イメージダイジェスト**も自動的に記録します。

```bash
# タグで指定してデプロイ
docker service create --name web nginx:1.21

# 実際にはダイジェストも保存される
docker service inspect web --format '{{.Spec.TaskTemplate.ContainerSpec.Image}}'
# 出力: nginx:1.21@sha256:abc123...
```

### 確認方法

```bash
# 完全なイメージ参照情報
docker service inspect test4-3 \
  --format '{{.Spec.TaskTemplate.ContainerSpec.Image}}'

# 出力例:
# swarm-web:v5.0
# または
# swarm-web:v5.0@sha256:cb9794fdf059fd08...
```

### ダイジェストが保存されない場合

**ローカルイメージの場合:**
```
swarm-web:v5.0  # タグのみ（ダイジェストなし）
```

**レジストリからpullした場合:**
```
nginx:1.21@sha256:abc123...  # タグ + ダイジェスト
```

---

## 実験：更新とロールバックの動作確認

### 実験1: 更新履歴の追跡

```bash
# 初期状態
docker service create --name test --replicas 2 nginx:1.19
# Spec: nginx:1.19
# PreviousSpec: (なし)

# 1回目更新
docker service update --image nginx:1.20 test
# Spec: nginx:1.20
# PreviousSpec: nginx:1.19

# 2回目更新
docker service update --image nginx:1.21 test
# Spec: nginx:1.21
# PreviousSpec: nginx:1.20  ← 1.19は消えた

# ロールバック
docker service rollback test
# Spec: nginx:1.20
# PreviousSpec: nginx:1.21  ← 入れ替わった
```

### 実験2: 設定変更の追跡

```bash
# レプリカ数変更
docker service update --replicas 5 test
# Spec.Mode.Replicated.Replicas: 5
# PreviousSpec.Mode.Replicated.Replicas: 2

# ロールバックでレプリカ数も戻る
docker service rollback test
# Spec.Mode.Replicated.Replicas: 2  ← 戻った
```

---

## Version.Index の役割

### バージョン管理

```bash
docker service inspect test4-3 --format '{{json .Version}}'
```

**出力:**
```json
{
    "Index": 249
}
```

**Index とは:**
- サービスの更新回数を示すカウンター
- 更新のたびにインクリメント
- 楽観的ロック（Optimistic Locking）に使用

### 楽観的ロックの仕組み

```bash
# 古いIndexでの更新は失敗する
docker service update \
  --image nginx:latest \
  --version 100 \  # 古いIndex
  test
# エラー: update out of sequence
```

**用途:**
- 並行更新の競合を防止
- 「読み取り→変更→書き込み」の一貫性保証

---

## データの永続性と冗長性

### マネージャーノード間での複製

```
┌──────────────┐       ┌──────────────┐       ┌──────────────┐
│ Manager 1    │◄─────►│ Manager 2    │◄─────►│ Manager 3    │
│ (Leader)     │       │              │       │              │
├──────────────┤       ├──────────────┤       ├──────────────┤
│ Raft DB      │       │ Raft DB      │       │ Raft DB      │
│ - Spec       │ sync  │ - Spec       │ sync  │ - Spec       │
│ - PrevSpec   │◄─────►│ - PrevSpec   │◄─────►│ - PrevSpec   │
└──────────────┘       └──────────────┘       └──────────────┘
```

### 高可用性

**過半数のマネージャーが稼働していればOK**

| マネージャー数 | 許容障害数 |
|:---:|:---:|
| 1 | 0（単一障害点） |
| 3 | 1 |
| 5 | 2 |
| 7 | 3 |

### データ損失のリスク

**マネージャーノードが全滅した場合:**
- Raftデータベースが失われる
- Spec、PreviousSpecも消失
- サービス定義を再作成する必要がある

**対策:**
- 3台以上のマネージャーノード推奨
- 定期的なバックアップ
- Infrastructure as Code（docker-compose.yml等）

---

## バックアップとリストア

### サービス定義のバックアップ

```bash
# 全サービス定義をエクスポート
for service in $(docker service ls -q); do
  docker service inspect ${service} > backup-${service}.json
done
```

### リストア方法

```bash
# JSONから主要な設定を抽出して再作成
# （完全な自動リストアは困難）
docker service create \
  --name $(jq -r '.Spec.Name' backup.json) \
  --image $(jq -r '.Spec.TaskTemplate.ContainerSpec.Image' backup.json) \
  --replicas $(jq -r '.Spec.Mode.Replicated.Replicas' backup.json) \
  ...
```

### より良いバックアップ方法

**docker-compose.ymlで管理（推奨）**

```yaml
version: '3.8'
services:
  web:
    image: swarm-web:v5.0
    deploy:
      replicas: 4
      update_config:
        parallelism: 1
        delay: 10s
```

```bash
# バックアップ: docker-compose.ymlをGit管理
git add docker-compose.yml
git commit -m "Update to v5.0"

# リストア: Gitから取得してデプロイ
git checkout HEAD~1  # 1つ前のバージョン
docker stack deploy -c docker-compose.yml mystack
```

---

## まとめ

### 保存場所と仕組み

| 項目 | 詳細 |
|:---|:---|
| **保存場所** | Raft Database (`/var/lib/docker/swarm/raft/`) |
| **保存ノード** | 全マネージャーノード |
| **データ構造** | Spec（現在）+ PreviousSpec（前回）|
| **保存世代数** | 1世代前のみ |
| **同期方法** | Raft合意アルゴリズム |

### 重要なポイント

1. **PreviousSpecは1世代前のみ保存**
   - 2世代以上前は保存されない
   - ロールバックで前後が入れ替わる

2. **マネージャーノードが重要**
   - すべての状態はマネージャーに保存
   - ワーカーノードには保存されない

3. **完全な履歴管理には別の仕組みが必要**
   - docker-compose.ymlをGit管理
   - CI/CDでデプロイ履歴を記録
   - イメージダイジェストをログに保存

4. **自動バックアップはない**
   - Swarm自体にバックアップ機能はない
   - Infrastructure as Code推奨
