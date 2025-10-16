# Docker Swarm タスク配置パターン

## 1. 配置制約（Placement Constraints）

### ノードのロール指定
```bash
# マネージャーノードのみに配置
docker service create --constraint 'node.role==manager' nginx

# ワーカーノードのみに配置
docker service create --constraint 'node.role==worker' nginx
```

### ノードのラベル指定
```bash
# ノードにラベル追加
docker node update --label-add env=production worker1
docker node update --label-add env=staging docker-desktop

# 特定ラベルのノードに配置
docker service create --constraint 'node.labels.env==production' nginx
```

### ホスト名指定
```bash
# 特定ノードに配置
docker service create --constraint 'node.hostname==worker1' nginx
```

## 2. 配置優先度（Placement Preferences）

### ノード分散の優先
```bash
# ラベルごとに均等分散（例：データセンター間分散）
docker service create \
  --placement-pref 'spread=node.labels.datacenter' \
  nginx
```

## 3. リソース制限

### CPUとメモリの予約・制限
```bash
docker service create \
  --reserve-cpu 0.5 \
  --reserve-memory 512M \
  --limit-cpu 1.0 \
  --limit-memory 1G \
  nginx
```

## 4. グローバルモード vs レプリケートモード

### レプリケートモード（デフォルト）
- 指定した数のレプリカを最適なノードに配置
```bash
docker service create --replicas 3 nginx
```

### グローバルモード
- 全ノードに1つずつ配置（監視エージェントなどに最適）
```bash
docker service create --mode global nginx
```

## 5. 配置アルゴリズム

Docker Swarmの配置決定要素（優先順位順）：

1. **配置制約** - 必須条件
2. **リソース予約** - CPU/メモリの空き確認
3. **Spread戦略** - ノード間で均等分散
4. **タスク失敗履歴** - 失敗が多いノードは避ける

## 6. 実践例

### データベース専用ノード
```bash
# DB用ノードにラベル追加
docker node update --label-add type=database worker1

# DBサービスをDB専用ノードに配置
docker service create \
  --constraint 'node.labels.type==database' \
  --replicas 1 \
  postgres
```

### 地理的分散
```bash
# 各ノードにリージョン設定
docker node update --label-add region=us-east worker1
docker node update --label-add region=us-west worker2

# リージョンごとに分散
docker service create \
  --replicas 6 \
  --placement-pref 'spread=node.labels.region' \
  nginx
```

### 高優先度サービス
```bash
# マネージャーノードに配置（より安定）
docker service create \
  --constraint 'node.role==manager' \
  --replicas 1 \
  critical-app
```

## 7. タスク配置の実験結果

### 実験: 3ノード、4タスクの配置パターン

**クラスタ構成:**
- docker-desktop (マネージャー)
- worker1 (ワーカー)
- worker2 (ワーカー)

**テストコマンド:**
```bash
docker service create --name test4 --replicas 4 swarm-web:latest
```

**結果（3回実施）:**

| テスト | docker-desktop | worker1 | worker2 | パターン |
|:---:|:---:|:---:|:---:|:---|
| 1回目 | 1 | 2 | 1 | 2,1,1 |
| 2回目 | 1 | 2 | 1 | 2,1,1 |
| 3回目 | 1 | 2 | 1 | 2,1,1 |

**配置詳細（3回目の例）:**
```
test4.1 → worker1
test4.2 → worker1
test4.3 → worker2
test4.4 → docker-desktop
```

### 分散配置の特徴

#### 均等分散の限界
- **4タスク ÷ 3ノード = 1.33...** （割り切れない）
- 完全な均等配置は数学的に不可能
- Swarmは「できるだけ均等」を目指す

#### Spread戦略の挙動
1. タスクを順次ノードに配置
2. ノードの負荷、リソース、既存タスク数を考慮
3. 配置先ノードの選択は確定的ではない（状況依存）

#### 可能な配置パターン
```
3ノード、4タスクの場合:
- パターンA: 2, 1, 1
- パターンB: 1, 2, 1
- パターンC: 1, 1, 2
```

どのパターンになるかは以下の要因で決まる:
- ノードの起動順序
- 既存のタスク数
- リソース使用状況
- タスクのスケジューリングタイミング

### より均等な配置を実現する方法

#### Placement Preferencesを使用
```bash
docker service create \
  --name test4-balanced \
  --replicas 4 \
  --placement-pref 'spread=node.id' \
  swarm-web:latest
```

#### 複数の配置基準を組み合わせ
```bash
# ラベルで地理的に分散
docker node update --label-add zone=east docker-desktop
docker node update --label-add zone=west worker1
docker node update --label-add zone=west worker2

docker service create \
  --name geo-balanced \
  --replicas 4 \
  --placement-pref 'spread=node.labels.zone' \
  nginx
```

### 配置パターンの検証方法

```bash
# ノード別タスク数確認
docker service ps <service-name> --filter "desired-state=running" \
  --format "{{.Node}}" | sort | uniq -c

# 期待出力:
#       1 docker-desktop
#       2 worker1
#       1 worker2
```

### 実践的な推奨事項

#### レプリカ数とノード数の関係

| ノード数 | 推奨レプリカ数 | 理由 |
|:---:|:---|:---|
| 3 | 3, 6, 9... | 均等分散可能（3の倍数） |
| 3 | 4, 5, 7... | 均等分散不可（許容する場合） |
| 5 | 5, 10, 15... | 均等分散可能（5の倍数） |

#### 本番環境での考慮事項
1. **ノード数 = レプリカ数の倍数** にすることで完全均等配置
2. 割り切れない場合は **1台の差は許容範囲**
3. 特定ノードへの偏りを避けるため **placement-pref** の使用を検討
4. ノードのリソース量が異なる場合は **リソース予約** で調整
