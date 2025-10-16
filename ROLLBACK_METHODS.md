# ロールバック方法の比較

## 2つのロールバック方法

Docker Swarmでサービスを前のバージョンに戻す方法は**2つ**あります。

---

## 方法1: `docker service rollback`（推奨）

### コマンド
```bash
docker service rollback <service-name>
```

### 動作

**PreviousSpec（前回の状態）を使用して自動的に復元**

```
┌─────────────────────┐
│  Current Spec       │  ← 現在の状態（v5.0）
│  Image: v5.0        │
│  Replicas: 4        │
│  UpdateConfig: ...  │
└─────────────────────┘
           ↓ rollback
┌─────────────────────┐
│  Previous Spec      │  ← 前回の状態（v4.0）
│  Image: v4.0        │  ← イメージだけでなく
│  Replicas: 4        │  ← すべての設定が復元される
│  UpdateConfig: ...  │
└─────────────────────┘
```

### 実行例

```bash
# ロールバック実行
$ docker service rollback test4-3
test4-3
rollback: manually requested rollback
overall progress: rolling back update: 4 out of 4 tasks
verify: Service test4-3 converged
rollback: rollback completed

# 確認
$ docker service inspect test4-3 --format '{{.Spec.TaskTemplate.ContainerSpec.Image}}'
swarm-web:v4.0  # v5.0 → v4.0 に戻った
```

### 特徴

#### メリット ✅
1. **最もシンプル**
   - 1コマンドで実行
   - バージョンを指定する必要なし

2. **完全な状態復元**
   - イメージだけでなく、すべての設定が戻る
   - レプリカ数、環境変数、リソース制限なども復元

3. **安全性が高い**
   - 直前の動作確認済み状態に戻る
   - 人的ミス（バージョン指定間違い）がない

4. **更新設定が適用される**
   - `update-parallelism`, `update-delay` が使用される
   - 段階的なロールバック

#### デメリット ❌
1. **1世代前にしか戻れない**
   - v5.0 → v4.0 ○
   - v5.0 → v3.0 ✕（直接は不可）

2. **PreviousSpecが必要**
   - 初回デプロイ後は使用不可
   - サービス削除後の再作成では使用不可

### 使用ケース

- ✅ **直前の更新を取り消したい**
- ✅ **緊急時の迅速な復旧**
- ✅ **本番環境での標準的なロールバック**
- ✅ **設定も含めて完全に戻したい**

---

## 方法2: `docker service update --image`（手動指定）

### コマンド
```bash
docker service update --image <image>:<version> <service-name>
```

### 動作

**指定したイメージに更新（通常の更新と同じ）**

```
┌─────────────────────┐
│  Current Spec       │
│  Image: v5.0        │
└─────────────────────┘
           ↓ update
┌─────────────────────┐
│  New Spec           │
│  Image: v4.0        │  ← 手動で指定したバージョン
└─────────────────────┘
```

### 実行例

#### イメージタグで指定
```bash
# v4.0に戻す
$ docker service update --image swarm-web:v4.0 test4-3
test4-3
overall progress: 4 out of 4 tasks
verify: Service test4-3 converged

# 確認
$ docker service inspect test4-3 --format '{{.Spec.TaskTemplate.ContainerSpec.Image}}'
swarm-web:v4.0
```

#### イメージダイジェスト（ハッシュ値）で指定
```bash
# イメージダイジェスト確認
$ docker inspect swarm-web:v4.0 --format '{{.RepoDigests}}'
[swarm-web@sha256:abc123...]

# ダイジェストで指定（最も確実）
$ docker service update \
  --image swarm-web@sha256:abc123... \
  test4-3
```

### 特徴

#### メリット ✅
1. **任意のバージョンに変更可能**
   - v5.0 → v4.0 ○
   - v5.0 → v3.0 ○
   - v5.0 → v2.0 ○（何世代でも遡れる）

2. **ダイジェスト指定で確実性UP**
   - タグの上書きの影響を受けない
   - 完全に同一のイメージを保証

3. **他の設定も同時変更可能**
   ```bash
   docker service update \
     --image swarm-web:v4.0 \
     --replicas 6 \
     --env-add NEW_VAR=value \
     test4-3
   ```

4. **PreviousSpecが不要**
   - どんな状況でも使用可能
   - 初回デプロイ後でもOK

#### デメリット ❌
1. **バージョンを手動で指定**
   - 人的ミスの可能性
   - 正確なバージョン番号を覚える必要

2. **イメージのみ変更**
   - 他の設定は現在の状態を維持
   - 完全な復元ではない

3. **更新扱いになる**
   - PreviousSpecが上書きされる
   - 再度rollbackすると、今回の変更が取り消される

### 使用ケース

- ✅ **2世代以上前に戻したい**（v5.0 → v3.0）
- ✅ **特定のハッシュ値のイメージに確実に戻したい**
- ✅ **PreviousSpecが存在しない**
- ✅ **ロールバックと同時に他の設定も変更したい**

---

## イメージダイジェスト（ハッシュ値）の使用

### ダイジェストとは

**イメージの内容から生成されるSHA256ハッシュ値**

```
swarm-web:v4.0  ← タグ（変更可能）
    ↓
swarm-web@sha256:abc123...  ← ダイジェスト（不変）
```

### タグ vs ダイジェスト

| 項目 | タグ | ダイジェスト |
|:---|:---|:---|
| 例 | `nginx:1.21` | `nginx@sha256:abc...` |
| 可変性 | 上書き可能 | 不変 |
| 人間可読性 | 高い | 低い |
| 確実性 | 低い | 高い |

### ダイジェストの取得方法

#### 方法1: docker inspect
```bash
$ docker inspect swarm-web:v4.0 --format '{{index .RepoDigests 0}}'
swarm-web@sha256:abc123...
```

#### 方法2: docker images
```bash
$ docker images --digests swarm-web
REPOSITORY   TAG    DIGEST          IMAGE ID     CREATED
swarm-web    v4.0   sha256:abc...   a6146d0c14   1 hour ago
swarm-web    v5.0   sha256:def...   fb7c3fbb8f   30 min ago
```

#### 方法3: docker pull
```bash
$ docker pull swarm-web:v4.0
v4.0: Pulling from swarm-web
Digest: sha256:abc123...
Status: Image is up to date
```

### ダイジェストを使ったロールバック

```bash
# 1. ダイジェスト確認
DIGEST=$(docker inspect swarm-web:v4.0 --format '{{index .RepoDigests 0}}')

# 2. ダイジェストで指定
docker service update --image ${DIGEST} test4-3
```

**メリット:**
- タグが上書きされても影響なし
- 完全に同一のイメージを保証
- 本番環境での推奨方法

---

## 実践的な使い分け

### パターン1: 直前の更新を取り消す（最も一般的）

**状況:** v5.0にしたけど問題があった

**推奨:** `docker service rollback` ✅

```bash
docker service rollback test4-3
```

**理由:**
- 最もシンプルで迅速
- 人的ミスがない
- 設定も含めて完全復元

---

### パターン2: 2世代以上前に戻す

**状況:** v5.0 → v4.0 → v3.0 とバージョンアップしたが、v2.0に戻したい

**推奨:** `docker service update --image` ✅

```bash
docker service update --image swarm-web:v2.0 test4-3
```

**理由:**
- rollbackは1世代前にしか戻れない
- 特定バージョンを明示的に指定

---

### パターン3: 確実に特定のビルドに戻す（本番環境）

**状況:** CI/CDでビルドされたイメージに確実に戻したい

**推奨:** ダイジェスト指定 ✅✅

```bash
# CI/CDで記録されたダイジェストを使用
docker service update \
  --image myregistry.com/app@sha256:abc123... \
  production-service
```

**理由:**
- タグの上書きの影響を受けない
- 監査証跡として明確
- 最も確実

---

### パターン4: ロールバックと同時に他の設定も変更

**状況:** v4.0に戻すと同時にレプリカ数も増やしたい

**推奨:** `docker service update` ✅

```bash
docker service update \
  --image swarm-web:v4.0 \
  --replicas 6 \
  --env-add OPTIMIZE=true \
  test4-3
```

**理由:**
- rollbackはイメージと設定の復元のみ
- updateなら追加の変更も可能

---

## 本番環境での推奨フロー

### 標準的なロールバック手順

```bash
# 1. 現在の状態確認
docker service ps <service-name>

# 2. ロールバック実行（推奨）
docker service rollback <service-name>

# 3. 状態確認
docker service ps <service-name>

# 4. 動作確認
curl http://<service-endpoint>
```

### ダイジェストを使った安全なデプロイフロー

```bash
# === デプロイ時 ===

# 1. イメージビルド
docker build -t myapp:v1.2.3 .

# 2. ダイジェスト記録
DIGEST=$(docker inspect myapp:v1.2.3 --format '{{index .RepoDigests 0}}')
echo "Deployed: ${DIGEST}" >> deployment-history.txt

# 3. ダイジェストでデプロイ
docker service update --image ${DIGEST} production-service

# === ロールバック時 ===

# deployment-history.txtから前バージョンのダイジェストを取得
PREV_DIGEST="myapp@sha256:xyz789..."

# ダイジェストでロールバック
docker service update --image ${PREV_DIGEST} production-service
```

---

## よくある質問

### Q1: rollbackを連続で実行するとどうなる？

```bash
# 1回目: v5.0 → v4.0
docker service rollback test4-3  # OK

# 2回目: v4.0 → v5.0（元に戻る）
docker service rollback test4-3  # v5.0に戻ってしまう
```

**注意:** rollbackは前後を入れ替えるだけ

### Q2: 複数のサービスを一括ロールバックできる？

```bash
# すべてのサービスをロールバック
for service in $(docker service ls -q); do
  docker service rollback ${service}
done

# 特定のサービス群をロールバック
for service in web api worker; do
  docker service rollback ${service}
done
```

### Q3: ロールバック中にさらに問題が発生したら？

```bash
# ロールバック自体を停止
docker service update --rollback-parallelism 0 <service-name>

# または特定バージョンに強制変更
docker service update --image <stable-version> <service-name>
```

---

## まとめ

### 一般的な使用頻度

| 方法 | 使用頻度 | 推奨度 |
|:---|:---:|:---:|
| `docker service rollback` | ★★★★★ | 最推奨 |
| `docker service update --image <tag>` | ★★★☆☆ | 条件付き |
| `docker service update --image @<digest>` | ★★★★☆ | 本番推奨 |

### 結論

**一般的には `docker service rollback` が推奨**

理由:
- ✅ 最もシンプルで安全
- ✅ 人的ミスが少ない
- ✅ 設定も含めて完全復元
- ✅ 緊急時に最速

**ただし、以下の場合は `update --image` を使用:**
- 2世代以上前に戻す必要がある
- ダイジェストで確実性を担保したい
- ロールバックと同時に他の設定も変更したい
- PreviousSpecが存在しない

**本番環境のベストプラクティス:**
```bash
# 通常のロールバック
docker service rollback <service-name>

# 重要なサービスのロールバック（ダイジェスト使用）
docker service update --image <registry>/<image>@sha256:<digest> <service-name>
```
