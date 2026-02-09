# TOXICTIDE

**AI 驱动的量化交易系统** - 具备盘口/成交量异常检测和智能风控能力

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 🎯 核心价值主张

**人类意图 → 策略路由 → 盘口/成交量环境感知 → 风控守护 → 可审计的真实执行**

TOXICTIDE 是一个生产级的 AI 交易系统，专为 **Dexless AI Trading Hackathon** 设计。系统通过多层异常检测和智能风控，确保在复杂市场环境下的安全执行。

### ⚡ 核心特性

- **🔍 多维异常检测** - OAD（盘口）+ VAD（成交量）+ Stress Index（综合压力）
- **🛡️ 7 层风控守护** - 数据质量、日亏熔断、冷却期、仓位上限、Impact/Toxic 检查
- **🎯 市场状态感知** - 三维状态分类（Price × Vol × Flow）
- **📊 Impact-aware 执行** - 高冲击自动分片，降低市场冲击
- **📝 完整审计追踪** - JSONL 格式记录每次决策，可回放复现
- **🤖 可解释性** - 每个决策都有人类可读的解释

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    TOXICTIDE 交易系统                         │
└─────────────────────────────────────────────────────────────┘

          ┌──────────────┐
          │  CLI / UI    │  ← 用户交互
          └──────┬───────┘
                 │
          ┌──────▼───────────────────────┐
          │    Orchestrator (主循环)      │
          │    1 秒 Tick                  │
          └──────┬───────────────────────┘
                 │
    ┌────────────┴────────────┐
    │                         │
┌───▼─────┐           ┌───────▼─────┐
│数据采集  │           │  特征计算    │
│Collector│           │   Engine     │
└───┬─────┘           └───────┬─────┘
    │                         │
    │      ┌──────────────────┴─────────┐
    │      │                            │
    │  ┌───▼────┐  ┌─────────┐  ┌──────▼────┐
    │  │  OAD   │  │   VAD   │  │  Stress   │
    │  │盘口异常│  │成交量异常│  │  Index    │
    │  └───┬────┘  └────┬────┘  └──────┬────┘
    │      └────────┬───┴──────────────┘
    │               │
    │        ┌──────▼─────────┐
    │        │  Regime        │  ← 市场状态分类
    │        │  Classifier    │
    │        └──────┬─────────┘
    │               │
    │        ┌──────▼─────────┐
    │        │  Signal        │  ← 策略信号生成
    │        │  Engine        │
    │        └──────┬─────────┘
    │               │
    │        ┌──────▼─────────┐
    │        │  Risk          │  ← 7 层风控检查
    │        │  Guardian      │
    │        └──────┬─────────┘
    │               │
    │        ┌──────▼─────────┐
    │        │  Execution     │  ← Impact-aware
    │        │  Planner       │     Slicing
    │        └──────┬─────────┘
    │               │
    │        ┌──────▼─────────┐
    │        │  Adapter       │  ← Paper / Real
    │        │  (执行)        │
    │        └──────┬─────────┘
    │               │
    │        ┌──────▼─────────┐
    │        │  Ledger        │  ← 审计日志
    │        │  (审计)        │
    │        └────────────────┘
    │
    └──────────────┘  Event Bus (事件总线)
```

---

## 🚀 快速开始

### 1. 安装依赖

```bash
# 克隆仓库
git clone https://github.com/yourusername/toxictide.git
cd toxictide

# 安装依赖
pip install -r requirements.txt
```

**核心依赖：**
- Python 3.10+
- pydantic >= 2.0
- numpy
- structlog
- pyyaml

### 2. 配置系统

```bash
# 复制配置模板
cp default_config.yaml config.yaml

# 编辑配置（可选）
# vim config.yaml
```

### 3. 运行系统

```bash
# 启动系统
python main.py
```

**启动后界面：**
```
============================================================
TOXICTIDE 交易系统已启动
============================================================

可用命令:
  /status  - 显示系统状态
  /pause   - 暂停交易
  /resume  - 恢复交易
  /why     - 显示最后决策解释
  /quit    - 退出系统

输入命令并按回车...
============================================================

>
```

---

## 📋 CLI 命令说明

### `/status` - 系统状态

显示当前系统运行状态：

```
============================================================
📊 系统状态
============================================================
状态: 运行中
市场压力: 🟢 OK
市场状态: RANGE / CALM
价格: $2000.50
价差: 5.25 bps
============================================================
```

### `/pause` / `/resume` - 暂停/恢复

暂停或恢复交易执行（数据采集和监控继续）

### `/why` - 决策解释

显示最后一次风控决策的详细解释：

```
============================================================
🔍 最后决策
============================================================
⚠️  交易允许，但已调整仓位：
  - 冲击成本偏高（12.00 bps > 入场上限 10.00 bps），已减仓

最终仓位: $500.00
最大滑点: 7.50 bps
============================================================
```

### `/quit` - 退出系统

优雅关闭系统，保存所有日志

---

## ⚙️ 配置参数说明

### 核心配置（`default_config.yaml`）

```yaml
# 异常检测阈值
oad:
  z_warn: 4.0      # WARN 级别（MAD z-score）
  z_danger: 6.0    # DANGER 级别

vad:
  z_warn: 4.0
  z_danger: 6.0
  toxic_warn: 0.6   # 毒性流 WARN 阈值
  toxic_danger: 0.75

# 风控参数
risk:
  max_daily_loss_pct: 1.0          # 日亏上限 1%
  max_position_notional: 3000      # 最大仓位 $3000
  impact_hard_cap_bps: 20.0        # 冲击硬上限 20 bps
  impact_entry_cap_bps: 10.0       # 入场上限 10 bps

# 执行参数
execution:
  mode: paper                       # paper | real
  slicing_threshold_bps: 10.0      # 分片阈值
```

---

## 📊 功能特性详解

### 1. 异常检测系统

#### **OAD (Orderbook Anomaly Detector)** - 盘口异常检测
- ✅ Spread 异常 - 价差突然扩大
- ✅ Impact 异常 - 价格冲击过高
- ✅ Liquidity Gap - 流动性断层
- ✅ Message Rate 异常 - 订单簿更新频率异常

#### **VAD (Volume Anomaly Detector)** - 成交量异常检测
- ✅ Volume Burst - 成交量爆发
- ✅ Volume Drought - 成交量干涸
- ✅ Whale Trade - 鲸鱼交易
- ✅ Toxic Flow - 毒性流（买卖严重不平衡）

#### **Stress Index** - 市场压力综合指数
- 综合 OAD + VAD 结果
- 输出 OK / WARN / DANGER 三级告警

---

### 2. 风控守护系统（7 层检查）

#### **优先级 1: 数据质量** 🔴
- 数据过期（> 10 秒）→ **DENY**
- Orderbook 不一致（spread <= 0）→ **DENY**

#### **优先级 2: 日亏熔断** 🔥
- 日盈亏 < -1% → **DENY**（当日禁止新开仓）

#### **优先级 3: 冷却期** ❄️
- 连续亏损触发冷却 → **DENY**

#### **优先级 4: 仓位上限** 📏
- 仓位 >= $3000 → **DENY**

#### **优先级 5: Impact/Toxic** 💥
- Impact > 20 bps → **DENY**
- Toxic >= 0.75 → **DENY**
- Impact > 10 bps → **ALLOW_WITH_REDUCTIONS**（减仓）

#### **优先级 6: Market Stress** ⚠️
- Stress = DANGER → **DENY**
- Stress = WARN → **ALLOW_WITH_REDUCTIONS**

#### **优先级 7: 交易频率** ⏱️
- 最近 1 小时 >= 6 笔 → **DENY**

---

### 3. 执行层（Impact-aware Slicing）

#### **模式 1: High Impact → Slicing**
```
Impact >= 10 bps → 分 5 片，间隔 10 秒
目的：降低市场冲击
```

#### **模式 2: High Toxic → Taker Only**
```
Toxic >= 0.6 → 使用 market 单快速成交
目的：避免在毒性流环境中挂单
```

#### **模式 3: Normal → Maker**
```
正常市场 → 使用 limit 单
目的：赚取 rebate，降低成本
```

---

### 4. 审计与可解释性

#### **完整审计日志**
- 格式：JSONL（每行一个 JSON）
- 位置：`logs/session_YYYYMMDD.jsonl`
- 内容：policy, features, oad, vad, stress, regime, signal, risk, plan, fills, explain

#### **可解释性**
每个决策都生成人类可读的解释：

```
❌ 交易被拒绝，原因：
  - 日亏超限（当前 -1.50% < 阈值 -1.00%）
  - 冷却期激活（剩余 120 秒）
```

---

## 🧪 测试

```bash
# 运行所有测试
pytest tests/

# 单元测试
pytest tests/unit/

# 集成测试
pytest tests/integration/

# 覆盖率报告
pytest --cov=toxictide tests/
```

---

## 📁 项目结构

```
toxictide/
├── toxictide/              # 核心代码
│   ├── market/            # 数据层
│   ├── features/          # 特征引擎
│   ├── detectors/         # 异常检测
│   ├── regime/            # 市场状态
│   ├── strategy/          # 策略信号
│   ├── risk/              # 风控守护
│   ├── execution/         # 执行层
│   ├── ledger/            # 审计日志
│   ├── explain/           # 可解释性
│   ├── ui/                # 用户界面
│   ├── app.py             # 主循环
│   ├── bus.py             # 事件总线
│   ├── models.py          # 数据模型
│   └── config_loader.py   # 配置加载
├── tests/                 # 测试
│   ├── unit/              # 单元测试
│   └── integration/       # 集成测试
├── logs/                  # 审计日志
├── default_config.yaml    # 默认配置
├── main.py                # 主入口
├── README.md              # 本文档
└── requirements.txt       # 依赖
```

---

## 🔧 开发指南

### 添加新策略

1. 在 `toxictide/strategy/signals.py` 中添加策略逻辑
2. 在 `default_config.yaml` 的 `allowed_strategies` 中启用
3. 编写单元测试

### 添加新的异常检测器

1. 在 `toxictide/detectors/` 创建新文件
2. 继承 `RollingMAD` 使用稳健统计
3. 在 `Orchestrator` 中集成
4. 编写测试

### 自定义风控规则

修改 `toxictide/risk/guardian.py` 中的 `assess()` 方法

---

## 📖 文档

- **[CLAUDE.md](CLAUDE.md)** - Claude Code 开发指南
- **[PRD](docs/TOXICTIDE_PRD.md)** - 产品需求文档
- **[Implementation Guide](docs/TOXICTIDE_IMPLEMENTATION_PRD.md)** - 实现指南

---

## 🤝 贡献指南

我们欢迎贡献！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支（`git checkout -b feature/AmazingFeature`）
3. 提交更改（`git commit -m 'Add some AmazingFeature'`）
4. 推送到分支（`git push origin feature/AmazingFeature`）
5. 开启 Pull Request

---

## 📝 License

本项目采用 MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 🙏 致谢

- **Dexless AI Trading Hackathon** - 项目灵感来源
- **Claude Code** - 开发工具支持
- **社区贡献者** - 感谢所有贡献者

---

## 📧 联系方式

- **项目主页**: [https://github.com/yourusername/toxictide](https://github.com/yourusername/toxictide)
- **问题反馈**: [Issues](https://github.com/yourusername/toxictide/issues)

---

**Built with ❤️ using Claude Code**
