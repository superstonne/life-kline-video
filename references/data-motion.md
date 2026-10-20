# 数据与运动契约

根字段：title、subject、initial_value、seed、events。默认数值是叙事指数，没有金融意义。

人物有可靠出生日期时增加 `birth_date: YYYY-MM-DD`；事件填 `event_date: YYYY-MM-DD`。编译器按事件当天计算周岁，输出 `age` 与根 `age_range`；渲染器把 `age` 追加到 time_label。开场或回看需要展示年龄跨度时设 `show_age_range: true`。无确切日期时不要编造日月来计算单一年龄。

| 事件字段 | 含义 |
| --- | --- |
| id | 唯一字符串，供标注绑定 |
| start / end | 视频秒数，连续且从 0 开始 |
| mode | trade / halt / overview |
| target | trade 终点；halt/overview 须等于前一节点终值 |
| candles | trade 蜡烛数量，默认 24；非交易段 0 |
| volatility | 0–0.5，局部波动强度，默认 0.025 |
| shape | 可选 `organic`，用相关的确定性波动与温和曲率代替独立噪声；默认保持原有线性数据模式 |
| headline / emphasis | 一到两行标题／其中要着色的字词数组 |
| time_label | 历史年份年龄，独立于视频秒数 |
| marker | 简短事件标记或空字符串 |
| source | 真实事件出处；示例注明虚构 |

历史时间无需等比例映射到视频。数年可压缩成短段，重大转折可以展开。不能伪造每根蜡烛的真实日期。

完整人物版增加根字段 `axis_start` / `axis_end`（历史年份小数）、`global_view`（总曲线数值范围）；事件以 `axis_year` 记录其在历史轴上的终点。编译器保留 `axis_from` / `axis_to`，给蜡烛写 `year0` / `year1`，给标记写 `year`。日期只有年度精度时，小数位置只是年代定位，不能反过来当精确日期。`age_label` 可保存可靠的已知年龄或范围；有精确日期时仍优先计算周岁。

局部可以平滑改变历史窗口宽度，但不能修改曲线数值、总轴上的事件间距或历史数据。需要保持烛图风格时，优先按固定历史时间桶聚合 OHLC：开盘为首根开盘，收盘为末根收盘，高低点取极值；跨等待区间分桶，当前桶只取已经出现的蜡烛。两级时间分辨率可以交叉淡化，以免变焦时闪烁。连线可作为另一种明确的设计选择，但不能成为掩盖粗蜡烛堆叠的默认修补，也不能另造更平滑的数据。

脚本输出每根蜡烛的 t0/t1、OHLC、volume 与 event_id；标题从事件开始生效，marker 在事件结束时锚定终点。中途标记需要拆为两个节点，不让终点标记提前出现。停牌章由当前事件的 mode 驱动，不用结束标记代替。

## 部分蜡烛显现

```javascript
const p = Math.max(0, Math.min(1, (t - c.t0) / (c.t1 - c.t0)));
if (t >= c.t0) {
  const closeNow = c.open + (c.close - c.open) * p;
  const highNow = Math.max(c.open, closeNow) +
    (c.high - Math.max(c.open, c.close)) * p;
  const lowNow = Math.min(c.open, closeNow) -
    (Math.min(c.open, c.close) - c.low) * p;
  // draw body(open, closeNow), wick(lowNow, highNow), volume * p
}
```

颜色按最终 close >= open 决定，避免中途闪色。十字星至少一个输出像素；影线和量柱用同一横坐标。蜡烛结束前指数用 closeNow，停牌和回看用上一终值，不在事件开始直接跳到 target。

## 视窗与锚点

```text
x = chartLeft + (candle.t0 - viewTimeMin) / viewTimeSpan * chartWidth
y = chartBottom - (price - viewPriceMin) / viewPriceSpan * chartHeight
```

一段内统一尺度，不为每根新蜡烛重新 fit 全图。尺度在节点边界或过渡段内插；避免尺度提前泄露未画出的极端值。

回看沿用全部历史 OHLC 与标记，只插值改变视窗 min/span。停牌占据其历史时间间隔，水平虚线跨过空白；延长视频停留不额外拉长全景中的历史距离。复牌从上一收盘价继续；回看不新增蜡烛。

文字与印章锚定图表坐标，再偏移像素避让。低谷标注在低点下侧、高点标注在上侧，检查与成交量和标题不碰撞。

编译器验证区间、正数、OHLC 和停牌约束；视觉另验数值一致、停牌留白、随机定位稳定、回看数据一致。编译通过不等于成片验收。
