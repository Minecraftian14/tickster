
  
**NSE stock prediction: complete data specification**

For NSE stocks traded on a daily-to-weekly frequency, I would build a swing-trading prediction dataset with daily features, event-driven updates, and predictions over the next 1, 3 and 5 trading sessions.

The objective is to predict stock direction, expected return, downside risk and relative performance—not just the next closing price.

Use NSE's official [equity reports and bhavcopy data](https://www.nseindia.com/all-reports?utm_source=chatgpt.com) as a core source for daily prices, traded quantities, deliverable quantities and related market data. For company events, use [NSE corporate filings](https://www.nseindia.com/companies-listing/corporate-filings-application?utm_source=chatgpt.com) and [shareholding patterns](https://www.nseindia.com/companies-listing/corporate-filings-shareholding-pattern?utm_source=chatgpt.com).

  

NSE India

+2

  

**1. Master list of features to collect**

The priority labels below indicate implementation order, not proven predictive strength for every stock.

  

A. Price history and momentum

P0

Raw data: daily OHLC, adjusted close, volume and trading calendar.

- Returns: 1, 2, 3, 5, 10, 20, 60 and 120 sessions.  
      
    
- SMA/EMA: 5, 10, 20, 50 and 100 sessions.  
      
    
- Distance from SMA20, SMA50 and SMA100.  
      
    
- RSI(7), RSI(14), MACD(12,26,9).  
      
    
- ADX(14), moving-average slopes and trend persistence.  
      
    
- Distance from 20-, 60- and 252-session highs/lows.  
      
    
- Overnight gap, intraday return and close location within the daily range.  
      
    

  

  

B. Volume, delivery and liquidity

P0

Raw data: traded volume, turnover, number of trades and deliverable quantity where available.

- Relative volume versus the previous 20 sessions.  
      
    
- Volume z-score over 20 and 60 sessions.  
      
    
- Delivery percentage and its 5-/20-session changes.  
      
    
- Traded value in INR and average daily traded value over 20 sessions.  
      
    
- Number of trades and average trade value, where available.  
      
    
- Price change × relative volume interaction.  
      
    
- Turnover acceleration and rolling liquidity percentile.  
      
    
- Bid–ask spread and order-book depth, if timestamped historical data is available.  
      
    

  

  

C. Volatility and downside risk

P0

- ATR(14) and ATR as a percentage of price.  
      
    
- Realized volatility over 5, 10, 20 and 60 sessions.  
      
    
- High-low range and intraday volatility.  
      
    
- Overnight gap volatility.  
      
    
- Rolling maximum drawdown over 20 and 60 sessions.  
      
    
- Downside volatility, downside beta and tail-loss indicators.  
      
    
- Current volatility percentile versus the stock's own history.  
      
    

  

  

D. Market and sector context

P0

- NIFTY 50 and relevant sector-index returns over 1, 5, 20 and 60 sessions.  
      
    
- Stock excess return against both its sector and benchmark.  
      
    
- Rolling beta and correlation over 20 and 60 sessions.  
      
    
- Advance/decline breadth and percentage of sector constituents above their 20-/50-day averages.  
      
    
- India VIX level, change and percentile.  
      
    
- USD/INR, crude oil, bond yields and relevant commodity returns.  
      
    
- Market regime: uptrend, downtrend, high volatility or low volatility.  
      
    

  

  

E. Company fundamentals and expectations

P1

- Revenue, EBITDA, EBIT, net profit and EPS growth.  
      
    
- Operating and net profit margins.  
      
    
- ROE, ROIC, debt/equity, net debt/EBITDA and interest coverage.  
      
    
- Operating cash flow, free cash flow and working-capital trends.  
      
    
- P/E, P/B, EV/EBITDA and valuation versus sector peers.  
      
    
- Quarterly earnings surprise versus pre-announcement consensus.  
      
    
- Analyst earnings-estimate revisions, if historical data is available.  
      
    
- Financial results publication timestamp and age of the latest available report.  
      
    

  

  

F. News and corporate events

P1

- Results, guidance, order wins, acquisitions, litigation and regulatory announcements.  
      
    
- Announcement time, event category, source and novelty.  
      
    
- Sentiment and event materiality scores.  
      
    
- Earnings surprise and guidance change versus expectations.  
      
    
- Days until results, board meetings and known corporate events.  
      
    
- Corporate actions, including splits, bonuses, dividends and rights issues.  
      
    

  

  

G. Ownership and derivatives

P1/P2

- FII/DII flows at market level; stock-level institutional holdings when disclosed.  
      
    
- Promoter holding changes, promoter pledging and public-float estimates.  
      
    
- Futures open interest, price change and OI change for eligible stocks.  
      
    
- Futures basis, rollover percentage and rollover cost.  
      
    
- Put-call ratios, options implied volatility and changes in open interest.  
      
    
- Days to expiry and proximity to major derivative strikes.  
      
    

**2. Exact derived features the model should calculate**

Do not feed only raw indicators into the model. Calculate normalized and interaction features so it can distinguish ordinary activity from unusual activity.

|   |   |   |
|---|---|---|
|**Feature name**|**Definition**|**Why it matters**|
|return_5d|\(C_t/C_{t-5}-1\)|Recent momentum|
|relative_strength_5d|Stock 5-day return minus sector 5-day return|Stock-specific outperformance|
|relative_volume_20d|Today's volume / trailing 20-session average volume|Unusual participation|
|delivery_pct|Deliverable quantity / traded quantity × 100|Delivery-related trading activity|
|delivery_change_5d|Change in delivery percentage over 5 sessions|Changes in delivery activity|
|close_location|\((C-L)/(H-L)\)|Whether the close was near the high or low|
|atr_pct|ATR(14) / close × 100|Typical price movement relative to price|
|volatility_ratio|5-day realized volatility / 20-day realized volatility|Short-term volatility expansion|
|ma_distance_20d|Close / SMA20 − 1|Price extension relative to trend|
|breakout_20d|Close relative to the previous 20-session high|Breakout detection without look-ahead|
|beta_60d|Rolling covariance with benchmark / benchmark variance|Market sensitivity|
|earnings_surprise|Actual result minus consensus, scaled appropriately|Difference from expectations|
|event_recency_hours|Time elapsed since an eligible event became public|Event-driven repricing|
|futures_oi_change|Change in futures open interest|Changes in derivatives positioning|

Use adjusted price series consistently for return calculations and appropriate corporate-action handling. For close_location, explicitly handle zero-range sessions. For earnings surprises, use comparable units and pre-event consensus rather than an arbitrary fixed scale.

Delivery percentage is not proof of accumulation: it does not identify the beneficial owner or establish whether a trade reflects bullish intent.

**3. Prediction targets and labels**

Create a separate target for each forecast horizon. For daily-to-weekly trading, the following is a reasonable initial setup.

Target A — Next-session return

Forecast the next trading session's return.

1 day

  

Target B — Short swing return

Forecast the return across the next three trading sessions.

3 days

  

Target C — Weekly return

Forecast the return across the next five trading sessions.

5 days

  

Target D — Benchmark-relative direction

Predict whether the stock will outperform its sector or NIFTY benchmark over the same horizon.

1/3/5 days

  

Target E — Downside risk

Estimate the probability of a material decline, future volatility and maximum adverse excursion.

1/3/5 days

Define a consistent prediction timestamp. For example, if features are computed after the market closes on day \(t\), a next-session open-to-close return is a different target from close-to-close return:

\[ R_{t,1}=\frac{C_{t+1}}{C_t}-1 \]

This is a close-to-close target. If the intended strategy enters at the next opening price, label returns from that opening price instead and include realistic execution costs.

For classification, avoid labeling every tiny positive return as a meaningful bullish signal. Define a neutral band using a volatility-scaled threshold and transaction costs, and evaluate whether that improves trading decisions.

**4. Data sources and collection priorities**

|   |   |
|---|---|
|**Data source**|**What to extract**|
|[NSE All Reports](https://www.nseindia.com/all-reports?utm_source=chatgpt.com)|Daily bhavcopy, OHLC, volume, deliverable quantities and relevant security data|
|[NSE Corporate Filings](https://www.nseindia.com/companies-listing/corporate-filings-application?utm_source=chatgpt.com)|Financial results, announcements, board meetings, corporate actions and shareholding|
|[NSE Shareholding Patterns](https://www.nseindia.com/companies-listing/corporate-filings-shareholding-pattern?utm_source=chatgpt.com)|Promoter and public shareholding disclosures|
|NSE index and volatility data|NIFTY, sector indices, India VIX and benchmark history|
|Historical financial-data provider|Quarterly fundamentals, valuation history and analyst estimates|
|Historical F&O data provider|Futures price, open interest, rollover and options metrics|
|News provider or announcement parser|Timestamped news, event classification and sentiment|

NSE provides official end-of-day and historical order/trade data products, although some historical and higher-granularity datasets require paid access.

  

NSE India

+1

  

For an initial build, start with freely accessible daily data where available and verify the historical coverage and licensing terms. Do not assume a current API endpoint provides complete historical data or permission for unrestricted commercial redistribution.

**5. Recommended dataset architecture**

Use separate tables rather than one enormous denormalized file.

daily_market_features

One row per symbol per trading session. OHLCV, returns, technical indicators, volatility, liquidity and benchmark-relative features.

  

fundamentals_asof

Company financials and valuation metrics, versioned by publication time and reporting period.

  

events

Announcements, news, sentiment, materiality, source reliability and event timestamps.

  

training_examples

Point-in-time feature snapshots joined to forward-return labels for the 1-, 3- and 5-session horizons.

Each observation should have a stable symbol identifier, trading-session date, exchange, data-source identifier and availability timestamp. Preserve raw data separately from engineered features so calculations can be reproduced and audited.

**6. What to implement first**

1. Phase 1 — Daily market data: OHLCV, delivery percentage, returns, moving averages, momentum, volatility and relative strength.  
      
    
2. Phase 2 — Market regime: NIFTY and sector returns, India VIX, market breadth and benchmark beta.  
      
    
3. Phase 3 — Event enrichment: Earnings releases, corporate announcements, news and event-surprise features with strict publication-time controls.  
      
    
4. Phase 4 — Fundamentals and positioning: Quarterly financials, valuations, shareholding changes and F&O features.  
      
    
5. Phase 5 — Validation: Chronological walk-forward tests, transaction costs, liquidity constraints and feature ablation to determine which additions genuinely improve results.  
      
    

Final specification: Start with daily OHLCV, delivery, momentum, volatility, liquidity and market/sector context across a survivorship-aware NSE equity universe. Add timestamped company events and fundamentals next. Only then invest in expensive derivatives or order-book data. The objective is to prove incremental out-of-sample predictive value for each data family, not maximize the number of features.