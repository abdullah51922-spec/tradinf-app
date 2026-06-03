# ============================================================
# داشبورد التداول السعودي - النسخة المحسّنة
# ============================================================

import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import numpy as np
import pytz
import json
import csv
import os
from datetime import datetime, timedelta

# ============================================================
# 1. الإعدادات الأساسية
# ============================================================

RIYADH_TZ = pytz.timezone("Asia/Riyadh")

def now_riyadh():
    return datetime.now(RIYADH_TZ)

# أوقات السوق
MARKET_PRE_OPEN  = 9 * 60 + 30   # 9:30
MARKET_SIGNALS   = 10 * 60 + 15  # 10:15
MARKET_OPEN      = 10 * 60        # 10:00
MARKET_CLOSE     = 15 * 60        # 15:00
MARKET_POST      = 15 * 60 + 30  # 15:30
REPORT_TIME      = 15 * 60 + 15  # 15:15

# رأس المال
CAPITAL_DAILY    = 100_000
CAPITAL_MID      = 100_000
CAPITAL_RESERVE  = 100_000
CAPITAL_SAFETY   = 100_000
MAX_TRADE_DAILY  = 20_000
MAX_TRADE_MID    = 30_000
DAILY_LOSS_STOP  = 15_000

# أهداف
TARGET_DAILY_PCT = 0.5
TARGET_MID_PCT   = 2.0

# مؤشرات
VOL_SPIKE_HIGH   = 1.5
VOL_SPIKE_VERY   = 2.0
ATR_MULTIPLIER   = 1.5

# مسارات البيانات
DATA_DIR         = "data"
SIGNALS_DB       = os.path.join(DATA_DIR, "signals_database.csv")
PERF_HISTORY     = os.path.join(DATA_DIR, "performance_history.csv")
DAILY_DIR        = os.path.join(DATA_DIR, "daily_reports")
WEEKLY_DIR       = os.path.join(DATA_DIR, "weekly_reports")
MONTHLY_DIR      = os.path.join(DATA_DIR, "monthly_reports")

# إنشاء المجلدات
for d in [DATA_DIR, DAILY_DIR, WEEKLY_DIR, MONTHLY_DIR]:
    os.makedirs(d, exist_ok=True)

# ============================================================
# 2. قوائم الأسهم
# ============================================================

STOCKS_ACTIVE = [
    ("2222","أرامكو السعودية"),("1120","مصرف الراجحي"),("7010","الاتصالات السعودية"),
    ("1180","البنك الأهلي السعودي"),("1050","بي اس اف"),("1211","معادن"),
    ("2082","أكوا باور"),("2010","سابك"),("4030","النقل البحري"),
    ("1020","بنك الجزيرة"),("2350","كيان للبتروكيماويات"),("4200","الدريس للبترول"),
    ("4210","الأبحاث والإعلام"),("4220","إعمار المدينة الاقتصادية"),("2060","التصنيع الوطنية"),
    ("1150","مصرف الإنماء"),("4300","دار الأركان"),("4001","أسواق عبدالله العثيم"),
    ("2150","الصناعات الزجاجية"),("4260","المتحدة للمواصلات"),("4031","الخدمات الأرضية"),
    ("1140","بنك البلاد"),("4050","سالك"),("2330","المتقدمة للبتروكيماويات"),
    ("1030","البنك السعودي للاستثمار"),("2380","رابغ للتكرير"),("1810","سيرا القابضة"),
    ("4240","سينومي ريتيل"),("2360","الأنابيب الفخارية"),("1060","البنك السعودي الأول"),
    ("2290","ينبع الوطنية للبتروكيماويات"),("2160","أميانتيت العربية"),("4160","ثمار التنمية"),
    ("2190","البنى التحتية المستدامة"),("4280","المملكة القابضة"),("2370","الشرق الأوسط للكابلات"),
    ("4310","مدينة المعرفة الاقتصادية"),("4320","الأندلس العقارية"),("2250","الاستثمار الصناعي"),
    ("4180","فتيحي القابضة"),("2100","وفرة للصناعة"),("4130","الباحة للاستثمار"),
    ("3002","أسمنت نجران"),("3003","أسمنت المدينة"),("3007","زهرة الواحة"),
    ("3010","الأسمنت العربية"),("4150","الرياض للتعمير"),("4051","باعظيم التجارية"),
    ("4190","جرير للتسويق"),
]

STOCKS_SCAN = [
    ("1010","بنك الرياض"),("1080","العربي"),("1090","1090"),
    ("1111","تداول السعودية القابضة"),
    ("1301","اتحاد مصانع الأسلاك"),("1302","بوان"),
    ("1303","الصناعات الكهربائية"),("1304","اليمامة للحديد"),
    ("1320","الأنابيب الصلب"),
    ("2001","كيمائيات الميثانول"),("2030","المصافي العربية"),
    ("2080","الغاز والتصنيع الأهلية"),("2130","التنمية الصناعية"),
    ("2170","اللجين"),("2180","تصنيع مواد التعبئة"),
    ("2200","الأنابيب العربية"),("2230","الكيميائية السعودية"),
    ("2240","صناعات البناء المتقدمة"),("2270","الألبان والأغذية"),
    ("2300","صناعة الورق"),("2310","الصحراء للبتروكيماويات"),
    ("3001","أسمنت حائل"),("3004","أسمنت الشمالية"),
    ("3005","أسمنت أم القرى"),("3008","الكثيري القابضة"),
    ("3020","أسمنت اليمامة"),
    ("4002","المواساة الطبية"),("4003","المتحدة للإلكترونيات"),
    ("4004","دله للخدمات الصحية"),("4005","الوطنية للرعاية الطبية"),
    ("4011","لازوردي للمجوهرات"),("4020","العقارية السعودية"),
    ("4040","النقل الجماعي"),("4070","تهامة"),
    ("4090","طيبة للاستثمار"),("4100","مكة للإنشاء"),
    ("4140","الصادرات الصناعية"),("4170","المشروعات السياحية"),
    ("4230","البحر الأحمر العالمية"),("4270","الطباعة والتغليف"),
    ("4290","الخليج للتدريب"),
    ("4340","الراجحي ريت"),("4345","الإنماء ريت"),
    ("2040","الخزف السعودي"),("2090","الجبس الأهلية"),
    ("2140","أيان للاستثمار"),("2210","نماء للكيماويات"),
    ("2320","البابطين للطاقة"),("2340","ارتيكس للاستثمار"),
    ("4007","الحمادي القابضة"),("4008","السعودية للعدد والأدوات"),
    ("4080","سناد القابضة"),("4346","ميفك ريت"),
]

# ============================================================
# 3. المصادقة والاتصال بـ API
# ============================================================

st.set_page_config(
    page_title="داشبورد التداول السعودي",
    layout="wide",
    page_icon="📊",
    initial_sidebar_state="collapsed"
)

API_KEY = st.secrets["API_KEY"]

if "auth" not in st.session_state:
    st.session_state.auth = False
if "paper_mode" not in st.session_state:
    st.session_state.paper_mode = False
if "daily_pnl" not in st.session_state:
    st.session_state.daily_pnl = 0.0
if "bot_active" not in st.session_state:
    st.session_state.bot_active = True
if "signal_log" not in st.session_state:
    st.session_state.signal_log = []

if not st.session_state.auth:
    st.markdown("<h2 style='text-align:center;margin-top:100px'>📊 داشبورد التداول السعودي</h2>", unsafe_allow_html=True)
    col_a, col_b, col_c = st.columns([1,1,1])
    with col_b:
        pwd = st.text_input("كلمة المرور", type="password")
        if st.button("دخول", use_container_width=True):
            if pwd == "Theapp1994":
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("كلمة مرور خاطئة")
    st.stop()

try:
    from sahmk import SahmkClient
    client = SahmkClient(api_key=API_KEY)
except Exception as e:
    st.error(f"❌ خطأ في الاتصال بـ API: {e}")
    st.stop()

# ============================================================
# 4. جلب البيانات
# ============================================================

@st.cache_data(ttl=30)
def get_all_quotes():
    try:
        all_syms = [s[0] for s in STOCKS_ACTIVE + STOCKS_SCAN]
        quotes_dict = {}
        errors = []
        for i in range(0, len(all_syms), 5):
            batch = all_syms[i:i+5]
            try:
                result = client.quotes(batch)
                for q in result.quotes:
                    quotes_dict[q.symbol] = q
            except Exception as e:
                err_msg = str(e)
                if "403" in err_msg:
                    st.error("❌ API Key منتهي أو غير صالح (403). توقف التداول.")
                    st.stop()
                errors.append(f"batch {i}: {err_msg[:50]}")
        return quotes_dict, errors
    except Exception as e:
        return {}, [str(e)]

@st.cache_data(ttl=300)
def get_historical(sym):
    try:
        h = client.historical(sym, from_date="2025-01-01")
        closes, highs, lows, volumes = [], [], [], []
        for item in h.data:
            if item.close and item.close > 0:
                closes.append(float(item.close))
                highs.append(float(item.high or item.close))
                lows.append(float(item.low or item.close))
                volumes.append(float(item.volume or 0))
        return closes, highs, lows, volumes
    except Exception:
        return [], [], [], []

@st.cache_data(ttl=30)
def get_market():
    try:
        return client.market_summary(), None
    except Exception as e:
        return None, str(e)

@st.cache_data(ttl=600)
def get_movers():
    try:
        return client.gainers(), client.losers(), client.volume_leaders(), None
    except Exception as e:
        return None, None, None, str(e)

# ============================================================
# 5. المؤشرات الفنية
# ============================================================

def calc_ema_series(data, period):
    if len(data) < period:
        return []
    k = 2.0 / (period + 1)
    ema = [sum(data[:period]) / period]
    for price in data[period:]:
        ema.append(price * k + ema[-1] * (1 - k))
    return ema

def calc_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50.0
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains  = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)

def calc_rsi_direction(closes, period=14, lookback=5):
    """اتجاه RSI - هل يصعد أم ينزل؟"""
    if len(closes) < period + lookback + 1:
        return 0.0
    rsi_now  = calc_rsi(closes, period)
    rsi_prev = calc_rsi(closes[:-lookback], period)
    return round(rsi_now - rsi_prev, 1)

def calc_macd(closes):
    if len(closes) < 35:
        return 0.0, 0.0, 0.0
    ema12 = calc_ema_series(closes, 12)
    ema26 = calc_ema_series(closes, 26)
    min_len = min(len(ema12), len(ema26))
    macd_line = [ema12[-(min_len-i)] - ema26[-(min_len-i)] for i in range(min_len)]
    if len(macd_line) < 9:
        return 0.0, 0.0, 0.0
    signal_line = calc_ema_series(macd_line, 9)
    macd_val   = macd_line[-1]
    signal_val = signal_line[-1] if signal_line else 0.0
    histogram  = macd_val - signal_val
    return round(macd_val, 3), round(signal_val, 3), round(histogram, 3)

def calc_macd_direction(closes, lookback=3):
    """هل الـ histogram بيصعد أم بينزل؟"""
    if len(closes) < 38 + lookback:
        return 0.0
    _, _, hist_now  = calc_macd(closes)
    _, _, hist_prev = calc_macd(closes[:-lookback])
    return round(hist_now - hist_prev, 4)

def calc_ma(closes, period):
    if len(closes) < period:
        return 0.0
    return round(sum(closes[-period:]) / period, 2)

def calc_bollinger(closes, period=20, std_dev=2):
    if len(closes) < period:
        return 0.0, 0.0, 0.0
    recent   = closes[-period:]
    ma       = sum(recent) / period
    variance = sum((x - ma) ** 2 for x in recent) / period
    std      = variance ** 0.5
    return round(ma + std_dev*std, 2), round(ma, 2), round(ma - std_dev*std, 2)

def calc_atr(highs, lows, closes, period=14):
    if len(closes) < period + 1:
        return 0.0
    tr_list = []
    for i in range(1, len(closes)):
        h, l, prev_c = highs[i], lows[i], closes[i-1]
        tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
        tr_list.append(tr)
    if len(tr_list) < period:
        return 0.0
    return round(sum(tr_list[-period:]) / period, 3)

def calc_volume(volumes):
    if len(volumes) < 20:
        return False, False, 0.0
    avg_5  = sum(volumes[-5:]) / 5 if len(volumes) >= 5 else 0
    avg_20 = sum(volumes[-20:]) / 20
    ratio  = avg_5 / avg_20 if avg_20 > 0 else 0.0
    return ratio >= VOL_SPIKE_HIGH, ratio >= VOL_SPIKE_VERY, round(ratio, 1)

# ============================================================
# 6. السيولة الفنية والانزلاق
# ============================================================

def calc_liquidity_score(vol_ratio, volumes):
    """حساب السيولة من 1 إلى 10"""
    if vol_ratio >= 3:
        score = 9
    elif vol_ratio >= 2:
        score = 8
    elif vol_ratio >= 1.5:
        score = 7
    elif vol_ratio >= 1.2:
        score = 6
    elif vol_ratio >= 1.0:
        score = 5
    elif vol_ratio >= 0.7:
        score = 4
    elif vol_ratio >= 0.5:
        score = 3
    else:
        score = 2

    avg_vol = sum(volumes[-5:]) / 5 if len(volumes) >= 5 else 0
    if avg_vol > 5_000_000:
        score = min(score + 1, 10)
    elif avg_vol < 500_000:
        score = max(score - 1, 1)

    return score

def calc_slippage(liquidity_score):
    """الانزلاق حسب السيولة"""
    if liquidity_score >= 8:
        return 0.0005, "عالية جداً ✅"
    elif liquidity_score >= 6:
        return 0.0015, "عالية 🟡"
    elif liquidity_score >= 4:
        return 0.003, "متوسطة ⚠️"
    else:
        return 0.005, "منخفضة 🔴"

def calc_entry_price(price, slippage_pct):
    return round(price * (1 + slippage_pct), 2)

def market_accepts(liquidity_score):
    return liquidity_score >= 4

# ============================================================
# 7. نظام النقاط والإشارات
# ============================================================

def get_strength(change_pct, rsi, rsi_dir, macd, macd_signal, macd_hist, macd_dir,
                 ma20, ma50, price, vol_high, vol_very_high, vol_ratio,
                 tasi_bullish, bb_lower, bb_upper):
    score   = 0
    reasons = []

    # RSI (30 نقطة)
    if rsi < 30:
        score += 30; reasons.append(f"RSI تشبع بيع ({rsi}) 🔥")
    elif rsi < 40:
        score += 22; reasons.append(f"RSI منطقة شراء ({rsi})")
    elif 40 <= rsi < 55:
        score += 12; reasons.append(f"RSI متوازن ({rsi})")
    elif rsi >= 70:
        score -= 15; reasons.append(f"⚠️ RSI ذروة شراء ({rsi})")

    # اتجاه RSI
    if rsi_dir > 10:
        score += 8; reasons.append(f"RSI زخم قوي (+{rsi_dir})")
    elif rsi_dir > 5:
        score += 4; reasons.append(f"RSI صاعد (+{rsi_dir})")
    elif rsi_dir < -5:
        score -= 5; reasons.append(f"RSI نازل ({rsi_dir})")

    # MACD (25 نقطة)
    if macd > 0 and macd_hist > 0 and macd > macd_signal and macd_dir > 0:
        score += 25; reasons.append("MACD إشارة شراء قوية 💪")
    elif macd > macd_signal and macd_hist > 0:
        score += 15; reasons.append("MACD تقاطع صاعد")
    elif macd > 0:
        score += 6
    if macd_dir < 0:
        score -= 8; reasons.append("⚠️ MACD زخم ضعيف")

    # المتوسطات (20 نقطة) - بدون MA200
    if ma50 > 0 and price > ma50:
        score += 10; reasons.append("فوق MA50")
    if ma20 > 0 and price > ma20:
        score += 8; reasons.append("فوق MA20")
    if ma20 > 0 and ma50 > 0 and ma20 > ma50:
        score += 7; reasons.append("Golden Cross MA20>MA50 ⭐")

    # الحجم (20 نقطة)
    if vol_very_high:
        score += 20; reasons.append(f"حجم استثنائي ×{vol_ratio} 🚀")
    elif vol_high:
        score += 12; reasons.append(f"حجم مرتفع ×{vol_ratio}")
    elif vol_ratio >= 1.2:
        score += 6; reasons.append(f"حجم فوق المتوسط ×{vol_ratio}")

    # TASI (5 نقاط)
    if tasi_bullish:
        score += 5; reasons.append("السوق صاعد")

    # بولينجر (5 نقاط)
    if bb_lower > 0 and price <= bb_lower * 1.01:
        score += 5; reasons.append("عند الحد الأدنى BB")
    elif bb_upper > 0 and price >= bb_upper * 0.99:
        score -= 5; reasons.append("⚠️ عند الحد الأعلى BB")

    return min(max(score, 0), 100), reasons

def calc_confidence(score, rsi_dir, macd_dir, vol_high, vol_very_high):
    """نسبة الثقة من 1 إلى 100%"""
    strong_signals = 0
    if rsi_dir > 10: strong_signals += 1
    if macd_dir > 0: strong_signals += 1
    if vol_very_high: strong_signals += 1
    elif vol_high:    strong_signals += 0.5

    if strong_signals >= 3:
        base = 95
    elif strong_signals >= 2:
        base = 75
    elif strong_signals >= 1:
        base = 55
    else:
        base = 30

    # تعديل بالـ score
    confidence = base * (score / 100) + base * 0.3
    return min(round(confidence), 100)

def get_signal(score, rsi, confidence):
    if score >= 75 and rsi < 70 and confidence >= 60:
        return "BUY 🟢", "strong"
    elif score >= 60 and rsi < 65 and confidence >= 45:
        return "BUY 🟢", "normal"
    elif score < 35 or rsi > 75:
        return "SELL 🔴", "sell"
    else:
        return "WAIT 🟡", "wait"

def calc_stars(score):
    if score >= 80: return "⭐⭐⭐⭐⭐"
    elif score >= 65: return "⭐⭐⭐⭐"
    elif score >= 50: return "⭐⭐⭐"
    elif score >= 35: return "⭐⭐"
    else: return "⭐"

# ============================================================
# 8. حساب الأهداف والـ Stop Loss
# ============================================================

def calc_targets_and_sl(price, atr, confidence=50, trade_type="daily"):
    """
    الهدف بناءً على توقع النموذج (ATR × معامل حسب قوة الإشارة)
    ثقة 80%+   → ATR × 2.0
    ثقة 60-80% → ATR × 1.5
    ثقة أقل   → ATR × 1.0
    """
    if confidence >= 80:
        atr_mult    = 2.0
        model_label = "توقع قوي 🔥"
    elif confidence >= 60:
        atr_mult    = 1.5
        model_label = "توقع متوسط 📊"
    else:
        atr_mult    = 1.0
        model_label = "توقع محافظ 🛡️"

    stop_loss  = round(price - ATR_MULTIPLIER * atr, 2)
    target     = round(price + atr_mult * atr, 2)
    target_pct = round((target - price) / price * 100, 2) if price > 0 else 0
    return target, stop_loss, target_pct, model_label

def calc_position_size(capital, price, stop_loss, max_amount):
    risk_per_share = price - stop_loss
    if risk_per_share <= 0:
        return 0, 0
    shares = int(min(capital, max_amount) / price)
    amount = shares * price
    return shares, round(amount, 2)

def calc_market_state(tasi_change_pct, vol_ratio_tasi=1.0):
    """حالة السوق وكم تستثمر"""
    if tasi_change_pct > 1.5 and vol_ratio_tasi > 1.5:
        return "قوي جداً 💪", 250_000, "15-20 ألف ريال"
    elif tasi_change_pct > 0.5:
        return "قوي 📈", 200_000, "10-15 ألف ريال"
    elif tasi_change_pct > -0.5:
        return "متوسط ➡️", 150_000, "5-8 آلاف ريال"
    else:
        return "ضعيف ⚠️", 100_000, "2-4 آلاف ريال"

# ============================================================
# 9. قاعدة البيانات
# ============================================================

SIGNALS_COLS = [
    "signal_id","date","time","symbol","name","signal_type",
    "price","entry_price","target","stop_loss","confidence",
    "rsi","macd","volume_ratio","slippage","liquidity_score",
    "result_24h","result_48h","result_72h","profit_loss"
]

def init_signals_db():
    if not os.path.exists(SIGNALS_DB):
        with open(SIGNALS_DB, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=SIGNALS_COLS)
            writer.writeheader()

def save_signal(sym, name, signal_type, price, entry_price, target,
                stop_loss, confidence, rsi, macd, vol_ratio,
                slippage, liquidity_score):
    init_signals_db()
    now = now_riyadh()
    existing = []
    try:
        with open(SIGNALS_DB, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            existing = list(reader)
    except:
        pass

    signal_id = len(existing) + 1
    row = {
        "signal_id": signal_id,
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "symbol": sym,
        "name": name,
        "signal_type": signal_type,
        "price": price,
        "entry_price": entry_price,
        "target": target,
        "stop_loss": stop_loss,
        "confidence": confidence,
        "rsi": rsi,
        "macd": macd,
        "volume_ratio": vol_ratio,
        "slippage": slippage,
        "liquidity_score": liquidity_score,
        "result_24h": "",
        "result_48h": "",
        "result_72h": "",
        "profit_loss": "",
    }
    with open(SIGNALS_DB, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=SIGNALS_COLS)
        writer.writerow(row)

    # إضافة للسجل اليومي في الذاكرة
    st.session_state.signal_log.append({
        "الوقت": now.strftime("%H:%M"),
        "الرمز": sym,
        "الاسم": name,
        "الإشارة": signal_type,
        "السعر": price,
        "الهدف": target,
        "Stop Loss": stop_loss,
        "الثقة": f"{confidence}%",
    })

def load_today_signals():
    init_signals_db()
    today = now_riyadh().strftime("%Y-%m-%d")
    try:
        with open(SIGNALS_DB, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return [r for r in reader if r.get("date") == today]
    except:
        return []

def save_daily_report(data):
    today = now_riyadh().strftime("%Y_%m_%d")
    path  = os.path.join(DAILY_DIR, f"{today}.csv")
    if data:
        df = pd.DataFrame(data)
        df.to_csv(path, index=False, encoding="utf-8")

# ============================================================
# 10. تحليل الأسهم
# ============================================================

def analyze_stocks(stocks_list, quotes_dict, tasi_bullish, trade_type="daily"):
    now      = now_riyadh()
    now_mins = now.hour * 60 + now.minute
    data, failed = [], []

    for sym, name in stocks_list:
        try:
            q = quotes_dict.get(sym)
            if not q or not hasattr(q, "price") or not q.price:
                failed.append(f"{sym}(لا سعر)")
                continue

            closes, highs, lows, volumes = get_historical(sym)
            if len(closes) < 30:
                failed.append(f"{sym}(بيانات قليلة)")
                continue

            price      = float(q.price)
            change_pct = float(getattr(q, "change_percent", 0) or 0)

            rsi      = calc_rsi(closes)
            rsi_dir  = calc_rsi_direction(closes)
            macd, macd_signal, macd_hist = calc_macd(closes)
            macd_dir = calc_macd_direction(closes)
            ma20     = calc_ma(closes, 20)
            ma50     = calc_ma(closes, 50)
            bb_upper, bb_mid, bb_lower = calc_bollinger(closes)
            atr      = calc_atr(highs, lows, closes)
            vol_high, vol_very_high, vol_ratio = calc_volume(volumes)

            liq_score = calc_liquidity_score(vol_ratio, volumes)
            slippage_pct, liq_label = calc_slippage(liq_score)
            entry_price = calc_entry_price(price, slippage_pct)
            accepts     = market_accepts(liq_score)

            score, reasons = get_strength(
                change_pct, rsi, rsi_dir, macd, macd_signal, macd_hist, macd_dir,
                ma20, ma50, price, vol_high, vol_very_high, vol_ratio,
                tasi_bullish, bb_lower, bb_upper
            )

            confidence = calc_confidence(score, rsi_dir, macd_dir, vol_high, vol_very_high)
            signal, signal_type = get_signal(score, rsi, confidence)
            stars = calc_stars(score)

            target, stop_loss, target_pct, model_label = calc_targets_and_sl(price, atr, confidence, trade_type)
            shares, amount = calc_position_size(
                CAPITAL_DAILY if trade_type == "daily" else CAPITAL_MID,
                entry_price, stop_loss,
                MAX_TRADE_DAILY if trade_type == "daily" else MAX_TRADE_MID
            )

            # RSI تحذير
            rsi_warning = "🔴 احذر ذروة!" if rsi > 70 else ("🟡 اقترب من الذروة" if rsi > 65 else "")

            data.append({
                "الرمز": sym,
                "الاسم": name,
                "السعر": price,
                "التغيير%": round(change_pct, 2),
                "النجوم": stars,
                "الإشارة": signal,
                "الهدف": target,
                "هدف%": f"+{target_pct}%",
                "توقع النموذج": model_label,
                "Stop Loss": stop_loss,
                "سعر الدخول": entry_price,
                "الثقة%": confidence,
                "RSI": rsi,
                "RSI اتجاه": rsi_dir,
                "تحذير RSI": rsi_warning,
                "MACD": macd,
                "Hist": macd_hist,
                "MACD زخم": "صاعد ✅" if macd_dir > 0 else "نازل ⚠️",
                "MA20": ma20,
                "MA50": ma50,
                "ATR": atr,
                "BB+": bb_upper,
                "BB-": bb_lower,
                "حجم×": vol_ratio,
                "السيولة": f"{liq_score}/10",
                "انزلاق": liq_label,
                "السوق يقبل": "✅ نعم" if accepts else "❌ لا",
                "الأسهم": shares,
                "المبلغ": amount,
                "القوة%": score,
                "_reasons": " | ".join(reasons),
                "_signal_type": signal_type,
                "_confidence": confidence,
                "_liq_score": liq_score,
                "_slippage": slippage_pct,
                "_entry": entry_price,
                "_target": target,
                "_stop": stop_loss,
                "_rsi": rsi,
                "_macd": macd,
                "_vol": vol_ratio,
                "_sym": sym,
                "_name": name,
            })
        except Exception as e:
            failed.append(f"{sym}({str(e)[:30]})")

    return data, failed

# ============================================================
# 11. الواجهة - CSS
# ============================================================

st.markdown("""
<style>
    /* ثيم فاتح نظيف */
    .stApp { background-color: #f5f6fa; }

    .stMetric label { font-size: 13px !important; color: #444; }
    .stMetric [data-testid="stMetricValue"] { color: #111; font-weight: 700; }
    .stDataFrame { font-size: 12px; }

    /* البطاقات */
    .signal-card {
        padding: 16px;
        border-radius: 14px;
        margin-bottom: 12px;
        border: 1.5px solid #dde1ea;
        box-shadow: 0 2px 8px rgba(0,0,0,0.07);
        background: #ffffff;
    }
    .buy-card  {
        background: #f0faf2;
        border-color: #4caf50;
        border-left: 5px solid #4caf50;
    }
    .wait-card {
        background: #fffdf0;
        border-color: #f0b429;
        border-left: 5px solid #f0b429;
    }
    .sell-card {
        background: #fff5f5;
        border-color: #e53935;
        border-left: 5px solid #e53935;
    }

    /* النصوص داخل البطاقات */
    .signal-card h4 { color: #1a1a2e; margin: 0 0 6px 0; font-size: 15px; }
    .signal-card p  { color: #333; font-size: 13px; margin: 3px 0; }

    /* الـ badges */
    .metric-row { display: flex; gap: 6px; flex-wrap: wrap; margin: 6px 0; }
    .badge {
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 700;
    }
    .badge-green  { background: #e6f4ea; color: #2e7d32; border: 1px solid #a5d6a7; }
    .badge-yellow { background: #fff8e1; color: #f57f17; border: 1px solid #ffe082; }
    .badge-red    { background: #ffebee; color: #c62828; border: 1px solid #ef9a9a; }
    .badge-blue   { background: #e3f2fd; color: #1565c0; border: 1px solid #90caf9; }

    /* الأزرار */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        border: 1.5px solid #dde1ea;
        background: #ffffff;
        color: #1a1a2e;
        transition: all 0.2s;
    }
    .stButton > button:hover {
        background: #f0f4ff;
        border-color: #4c6ef5;
        color: #4c6ef5;
    }

    /* الـ tabs */
    .stTabs [data-baseweb="tab"] {
        font-weight: 600;
        color: #555;
    }
    .stTabs [aria-selected="true"] {
        color: #4c6ef5 !important;
        border-bottom: 2px solid #4c6ef5;
    }

    details summary { color: #666; font-size: 12px; cursor: pointer; }
    details p { color: #555; font-size: 11px; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 12. شريط الأدوات العلوي
# ============================================================

st_autorefresh(interval=30_000, key="autorefresh")

now      = now_riyadh()
now_mins = now.hour * 60 + now.minute
weekday  = now.weekday()  # 0=Monday ... 6=Sunday
is_workday = weekday < 5  # الأحد=6 في Python، لكن نتحقق لاحقاً

# في pytz: weekday() 0=Monday ... 6=Sunday
# السوق السعودي: الأحد-الخميس = 6,0,1,2,3
is_workday_sa = weekday in [6, 0, 1, 2, 3]

market_open    = is_workday_sa and MARKET_OPEN <= now_mins < MARKET_CLOSE
signals_active = is_workday_sa and now_mins >= MARKET_SIGNALS and now_mins < MARKET_CLOSE
pre_open       = is_workday_sa and MARKET_PRE_OPEN <= now_mins < MARKET_OPEN

# Circuit Breaker
market, market_err = get_market()
tasi_change = 0.0
tasi_value  = 0.0
tasi_bullish = False

if market:
    try:
        tasi_change  = float(getattr(market, "index_change_percent", 0) or 0)
        tasi_value   = float(getattr(market, "index_value", 0) or 0)
        tasi_bullish = (
            getattr(market, "market_mood", "") == "Bullish" or
            getattr(market, "advancing", 0) > getattr(market, "declining", 0)
        )
    except:
        pass

circuit_break = tasi_change < -3.0

st.title("📊 داشبورد التداول السعودي")

# Paper Mode Banner
if st.session_state.paper_mode:
    st.warning("🧪 **وضع المحاكاة** - لا توجد صفقات حقيقية")

if circuit_break:
    st.error(f"🚨 **Circuit Breaker** - TASI نزل {tasi_change:.2f}% - التداول موقوف!")

if not st.session_state.bot_active:
    st.error("🛑 **البوت موقوف** - تحتاج تفعيله يدوياً")

# ---- شريط الحالة ----
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    if not is_workday_sa:
        st.warning("🔒 عطلة نهاية الأسبوع")
    elif now_mins < MARKET_PRE_OPEN:
        st.info(f"⏳ يبدأ سحب البيانات بعد {MARKET_PRE_OPEN - now_mins} دقيقة")
    elif pre_open:
        st.warning(f"⏳ السوق يفتح بعد {MARKET_OPEN - now_mins} دقيقة")
    elif now_mins == MARKET_OPEN or (MARKET_OPEN <= now_mins < MARKET_SIGNALS):
        st.error(f"⛔ أول 15 دقيقة - انتظر حتى 10:15")
    elif market_open and signals_active:
        st.success("✅ السوق مفتوح - الإشارات نشطة")
    elif market_open:
        st.success("✅ السوق مفتوح")
    else:
        st.warning("🔒 السوق أغلق")

with c2:
    if market:
        try:
            st.metric("TASI", f"{tasi_value:,.0f}", f"{tasi_change:+.2f}%")
        except:
            st.metric("TASI", "—")
    else:
        st.metric("TASI", "—")

with c3:
    market_state, invest_amount, expected_profit = calc_market_state(tasi_change)
    st.metric("حالة السوق", market_state)

with c4:
    st.metric("توصية الاستثمار", f"{invest_amount:,.0f} ﷼")

with c5:
    pnl_color = "normal" if st.session_state.daily_pnl >= 0 else "inverse"
    st.metric("ربح/خسارة اليوم", f"{st.session_state.daily_pnl:+,.0f} ﷼",
              delta_color=pnl_color)

# ---- إحصاءات السوق ----
if market:
    try:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("صاعدة 🟢", getattr(market, "advancing", "—"))
        m2.metric("هابطة 🔴", getattr(market, "declining", "—"))
        m3.metric("ثابتة ➡️",  getattr(market, "unchanged", "—"))
        m4.metric("مزاج السوق", getattr(market, "market_mood", "—"))
    except:
        pass

st.divider()

# ---- أزرار التحكم ----
ctrl1, ctrl2, ctrl3, ctrl4, ctrl5 = st.columns(5)
with ctrl1:
    if st.button("🔄 تحديث يدوي"):
        st.cache_data.clear()
        st.rerun()
with ctrl2:
    paper_label = "🧪 إيقاف المحاكاة" if st.session_state.paper_mode else "🧪 تفعيل المحاكاة"
    if st.button(paper_label):
        st.session_state.paper_mode = not st.session_state.paper_mode
        st.rerun()
with ctrl3:
    bot_label = "🛑 إيقاف البوت" if st.session_state.bot_active else "✅ تفعيل البوت"
    if st.button(bot_label):
        st.session_state.bot_active = not st.session_state.bot_active
        st.rerun()
with ctrl4:
    if st.button("💰 خذ أرباح"):
        st.success("تم تسجيل أخذ الأرباح يدوياً")
with ctrl5:
    if st.button("❌ أغلق كل الصفقات"):
        st.warning("تم إغلاق كل الصفقات يدوياً")

st.caption(
    f"🕐 {now.strftime('%H:%M:%S')} | "
    f"📅 {now.strftime('%Y-%m-%d')} | "
    f"تحديث الأسعار: 30ث | المؤشرات: 5د"
)

# ============================================================
# 13. جلب وتحليل البيانات
# ============================================================

with st.spinner("جاري تحليل الأسهم..."):
    quotes_dict, api_errors = get_all_quotes()
    data1, failed1 = analyze_stocks(STOCKS_ACTIVE, quotes_dict, tasi_bullish, "daily")
    data2, failed2 = analyze_stocks(STOCKS_SCAN,   quotes_dict, tasi_bullish, "daily")

total_ok   = len(data1) + len(data2)
total_fail = len(failed1) + len(failed2)

if api_errors or failed1 or failed2:
    with st.expander(f"⚠️ مشاكل ({total_fail} سهم مفقود)"):
        if api_errors: st.error("أخطاء API: " + str(api_errors))
        if failed1: st.write("النشطة:", failed1)
        if failed2: st.write("المسح:", failed2)

# ============================================================
# 14. دالة عرض البطاقة
# ============================================================

def render_stock_card(row, key_suffix=""):
    sig_type = row.get("_signal_type", "wait")
    card_class = {"strong": "buy-card", "normal": "buy-card",
                  "sell": "sell-card", "wait": "wait-card"}.get(sig_type, "wait-card")

    rsi_warn = row.get("تحذير RSI", "")

    sig_badge = "green" if sig_type in ["strong","normal"] else "red" if sig_type=="sell" else "yellow"
    liq_badge = "green" if row.get("_liq_score",0) >= 7 else "yellow" if row.get("_liq_score",0) >= 4 else "red"
    mkt_badge = "green" if "✅" in row.get("السوق يقبل","") else "red"

    st.markdown(f"""
    <div class='signal-card {card_class}'>
        <div style='display:flex;justify-content:space-between;align-items:center'>
            <h4>{row['الرمز']} — {row['الاسم']}</h4>
            <span style='font-size:22px'>{row['النجوم']}</span>
        </div>
        <div class='metric-row'>
            <span class='badge badge-{sig_badge}'>{row['الإشارة']}</span>
            <span class='badge badge-blue'>ثقة {row['الثقة%']}%</span>
            <span class='badge badge-{liq_badge}'>سيولة {row['السيولة']}</span>
            <span class='badge badge-{mkt_badge}'>{row['السوق يقبل']}</span>
        </div>
        <div style='margin-top:10px;font-size:13px;color:#222;line-height:1.8'>
            💰 <b>السعر:</b> {row['السعر']} &nbsp;|&nbsp;
            🎯 <b>الهدف:</b> {row['الهدف']} &nbsp;
            <span style='color:#2e7d32;font-weight:bold'>({row.get('هدف%','')})</span> &nbsp;|&nbsp;
            🛑 <b>Stop:</b> {row['Stop Loss']}<br>
            🤖 <b>توقع النموذج:</b> {row.get('توقع النموذج','—')}<br>
            📥 <b>سعر الدخول:</b> {row['سعر الدخول']} &nbsp;({row['انزلاق']})<br>
            📊 <b>RSI:</b> {row['RSI']} {rsi_warn} &nbsp;|&nbsp;
            📈 <b>MACD:</b> {row['MACD']} {row['MACD زخم']}<br>
            📦 <b>الكمية:</b> {row['الأسهم']} سهم &nbsp;=&nbsp; <b>{row['المبلغ']:,.0f} ﷼</b>
        </div>
        <details style='margin-top:8px'>
            <summary>أسباب الإشارة 🔍</summary>
            <p style='margin:6px 0'>{row['_reasons']}</p>
        </details>
    </div>
    """, unsafe_allow_html=True)

    # أزرار
    col_a, col_b, col_c = st.columns(3)
    with col_a:
        if st.button(f"ادخل الآن 🚀", key=f"enter_{row['الرمز']}_{key_suffix}"):
            st.session_state[f"calc_{row['الرمز']}"] = True
    with col_b:
        if st.button(f"اطلع 📤", key=f"exit_{row['الرمز']}_{key_suffix}"):
            if row["السعر"] > row["الهدف"]:
                profit = (row["السعر"] - row["الهدف"]) * row["الأسهم"]
                st.success(f"ربح تقريبي: {profit:,.0f} ﷼")
            else:
                loss = (row["الهدف"] - row["السعر"]) * row["الأسهم"]
                st.error(f"خسارة تقريبية: {loss:,.0f} ﷼")
    with col_c:
        if st.button(f"احسب 🧮", key=f"calc_btn_{row['الرمز']}_{key_suffix}"):
            st.session_state[f"show_calc_{row['الرمز']}"] = True

    if st.session_state.get(f"calc_{row['الرمز']}"):
        amount_in = st.number_input(
            "أدخل المبلغ (ريال):", min_value=1000, max_value=200000,
            value=20000, key=f"amt_{row['الرمز']}_{key_suffix}"
        )
        qty = int(amount_in / row["سعر الدخول"])
        profit_potential = qty * (row["الهدف"] - row["سعر الدخول"])
        loss_potential   = qty * (row["سعر الدخول"] - row["Stop Loss"])
        st.info(f"الكمية: {qty} سهم | ربح متوقع: {profit_potential:,.0f} ﷼ | خسارة محتملة: {loss_potential:,.0f} ﷼")

        if st.button("✅ تأكيد الدخول", key=f"confirm_{row['الرمز']}_{key_suffix}"):
            save_signal(
                row["_sym"], row["_name"], row["الإشارة"],
                row["السعر"], row["_entry"], row["_target"], row["_stop"],
                row["_confidence"], row["_rsi"], row["_macd"], row["_vol"],
                row["_slippage"], row["_liq_score"]
            )
            st.success("✅ تم تسجيل الصفقة!")
            st.session_state[f"calc_{row['الرمز']}"] = False

# ============================================================
# 15. دالة عرض الجدول
# ============================================================

def render_table(data_list, key_prefix):
    if not data_list:
        st.warning("لا توجد بيانات")
        return

    df = pd.DataFrame(data_list)
    display_cols = [
        "الرمز","الاسم","السعر","التغيير%",
        "النجوم","الإشارة","الهدف","Stop Loss",
        "سعر الدخول","الثقة%","RSI","تحذير RSI",
        "MACD زخم","حجم×","السيولة","القوة%"
    ]
    display_cols = [c for c in display_cols if c in df.columns]
    df_display = df[display_cols].copy()

    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1:
        show_buy = st.checkbox("BUY فقط 🟢", key=f"{key_prefix}_buy")
    with col_f2:
        show_strong = st.checkbox("ثقة 75%+ فقط", key=f"{key_prefix}_strong")
    with col_f3:
        hide_rsi = st.checkbox("إخفاء RSI ذروة", key=f"{key_prefix}_rsi")
    with col_f4:
        sort_by = st.selectbox("ترتيب:", ["القوة%","الثقة%","RSI","التغيير%","حجم×"],
                               key=f"{key_prefix}_sort")

    df_display = df_display.sort_values(sort_by, ascending=(sort_by == "RSI"))

    if show_buy:
        df_display = df_display[df_display["الإشارة"] == "BUY 🟢"]
    if show_strong:
        df_display = df_display[df_display["الثقة%"] >= 75]
    if hide_rsi and "تحذير RSI" in df_display.columns:
        df_display = df_display[df_display["تحذير RSI"] == ""]

    st.dataframe(
        df_display,
        use_container_width=True,
        height=450,
        column_config={
            "القوة%":  st.column_config.ProgressColumn("القوة%",  min_value=0, max_value=100),
            "الثقة%":  st.column_config.ProgressColumn("الثقة%",  min_value=0, max_value=100),
            "RSI":     st.column_config.NumberColumn("RSI",     format="%.1f"),
            "التغيير%": st.column_config.NumberColumn("التغيير%", format="%.2f%%"),
        }
    )

    buy_df = df[df["الإشارة"] == "BUY 🟢"]
    if not buy_df.empty:
        syms = buy_df["الرمز"].tolist()
        st.success(f"🔔 BUY ({len(syms)}): {', '.join(syms[:8])}" +
                   (" وأخرى..." if len(syms) > 8 else ""))

# ============================================================
# 16. التابات
# ============================================================

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📈 السوق",
    "🌅 صفقات اليوم",
    "⚡ الأسهم النشطة",
    "🔍 المسح الشامل",
    "⭐ أفضل الفرص",
    "📋 سجل اليوم",
    "📊 التقارير",
])

# ---- تاب 1: حركة السوق ----
with tab1:
    st.subheader("📈 حركة السوق اليوم")
    g, l, v, movers_err = get_movers()
    if movers_err:
        st.warning(f"تعذر تحميل بيانات السوق: {movers_err}")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**🟢 أعلى الصاعدين**")
        try:
            gdf = pd.DataFrame([{"الرمز": x.symbol, "الاسم": x.name,
                                  "السعر": x.price, "التغيير%": x.change_percent}
                                 for x in g.movers])
            st.dataframe(gdf, use_container_width=True)
        except:
            st.info("لا توجد بيانات")
    with col2:
        st.markdown("**🔴 أكثر الهابطين**")
        try:
            ldf = pd.DataFrame([{"الرمز": x.symbol, "الاسم": x.name,
                                  "السعر": x.price, "التغيير%": x.change_percent}
                                 for x in l.movers])
            st.dataframe(ldf, use_container_width=True)
        except:
            st.info("لا توجد بيانات")
    with col3:
        st.markdown("**💹 الأكثر تداولاً**")
        try:
            vdf = pd.DataFrame([{"الرمز": x.symbol, "الاسم": x.name,
                                  "السعر": x.price, "الحجم": x.volume}
                                 for x in v.movers])
            st.dataframe(vdf, use_container_width=True)
        except:
            st.info("لا توجد بيانات")

    # ملخص السوق
    st.divider()
    ms1, ms2, ms3 = st.columns(3)
    with ms1:
        st.info(f"**حالة السوق:** {market_state}")
        st.info(f"**مبلغ الاستثمار المناسب:** {invest_amount:,.0f} ﷼")
    with ms2:
        st.info(f"**الأرباح المتوقعة:** {expected_profit}")
    with ms3:
        if tasi_change < -3:
            st.error("🚨 السوق ضعيف جداً - الإشارات خطرة!")
        elif tasi_change < 0:
            st.warning("⚠️ السوق في هبوط")
        else:
            st.success("✅ السوق إيجابي")

# ---- تاب 2: صفقات اليوم ----
with tab2:
    if not signals_active:
        st.warning("⏳ الإشارات تبدأ من 10:15 صباحاً فقط")
        if not market_open:
            st.info("السوق مغلق - البيانات أدناه للمراجعة فقط")

    all_data = data1 + data2
    df_all   = pd.DataFrame(all_data) if all_data else pd.DataFrame()

    if not df_all.empty:
        df_buy = df_all[df_all["الإشارة"] == "BUY 🟢"].sort_values("الثقة%", ascending=False)

        # ---- قسم: صفقات اليوم (هدف 0.5%) ----
        st.subheader("🌅 صفقات اليوم - هدف 0.5%")
        st.caption("تركز على الحجم والزخم الصباحي - للتداول السريع")

        df_today = df_buy[
            (df_all["حجم×"] >= 1.2) &
            (df_all["الثقة%"] >= 45)
        ].head(6) if not df_buy.empty else pd.DataFrame()

        if not df_today.empty:
            cols_today = st.columns(min(3, len(df_today)))
            for idx, (_, row) in enumerate(df_today.iterrows()):
                with cols_today[idx % 3]:
                    render_stock_card(row.to_dict(), key_suffix=f"today_{idx}")
        else:
            st.info("لا توجد صفقات يوم مناسبة حالياً")

        st.divider()

        # ---- قسم: صفقات الغد (هدف 2%) ----
        st.subheader("🌙 صفقات الغد - هدف 2%")
        st.caption("أسهم في وضع جيد للتحرك غداً")

        df_tmr = df_buy[
            (df_buy["القوة%"] >= 60) &
            (df_buy["RSI"].between(30, 60))
        ].head(6) if not df_buy.empty else pd.DataFrame()

        if not df_tmr.empty:
            cols_tmr = st.columns(min(3, len(df_tmr)))
            for idx, (_, row) in enumerate(df_tmr.iterrows()):
                with cols_tmr[idx % 3]:
                    render_stock_card(row.to_dict(), key_suffix=f"tmr_{idx}")
        else:
            st.info("لا توجد صفقات غد مناسبة حالياً")
    else:
        st.warning("لا توجد بيانات")

# ---- تاب 3: الأسهم النشطة ----
with tab3:
    st.subheader(f"⚡ الأسهم النشطة ({len(STOCKS_ACTIVE)} سهم)")
    render_table(data1, "active")

# ---- تاب 4: المسح الشامل ----
with tab4:
    st.subheader(f"🔍 المسح الشامل ({len(STOCKS_SCAN)} سهم)")
    render_table(data2, "scan")

# ---- تاب 5: أفضل الفرص ----
with tab5:
    st.subheader("⭐ أفضل الفرص - ملخص شامل")
    all_data = data1 + data2

    if all_data:
        df_all  = pd.DataFrame(all_data)
        df_best = df_all[df_all["الإشارة"] == "BUY 🟢"].sort_values("الثقة%", ascending=False)

        if not df_best.empty:
            # أقوى 3 فرص
            st.markdown("### 🏆 أقوى 3 فرص")
            top3 = df_best.head(3)
            cols = st.columns(3)
            for i, (_, row) in enumerate(top3.iterrows()):
                with cols[i]:
                    render_stock_card(row.to_dict(), key_suffix=f"best_{i}")

            st.divider()
            st.markdown("### 📋 جميع إشارات BUY")

            show_cols = [
                "الرمز","الاسم","السعر","التغيير%","النجوم",
                "الإشارة","الهدف","Stop Loss","سعر الدخول",
                "الثقة%","RSI","تحذير RSI","حجم×","السيولة","القوة%"
            ]
            show_cols = [c for c in show_cols if c in df_best.columns]
            st.dataframe(
                df_best[show_cols].head(20),
                use_container_width=True,
                column_config={
                    "القوة%": st.column_config.ProgressColumn("القوة%", min_value=0, max_value=100),
                    "الثقة%": st.column_config.ProgressColumn("الثقة%", min_value=0, max_value=100),
                }
            )
        else:
            st.info("لا توجد إشارات BUY حالياً")
    else:
        st.warning("لا توجد بيانات")

# ---- تاب 6: سجل اليوم ----
with tab6:
    st.subheader("📋 سجل إشارات اليوم")

    # السجل من الذاكرة
    if st.session_state.signal_log:
        df_log = pd.DataFrame(st.session_state.signal_log)
        st.dataframe(df_log, use_container_width=True)
    else:
        st.info("لم تُسجَّل أي إشارات اليوم بعد")

    # السجل من قاعدة البيانات
    st.divider()
    st.subheader("📂 سجل قاعدة البيانات")
    today_signals = load_today_signals()
    if today_signals:
        df_db = pd.DataFrame(today_signals)
        st.dataframe(df_db, use_container_width=True)

        # إحصاءات
        total_sigs = len(today_signals)
        buy_sigs   = len([s for s in today_signals if "BUY" in s.get("signal_type","")])
        st.metric("إجمالي الإشارات اليوم", total_sigs)
        st.metric("إشارات BUY", buy_sigs)
    else:
        st.info("لا توجد سجلات في قاعدة البيانات لهذا اليوم")

    # حفظ التقرير اليومي
    if now_mins >= REPORT_TIME and all_data:
        save_daily_report(all_data)
        st.caption("✅ تم حفظ تقرير اليوم تلقائياً")

# ---- Daily Loss Stop ----
if abs(st.session_state.daily_pnl) >= DAILY_LOSS_STOP and st.session_state.daily_pnl < 0:
    st.error(f"🚨 وصلت لحد الخسارة اليومية ({DAILY_LOSS_STOP:,.0f} ﷼) - توقف التداول!")

# ---- تاب 7: التقارير ----
with tab7:
    st.subheader("📊 التقارير والإحصاءات")

    report_tab1, report_tab2, report_tab3 = st.tabs([
        "📅 تقرير اليوم", "📆 تقرير الأسبوع", "📈 الأداء الكلي"
    ])

    # ---- تقرير اليوم ----
    with report_tab1:
        st.markdown("### 📅 تقرير اليوم")
        today_signals = load_today_signals()

        if today_signals:
            df_today = pd.DataFrame(today_signals)
            total  = len(today_signals)
            buys   = len([s for s in today_signals if "BUY"  in s.get("signal_type","")])
            sells  = len([s for s in today_signals if "SELL" in s.get("signal_type","")])
            waits  = len([s for s in today_signals if "WAIT" in s.get("signal_type","")])

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("إجمالي الإشارات", total)
            c2.metric("إشارات BUY 🟢",  buys)
            c3.metric("إشارات SELL 🔴", sells)
            c4.metric("إشارات WAIT 🟡", waits)

            st.divider()
            st.dataframe(df_today, use_container_width=True)

            # تحميل التقرير
            csv = df_today.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ تحميل تقرير اليوم CSV",
                csv,
                f"report_{now.strftime('%Y_%m_%d')}.csv",
                "text/csv"
            )
        else:
            st.info("لا توجد إشارات مسجلة اليوم")

        # حفظ تلقائي
        if now_mins >= REPORT_TIME and all_data:
            save_daily_report(all_data)
            st.success("✅ تم حفظ تقرير اليوم تلقائياً")

    # ---- تقرير الأسبوع ----
    with report_tab2:
        st.markdown("### 📆 تقرير الأسبوع")

        # قراءة كل التقارير اليومية من آخر 7 أيام
        weekly_data = []
        for i in range(7):
            day = now_riyadh() - timedelta(days=i)
            path = os.path.join(DAILY_DIR, f"{day.strftime('%Y_%m_%d')}.csv")
            if os.path.exists(path):
                try:
                    df_day = pd.read_csv(path)
                    df_day["التاريخ"] = day.strftime("%Y-%m-%d")
                    weekly_data.append(df_day)
                except:
                    pass

        if weekly_data:
            df_week = pd.concat(weekly_data, ignore_index=True)
            st.success(f"✅ بيانات {len(weekly_data)} أيام")

            # إحصاءات الأسبوع
            if "الإشارة" in df_week.columns:
                buy_week  = len(df_week[df_week["الإشارة"] == "BUY 🟢"])
                sell_week = len(df_week[df_week["الإشارة"] == "SELL 🔴"])
                wait_week = len(df_week[df_week["الإشارة"] == "WAIT 🟡"])

                w1, w2, w3 = st.columns(3)
                w1.metric("BUY هذا الأسبوع",  buy_week)
                w2.metric("SELL هذا الأسبوع", sell_week)
                w3.metric("WAIT هذا الأسبوع", wait_week)

            st.divider()
            st.dataframe(df_week, use_container_width=True)

            csv_week = df_week.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ تحميل تقرير الأسبوع", csv_week, "weekly_report.csv", "text/csv")
        else:
            st.info("لا توجد تقارير أسبوعية بعد — ستظهر بعد أول يوم تداول")

    # ---- الأداء الكلي ----
    with report_tab3:
        st.markdown("### 📈 الأداء الكلي")

        if os.path.exists(SIGNALS_DB):
            try:
                df_all_signals = pd.read_csv(SIGNALS_DB, encoding="utf-8")

                if not df_all_signals.empty:
                    total_all  = len(df_all_signals)
                    buy_all    = len(df_all_signals[df_all_signals["signal_type"].str.contains("BUY", na=False)])
                    completed  = df_all_signals[df_all_signals["result_24h"] != ""]
                    success    = len(completed[completed["profit_loss"].astype(str).str.startswith("+")])

                    p1, p2, p3, p4 = st.columns(4)
                    p1.metric("إجمالي الإشارات", total_all)
                    p2.metric("إشارات BUY", buy_all)
                    p3.metric("مكتملة (24h)", len(completed))
                    p4.metric("ناجحة", success)

                    if len(completed) > 0:
                        success_rate = round(success / len(completed) * 100, 1)
                        st.metric("نسبة النجاح", f"{success_rate}%")

                        if success_rate >= 75:
                            st.success(f"🎯 نسبة النجاح {success_rate}% - ممتاز!")
                        elif success_rate >= 60:
                            st.warning(f"📊 نسبة النجاح {success_rate}% - جيد")
                        else:
                            st.error(f"⚠️ نسبة النجاح {success_rate}% - تحتاج مراجعة")

                    st.divider()
                    st.dataframe(df_all_signals.tail(50), use_container_width=True)

                    csv_all = df_all_signals.to_csv(index=False).encode("utf-8")
                    st.download_button("⬇️ تحميل كل الإشارات", csv_all, "all_signals.csv", "text/csv")
                else:
                    st.info("قاعدة البيانات فارغة — ابدأ التداول لتظهر الإحصاءات")
            except:
                st.info("لا توجد بيانات بعد")
        else:
            st.info("لا توجد بيانات بعد — ستظهر بعد أول إشارة مسجلة")

st.divider()
st.caption("⚠️ هذه الأداة للمعلومات فقط وليست توصية استثمارية - التداول على مسؤوليتك الشخصية")
