# AKQuant 修改任务总结 - CurrentOpen 执行模式

## 概述

本次修改为 AKQuant 量化回测框架添加了 `CurrentOpen` 执行模式，允许订单使用当前 Bar 的开盘价成交。

**修改日期**: 2026-07-03  
**修改目的**: 支持 `fill_policy={'price_basis': 'open', 'bar_offset': 0, 'temporal': 'same_cycle'}` 参数，使买入订单能够在策略信号发出的同一根 Bar 使用开盘价成交。

---

## 修改内容

### 1. Python 层修改

#### 1.1 strategy_trading_api.py
**文件路径**: `python/akquant/strategy_trading_api.py`  
**修改内容**: 移除对 `open` 的 `bar_offset` 限制

```python
# 修改前
if raw_basis in {"open", "ohlc4", "hl2"} and raw_offset != 1:
    raise ValueError(f"fill_policy({raw_basis}) requires bar_offset=1")

# 修改后
if raw_basis in {"ohlc4", "hl2"} and raw_offset != 1:
    raise ValueError(f"fill_policy({raw_basis}) requires bar_offset=1")
```

#### 1.2 backtest/engine.py
**文件路径**: `python/akquant/backtest/engine.py`  
**修改内容**: 
- 添加 `_RUNTIME_MODE_CURRENT_OPEN` 常量
- 修改 fill_policy 解析逻辑，支持 `open` + `bar_offset=0` 映射到 `CurrentOpen`
- 更新模式映射表和反向映射表

```python
# 添加常量
_RUNTIME_MODE_CURRENT_OPEN = getattr(_RUNTIME_EXECUTION_MODE, "CurrentOpen", "current_open")

# 修改解析逻辑
if raw_basis == "open":
    basis_mode = (
        _RUNTIME_MODE_CURRENT_OPEN
        if raw_offset == 0
        else _RUNTIME_MODE_NEXT_OPEN
    )
```

---

### 2. Rust 层修改

#### 2.1 src/model/types.rs
**文件路径**: `src/model/types.rs`  
**修改内容**: 添加 `CurrentOpen` 执行模式枚举值

```rust
pub enum ExecutionMode {
    CurrentClose,   // 当前Bar收盘价成交 (Cheat-on-Close)
    CurrentOpen,    // 当前Bar开盘价成交 (Pre-market order)
    NextOpen,       // 下一根Bar开盘价成交 (Real-world)
    NextClose,      // 下一根Bar收盘价成交
    NextAverage,    // 下一根Bar均价成交 (TWAP/VWAP 模拟)
    NextHighLowMid, // 下一根Bar最高价和最低价的中间价成交
}
```

#### 2.2 src/context.rs
**文件路径**: `src/context.rs`  
**修改内容**: 移除对 `PriceBasis::Open` 的 `bar_offset` 验证限制

```rust
// 修改前
match basis {
    PriceBasis::Open if bar_offset != 1 => {
        return Err(PyValueError::new_err(
            "fill_policy(open) requires bar_offset=1",
        ));
    }
    PriceBasis::Ohlc4 if bar_offset != 1 => {

// 修改后
match basis {
    PriceBasis::Ohlc4 if bar_offset != 1 => {
```

#### 2.3 src/engine/python.rs
**文件路径**: `src/engine/python.rs`  
**修改内容**: 移除对 `PriceBasis::Open` 的 `bar_offset` 验证限制

```rust
// 修改前
match basis {
    PriceBasis::Open | PriceBasis::Ohlc4 | PriceBasis::Hl2 if bar_offset != 1 => {
        return Err(PyValueError::new_err(
            "price_basis=open|ohlc4|hl2 requires bar_offset=1",
        ));
    }
    _ => {}
}

// 修改后
match basis {
    PriceBasis::Ohlc4 | PriceBasis::Hl2 if bar_offset != 1 => {
        return Err(PyValueError::new_err(
            "price_basis=ohlc4|hl2 requires bar_offset=1",
        ));
    }
    _ => {}
}
```

#### 2.4 src/pipeline/stages/shared.rs
**文件路径**: `src/pipeline/stages/shared.rs`  
**修改内容**: 调整 `should_run_phase_for_current_event` 函数，使 `CurrentOpen` 在 `PostStrategy` 阶段执行

#### 2.5 src/pipeline/stages/channel.rs
**文件路径**: `src/pipeline/stages/channel.rs`  
**修改内容**: 在处理完订单请求后立即处理事件队列，确保 `bar_offset=0` 的订单能被及时执行

---

### 3. 编译部署

```bash
# 编译
maturin build --release

# 替换旧的扩展文件
cp target/release/akquant.dll python/akquant/akquant.pyd
```

---

## 使用方法

在策略中使用以下 `fill_policy` 参数即可实现当日开盘价成交：

```python
buy_fill_policy = {
    'price_basis': 'open',
    'bar_offset': 0,
    'temporal': 'same_cycle'
}

self.order_target_percent(symbol, 0.95, fill_policy=buy_fill_policy)
```

---

## 测试验证

**测试脚本**: `test_current_open.py`  
**测试结果**:
- ✅ 买入订单在第一根 Bar 以 100.0（当前开盘价）成交
- ✅ 卖出订单在第二根 Bar 以 103.0（收盘价）成交

---

## 注意事项

1. **akquant 升级后需重新应用此修改**: 当 AKQuant 官方发布新版本时，本修改会被覆盖，需要重新应用。
2. **编译环境**: 需要 Rust 工具链和 maturin 构建工具。
3. **Python 版本**: 本修改基于 Python 3.10+ 开发和测试。

---

## 文件变更清单

| 文件路径 | 修改类型 | 说明 |
|---------|---------|------|
| `python/akquant/strategy_trading_api.py` | 修改 | 移除 open 的 bar_offset 限制 |
| `python/akquant/backtest/engine.py` | 修改 | 添加 CurrentOpen 支持 |
| `src/model/types.rs` | 修改 | 添加 CurrentOpen 枚举值 |
| `src/context.rs` | 修改 | 移除 Open 的验证限制 |
| `src/engine/python.rs` | 修改 | 移除 Open 的验证限制 |
| `src/pipeline/stages/shared.rs` | 修改 | 调整执行阶段逻辑 |
| `src/pipeline/stages/channel.rs` | 修改 | 优化事件处理循环 |
| `python/akquant/akquant.pyd` | 替换 | 新编译的扩展文件 |
| `test_current_open.py` | 新建 | 测试脚本 |
