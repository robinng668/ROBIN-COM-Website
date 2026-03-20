# ROBIN.COM 工作流系统 v1.0

## 最高目标
**让ROBIN.COM成为顶级量化交易公司**

---

## 一、核心工作流清单

### 1. 资讯收集工作流 📰
```
触发: 每日 7:00, 15:00
技能: Tavily Search → 整理 → 飞书发送
状态: ✅ 已实现
```

### 2. 网站更新工作流 🌐
```
触发: 每2小时 + 手动
技能: 数据获取 → HTML更新 → 部署
状态: ⚠️ 需完善
```

### 3. 盯盘监控工作流 👁️
```
触发: 实时/定时
技能: Futu行情 → 信号检测 → 告警
状态: ⏳ 待开发
```

### 4. 交易执行工作流 📈
```
触发: 信号确认后
技能: 行情判断 → 订单执行 → 记录
状态: ⏳ 待开发
```

### 5. 风控监控工作流 🛡️
```
触发: 实时监控
技能: 持仓检查 → 止损检测 → 告警
状态: ⏳ 待开发
```

### 6. 回测验证工作流 🔬
```
触发: 新策略上线前
技能: 历史数据 → 回测 → 报告
状态: ⏳ 待开发
```

### 7. 复盘分析工作流 📊
```
触发: 每日 21:00
技能: 数据汇总 → 收益分析 → 改进建议
状态: ⏳ 待开发
```

---

## 二、工作流执行脚本

### 2.1 网站更新脚本
```bash
# /scripts/update_website.sh
#!/bin/bash
cd /mnt/d/Aproject/Xfile/workbench

# 1. 获取最新行情
python3 scripts/get_quotes.py

# 2. 更新网站
python3 scripts/update_index.py

# 3. 部署
cp www/index.html /var/www/html/
```

### 2.2 盯盘监控脚本
```bash
# /scripts/market_monitor.sh
#!/bin/bash

# 检查Futu连接
python3 scripts/check_futu_opend.py

# 获取持仓报价
python3 scripts/get_positions.py

# 检测信号
python3 scripts/signal_detection.py

# 发送告警（如有）
python3 scripts/send_alert.py
```

---

## 三、每日任务时间表

| 时间 | 工作流 | Agent |
|------|--------|-------|
| 07:00 | 资讯早报 | 发哥 |
| 12:00 | 午间动态 | 发哥 |
| 15:00 | 资讯TOP10 | 发哥 |
| 16:00 | 网站更新 | 卡特 |
| 17:00 | 进度检查 | 卡特 |
| 18:00 | 汇总报告 | 卡特 |
| 19:00 | 投研分析 | 星星 |
| 21:00 | 复盘分析 | 星星 |
| 22:00 | 风控检查 | 卡特 |
| 每2h | 网站行情 | 发哥 |

---

## 四、自动化部署

### Cron 配置
```cron
# ROBIN.COM 工作流定时任务
0 7 * * * /mnt/d/Aproject/Xfile/workbench/scripts/workflow_daily.sh
0 15 * * * /mnt/d/Aproject/Xfile/workbench/scripts/news_top10.sh
0 */2 * * * /mnt/d/Aproject/Xfile/workbench/scripts/update_website.sh
0 21 * * * /mnt/d/Aproject/Xfile/workbench/scripts/review.sh
```

---

## 五、待开发脚本清单

| 脚本 | 功能 | 优先级 |
|------|------|--------|
| get_quotes.py | 获取实时行情 | P0 |
| signal_detection.py | 信号检测 | P0 |
| update_index.py | 更新网站HTML | P1 |
| send_alert.py | 发送告警 | P1 |
| position_check.py | 持仓检查 | P1 |
| stop_loss.py | 止损检测 | P2 |
| backtest.py | 回测引擎 | P2 |

---

_目标：实现全流程自动化，7x24小时无人值守_
