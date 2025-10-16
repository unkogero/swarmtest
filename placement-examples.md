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
