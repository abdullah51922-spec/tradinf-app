# ============================================================
# داشبورد التداول السعودي - test11
# الجديد عن test10: الطبقة 3 — بيانات Intraday (كل 5 دقائق)
# RSI/MACD/ATR/Bollinger تُحسب على شمعات حقيقية خلال الجلسة
# ============================================================

import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import pytz
import sqlite3
import os
from datetime import datetime, timedelta

RIYADH_TZ = pytz.timezone("Asia/Riyadh")

def now_riyadh():
    return datetime.now(RIYADH_TZ)

# ============================================================
# 1. الإعدادات
# ============================================================

MARKET_PRE_OPEN  = 9  * 60 + 30
MARKET_OPEN      = 10 * 60
MARKET_FIRST15   = 10 * 60 + 15
MARKET_SIGNALS   = 10 * 60 + 15
MARKET_CLOSE     = 15 * 60
REPORT_TIME      = 15 * 60 + 15

CAPITAL_DAILY   = 100_000
MAX_TRADE_DAILY = 20_000
DAILY_LOSS_STOP = 15_000

ATR_RISK_MULT   = 1.0
ATR_T1_MULT     = 1.0
ATR_T2_MULT     = 2.0

MIN_SCORE       = 65
MIN_CONFIDENCE  = 60
MIN_SCORE_STR   = 80
MIN_CONF_STR    = 70
MIN_LIQ         = 4
MIN_ATR_PCT     = 0.008
MIN_VOL_RATIO   = 0.8
MAX_CHANGE_NEG  = -1.5

BREAKOUT_CHANGE = 1.0
BREAKOUT_VOL    = 2.0

TONIGHT_VOL     = 1.5
TONIGHT_CLOSE   = 0.75
TONIGHT_RSI_MAX = 65

# الطبقة 3 — إعدادات Intraday
INTRADAY_INTERVAL = "5min"   # شمعة كل 5 دقائق
INTRADAY_TTL      = 300      # cache كل 5 دقائق
INTRADAY_MIN_CANDLES = 14    # أقل عدد شمعات لحساب RSI

DATA_DIR    = "data"
DAILY_DIR   = os.path.join(DATA_DIR, "daily_reports")
TONIGHT_DB  = os.path.join(DATA_DIR, "tonight_watchlist.db")
SIGNALS_DB  = os.path.join(DATA_DIR, "signals.db")

for d in [DATA_DIR, DAILY_DIR]:
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
    ("2190","سيسكو القابضة"),("4280","المملكة القابضة"),("2370","الشرق الأوسط للكابلات"),
    ("4310","مدينة المعرفة الاقتصادية"),("4320","الأندلس العقارية"),("2250","الاستثمار الصناعي"),
    ("4180","فتيحي القابضة"),("2100","وفرة للصناعة"),("4130","الباحة للاستثمار"),
    ("3002","أسمنت نجران"),("3003","أسمنت المدينة"),("3007","زهرة الواحة"),
    ("3010","الأسمنت العربية"),("4150","الرياض للتعمير"),("4051","باعظيم التجارية"),
    ("4190","جرير للتسويق"),
]

STOCKS_SCAN = [
    ("1010","بنك الرياض"),("1080","العربي"),("1111","تداول السعودية القابضة"),
    ("1301","اتحاد مصانع الأسلاك"),("1302","بوان"),("1303","الصناعات الكهربائية"),
    ("1304","اليمامة للحديد"),("1320","الأنابيب الصلب"),
    ("2001","كيمائيات الميثانول"),("2030","المصافي العربية"),
    ("2080","الغاز والتصنيع الأهلية"),("2130","التنمية الصناعية"),
    ("2170","اللجين"),("2200","الأنابيب العربية"),("2230","الكيميائية السعودية"),
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
    # أسهم جديدة مهمة
    ("4146","جاز"),("4194","محطة البناء"),("7205","دي بي اس"),
    ("2382","أديس القابضة"),("1322","أماك"),("2050","صافولا"),
    ("1212","أسترا الصناعية"),("1211","معادن"),("1182","أملاك العالمية"),
    ("2020","سابك للمغذيات"),("1201","تكوين المتطورة"),
    ("7020","موبايلي"),("7030","زين السعودية"),
    ("4110","المملكة القابضة"),("1832","صدر اللوجستية"),
    ("2030","ساركو"),("1320","أنابيب الصلب"),("1321","أنابيب الشرق"),
]

# ============================================================
# 3. الصفحة والمصادقة
# ============================================================

st.set_page_config(
    page_title="داشبورد التداول - test11",
    layout="wide",
    page_icon="📊",
    initial_sidebar_state="collapsed"
)

API_KEY = st.secrets["API_KEY"]

for key, val in {
    "auth": False, "paper_mode": False,
    "daily_pnl": 0.0, "bot_active": True,
    "signal_log": [], "tonight_list": [],
    "intraday_supported": None,
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

if not st.session_state.auth:
    st.markdown("<h2 style='text-align:center;margin-top:100px'>📊 داشبورد التداول — test11</h2>", unsafe_allow_html=True)
    _, col_b, _ = st.columns([1, 1, 1])
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
# 4. جلب البيانات — مع إضافة Intraday
# ============================================================

@st.cache_data(ttl=30)
def get_all_quotes():
    all_syms = [s[0] for s in STOCKS_ACTIVE + STOCKS_SCAN]
    # إزالة التكرار
    seen, unique = set(), []
    for s in all_syms:
        if s not in seen:
            seen.add(s)
            unique.append(s)
    quotes_dict, errors = {}, []
    for i in range(0, len(unique), 5):
        batch = unique[i:i+5]
        try:
            result = client.quotes(batch)
            for q in result.quotes:
                quotes_dict[q.symbol] = q
        except Exception as e:
            err_msg = str(e)
            if "403" in err_msg:
                st.error("❌ API Key منتهي (403).")
                st.stop()
            errors.append(f"batch {i}: {err_msg[:50]}")
    return quotes_dict, errors

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
    except:
        return [], [], [], []

@st.cache_data(ttl=INTRADAY_TTL)
def get_intraday(sym):
    """
    الطبقة 3 — يجلب بيانات كل 5 دقائق لليوم الحالي
    لو API لا يدعم intraday يرجع قائمة فارغة
    """
    try:
        h = client.intraday(sym, interval=INTRADAY_INTERVAL)
        closes, highs, lows, volumes, times = [], [], [], [], []
        for item in h.data:
            if item.close and item.close > 0:
                closes.append(float(item.close))
                highs.append(float(item.high or item.close))
                lows.append(float(item.low or item.close))
                volumes.append(float(item.volume or 0))
                times.append(getattr(item, "time", ""))
        return closes, highs, lows, volumes, times, True
    except Exception as e:
        # intraday غير مدعوم أو خطأ
        return [], [], [], [], [], False

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
# 5. دالة دمج البيانات — الطبقة 3
# ============================================================

def get_best_data(sym, quotes_dict):
    """
    يجلب أفضل بيانات متاحة:
    1. لو intraday متاح → يستخدمه (الطبقة 3)
    2. لو لا → يستخدم التاريخي اليومي (test10 عادي)
    يرجع: closes, highs, lows, volumes, is_intraday
    """
    # جرّب intraday أولاً
    i_closes, i_highs, i_lows, i_vols, i_times, supported = get_intraday(sym)

    if supported and len(i_closes) >= INTRADAY_MIN_CANDLES:
        # ✅ الطبقة 3 متاحة
        if st.session_state.intraday_supported is None:
            st.session_state.intraday_supported = True
        return i_closes, i_highs, i_lows, i_vols, True, len(i_closes)

    # ❌ الطبقة 3 غير متاحة — استخدم التاريخي
    if st.session_state.intraday_supported is None:
        st.session_state.intraday_supported = False
    h_closes, h_highs, h_lows, h_vols = get_historical(sym)
    return h_closes, h_highs, h_lows, h_vols, False, len(h_closes)

# ============================================================
# 6. المؤشرات الفنية (نفس test10 بالضبط)
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
    ag = sum(gains[:period]) / period
    al = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        ag = (ag*(period-1) + gains[i]) / period
        al = (al*(period-1) + losses[i]) / period
    if al == 0: return 100.0
    return round(100 - (100 / (1 + ag/al)), 1)

def calc_rsi_direction(closes, period=14, lookback=5):
    if len(closes) < period + lookback + 1:
        return 0.0
    return round(calc_rsi(closes, period) - calc_rsi(closes[:-lookback], period), 1)

def calc_macd(closes):
    if len(closes) < 35:
        return 0.0, 0.0, 0.0
    e12 = calc_ema_series(closes, 12)
    e26 = calc_ema_series(closes, 26)
    ml  = min(len(e12), len(e26))
    macd_line = [e12[-(ml-i)] - e26[-(ml-i)] for i in range(ml)]
    if len(macd_line) < 9:
        return 0.0, 0.0, 0.0
    sig = calc_ema_series(macd_line, 9)
    return round(macd_line[-1],3), round(sig[-1],3), round(macd_line[-1]-sig[-1],3)

def calc_macd_direction(closes, lookback=3):
    if len(closes) < 38 + lookback:
        return 0.0
    _, _, h1 = calc_macd(closes)
    _, _, h2 = calc_macd(closes[:-lookback])
    return round(h1 - h2, 4)

def calc_ma(closes, period):
    if len(closes) < period:
        return 0.0
    return round(sum(closes[-period:]) / period, 2)

def calc_bollinger(closes, period=20):
    if len(closes) < period:
        return 0.0, 0.0, 0.0
    r  = closes[-period:]
    ma = sum(r) / period
    std = (sum((x-ma)**2 for x in r)/period)**0.5
    return round(ma+2*std,2), round(ma,2), round(ma-2*std,2)

def calc_atr(highs, lows, closes, period=14):
    if len(closes) < period + 1:
        return 0.0
    trs = [max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
           for i in range(1, len(closes))]
    if len(trs) < period:
        return 0.0
    return round(sum(trs[-period:]) / period, 3)

def calc_volume(volumes, period=20):
    if len(volumes) < period:
        return False, False, 0.0, 0.0
    avg20 = sum(volumes[-period:]) / period
    avg5  = sum(volumes[-5:]) / 5 if len(volumes) >= 5 else avg20
    ratio = round(avg5/avg20, 1) if avg20 > 0 else 0.0
    return ratio >= 1.5, ratio >= 2.0, ratio, avg20

def calc_closing_strength(closes, highs, lows):
    if not closes: return 0.0
    h, l, c = highs[-1], lows[-1], closes[-1]
    if h == l: return 0.5
    return round((c-l)/(h-l), 2)

def calc_liquidity_score(vol_ratio, avg_vol):
    if vol_ratio >= 3:     s = 9
    elif vol_ratio >= 2:   s = 8
    elif vol_ratio >= 1.5: s = 7
    elif vol_ratio >= 1.2: s = 6
    elif vol_ratio >= 1.0: s = 5
    elif vol_ratio >= 0.7: s = 4
    elif vol_ratio >= 0.5: s = 3
    else:                  s = 2
    if avg_vol > 5_000_000:  s = min(s+1, 10)
    elif avg_vol < 500_000:  s = max(s-1, 1)
    return s

def calc_slippage(liq):
    if liq >= 8:   return 0.0005, "عالية جداً ✅"
    elif liq >= 6: return 0.0015, "عالية 🟡"
    elif liq >= 4: return 0.003,  "متوسطة ⚠️"
    else:          return 0.005,  "منخفضة 🔴"

# ============================================================
# 7. نظام النقاط — يعمل على أي بيانات (يومية أو intraday)
# ============================================================

def get_strength(change_pct, rsi, rsi_dir, macd, macd_signal, macd_hist,
                 macd_dir, ma20, ma50, price, vol_high, vol_very_high,
                 vol_ratio, tasi_change, bb_lower, bb_upper, is_intraday=False):
    score, reasons = 0, []

    # RSI
    if rsi < 30:
        score += 30; reasons.append(f"RSI تشبع بيع ({rsi}) 🔥")
    elif rsi < 40:
        score += 22; reasons.append(f"RSI منطقة شراء ({rsi})")
    elif 40 <= rsi < 55:
        score += 12; reasons.append(f"RSI متوازن ({rsi})")
    elif rsi >= 70:
        score -= 15; reasons.append(f"⚠️ RSI ذروة ({rsi})")

    if rsi_dir > 10:   score += 8;  reasons.append(f"RSI زخم قوي")
    elif rsi_dir > 5:  score += 4;  reasons.append(f"RSI صاعد")
    elif rsi_dir < -5: score -= 5;  reasons.append(f"RSI نازل")

    # MACD
    if macd > 0 and macd_hist > 0 and macd > macd_signal and macd_dir > 0:
        score += 25; reasons.append("MACD إشارة شراء قوية 💪")
    elif macd > macd_signal and macd_hist > 0:
        score += 15; reasons.append("MACD تقاطع صاعد")
    elif macd > 0:
        score += 6
    if macd_dir < 0:
        score -= 8; reasons.append("⚠️ MACD زخم ضعيف")

    # المتوسطات (فقط لو بيانات يومية — intraday MA لا معنى له)
    if not is_intraday:
        if ma50 > 0 and price > ma50:
            score += 10; reasons.append("فوق MA50 ✅")
        if ma20 > 0 and price > ma20:
            score += 8;  reasons.append("فوق MA20")
        if ma20 > 0 and ma50 > 0 and ma20 > ma50:
            score += 7;  reasons.append("Golden Cross ⭐")
    else:
        # intraday: استخدم EMA9 بدل MA
        if ma20 > 0 and price > ma20:
            score += 10; reasons.append("فوق EMA9 intraday ✅")

    # الحجم
    if vol_very_high:
        score += 20; reasons.append(f"حجم استثنائي ×{vol_ratio} 🚀")
    elif vol_high:
        score += 12; reasons.append(f"حجم مرتفع ×{vol_ratio}")
    elif vol_ratio >= 1.2:
        score += 6;  reasons.append(f"حجم فوق المتوسط ×{vol_ratio}")

    # TASI
    if tasi_change >= 0.5:
        score += 5;  reasons.append("السوق صاعد 📈")
    elif tasi_change < -2.0:
        score -= 20; reasons.append("🚨 السوق هابط بقوة")
    elif tasi_change < -1.0:
        score -= 10; reasons.append("⚠️ السوق ضعيف")
    elif tasi_change < 0:
        score -= 3

    # Bollinger
    if bb_lower > 0 and price <= bb_lower * 1.01:
        score += 5;  reasons.append("عند الحد الأدنى BB")
    elif bb_upper > 0 and price >= bb_upper * 0.99:
        score -= 5;  reasons.append("⚠️ عند الحد الأعلى BB")

    # تغيير اليوم
    if change_pct >= 2.0:
        score += 10; reasons.append(f"زخم قوي +{change_pct}%")
    elif change_pct >= 1.0:
        score += 5;  reasons.append(f"زخم إيجابي +{change_pct}%")
    elif change_pct < -1.5:
        score -= 12; reasons.append(f"⚠️ هابط {change_pct}%")
    elif change_pct < -0.5:
        score -= 5

    # مكافأة إضافية لو intraday مؤكد
    if is_intraday:
        reasons.append("📡 بيانات intraday حقيقية")

    return min(max(score, 0), 100), reasons

def calc_confidence(score, rsi_dir, macd_dir, vol_high, vol_very, tasi_change):
    if score <= 0: return 0
    bonus = 0
    if rsi_dir > 10:      bonus += 12
    elif rsi_dir > 5:     bonus += 6
    if macd_dir > 0:      bonus += 10
    if vol_very:          bonus += 8
    elif vol_high:        bonus += 4
    if tasi_change < -1.0:  bonus -= 15
    elif tasi_change < -0.5: bonus -= 8
    return min(max(round((score*0.70)+bonus), 0), 100)

def get_signal(score, rsi, confidence, price, ma50, change_pct,
               liq_score, vol_ratio, atr, is_intraday=False):
    in_downtrend = (not is_intraday) and ma50 > 0 and price < ma50 * 0.95
    atr_pct      = atr/price if price > 0 else 0
    atr_small    = atr_pct < MIN_ATR_PCT
    low_vol      = vol_ratio < MIN_VOL_RATIO
    low_liq      = liq_score < MIN_LIQ
    falling      = change_pct < MAX_CHANGE_NEG

    if any([in_downtrend, atr_small, low_vol, low_liq, falling]):
        if score < 35 or rsi > 75:
            return "SELL 🔴", "sell"
        return "WAIT 🟡", "wait"

    if score >= MIN_SCORE_STR and rsi < 70 and confidence >= MIN_CONF_STR:
        return "BUY 🟢", "strong"
    if score >= MIN_SCORE and rsi < 65 and confidence >= MIN_CONFIDENCE:
        return "BUY 🟢", "normal"
    if score < 35 or rsi > 75:
        return "SELL 🔴", "sell"
    return "WAIT 🟡", "wait"

def calc_stars(score):
    if score >= 80:   return "⭐⭐⭐⭐⭐"
    elif score >= 65: return "⭐⭐⭐⭐"
    elif score >= 50: return "⭐⭐⭐"
    elif score >= 35: return "⭐⭐"
    else:             return "⭐"

# ============================================================
# 8. الأهداف R/R 1:2
# ============================================================

def calc_targets_and_sl(entry, atr, confidence=50):
    risk    = round(atr * ATR_RISK_MULT, 3)
    stop    = round(entry - risk, 2)
    t1      = round(entry + risk * ATR_T1_MULT, 2)
    t2      = round(entry + risk * ATR_T2_MULT, 2)
    t1_pct  = round((t1-entry)/entry*100, 2) if entry > 0 else 0
    t2_pct  = round((t2-entry)/entry*100, 2) if entry > 0 else 0
    if confidence >= 80:   label = "توقع قوي 🔥"
    elif confidence >= 60: label = "توقع متوسط 📊"
    else:                  label = "توقع محافظ 🛡️"
    return t1, t2, stop, t1_pct, t2_pct, label

def calc_position_size(entry, stop):
    risk = entry - stop
    if risk <= 0: return 0, 0
    shares = int(min(CAPITAL_DAILY, MAX_TRADE_DAILY) / entry)
    return shares, round(shares*entry, 2)

# ============================================================
# 9. قاعدة البيانات
# ============================================================

def get_db_conn():
    conn = sqlite3.connect(SIGNALS_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_signals_db():
    with get_db_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                signal_id       INTEGER PRIMARY KEY AUTOINCREMENT,
                date            TEXT, time TEXT, symbol TEXT, name TEXT,
                signal_type     TEXT, price REAL, entry_price REAL,
                target1 REAL, target2 REAL, stop_loss REAL,
                confidence REAL, rsi REAL, macd REAL,
                volume_ratio REAL, slippage REAL, liquidity_score REAL,
                result_24h TEXT DEFAULT '', profit_loss TEXT DEFAULT '',
                is_breakout INTEGER DEFAULT 0,
                is_intraday INTEGER DEFAULT 0
            )
        """)
        conn.commit()

init_signals_db()

def signal_already_saved_today(sym):
    today = now_riyadh().strftime("%Y-%m-%d")
    with get_db_conn() as conn:
        row = conn.execute(
            "SELECT 1 FROM signals WHERE symbol=? AND date=? LIMIT 1", (sym,today)
        ).fetchone()
    return row is not None

def save_signal(sym, name, signal_type, price, entry, t1, t2, stop,
                confidence, rsi, macd, vol, slip, liq,
                is_breakout=0, is_intraday=0):
    now = now_riyadh()
    with get_db_conn() as conn:
        conn.execute("""
            INSERT INTO signals
            (date,time,symbol,name,signal_type,price,entry_price,target1,target2,
             stop_loss,confidence,rsi,macd,volume_ratio,slippage,liquidity_score,
             result_24h,profit_loss,is_breakout,is_intraday)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'','',?,?)
        """, (now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"),
              sym, name, signal_type, price, entry, t1, t2,
              stop, confidence, rsi, macd, vol, slip, liq,
              is_breakout, is_intraday))
        conn.commit()
    st.session_state.signal_log.append({
        "الوقت": now.strftime("%H:%M"), "الرمز": sym, "الاسم": name,
        "الإشارة": signal_type, "السعر": price,
        "هدف1": t1, "هدف2": t2, "Stop": stop,
        "الثقة": f"{confidence}%",
        "Intraday": "📡" if is_intraday else "",
        "Breakout": "🚨" if is_breakout else ""
    })

def load_today_signals():
    today = now_riyadh().strftime("%Y-%m-%d")
    with get_db_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM signals WHERE date=? ORDER BY signal_id", (today,)
        ).fetchall()
    return [dict(r) for r in rows]

# ============================================================
# 10. التقييم المستمر
# ============================================================

def eval_signals_continuous(quotes_dict):
    today = now_riyadh().strftime("%Y-%m-%d")
    try:
        with get_db_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM signals WHERE date=? AND result_24h=''", (today,)
            ).fetchall()
            for row in rows:
                row   = dict(row)
                sym   = row.get("symbol")
                q     = quotes_dict.get(sym)
                if not q: continue
                cur   = float(getattr(q,"price",0) or 0)
                hi    = float(getattr(q,"high", 0) or cur)
                lo    = float(getattr(q,"low",  0) or cur)
                t1    = float(row.get("target1",   0) or 0)
                t2    = float(row.get("target2",   0) or 0)
                stop  = float(row.get("stop_loss", 0) or 0)
                entry = float(row.get("entry_price",0) or 0)
                if hi >= t2:
                    result = "✅ وصل الهدف 2"
                    pl = f"+{round((t2-entry)/entry*100,2)}%"
                elif hi >= t1:
                    result = "🟡 وصل الهدف 1"
                    pl = f"+{round((t1-entry)/entry*100,2)}%"
                elif lo <= stop:
                    result = "❌ وصل Stop Loss"
                    pl = f"-{round((entry-stop)/entry*100,2)}%"
                else:
                    chg = round((cur-entry)/entry*100, 2)
                    result = "⏳ لم يصل بعد"
                    pl = f"{chg:+.2f}%"
                conn.execute(
                    "UPDATE signals SET result_24h=?, profit_loss=? WHERE signal_id=?",
                    (result, pl, row["signal_id"])
                )
            conn.commit()
    except: pass

# ============================================================
# 11. قائمة الغد
# ============================================================

def get_tonight_db():
    conn = sqlite3.connect(TONIGHT_DB, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_tonight_db():
    with get_tonight_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT, symbol TEXT, name TEXT,
                close_price REAL, closing_strength REAL,
                vol_ratio REAL, rsi REAL, macd_dir REAL,
                ma50 REAL, atr REAL, score REAL,
                intraday_rsi REAL, intraday_candles INTEGER
            )
        """)
        conn.commit()

init_tonight_db()

def scan_tonight(stocks_list, quotes_dict):
    today   = now_riyadh().strftime("%Y-%m-%d")
    results = []
    for sym, name in stocks_list:
        try:
            closes, highs, lows, volumes = get_historical(sym)
            if len(closes) < 30: continue
            q = quotes_dict.get(sym)
            if not q: continue

            close_str = calc_closing_strength(closes, highs, lows)
            vol_high, vol_very, vol_ratio, avg_vol = calc_volume(volumes)
            rsi      = calc_rsi(closes)
            macd_dir = calc_macd_direction(closes)
            ma50     = calc_ma(closes, 50)
            atr      = calc_atr(highs, lows, closes)
            price    = float(closes[-1])

            # الطبقة 3: RSI intraday لقائمة الغد
            i_closes, _, _, _, _, i_supported = get_intraday(sym)
            intraday_rsi     = calc_rsi(i_closes) if len(i_closes) >= 14 else rsi
            intraday_candles = len(i_closes)

            if (close_str >= TONIGHT_CLOSE
                    and vol_ratio >= TONIGHT_VOL
                    and rsi < TONIGHT_RSI_MAX
                    and macd_dir > 0
                    and ma50 > 0 and price > ma50
                    and atr/price >= MIN_ATR_PCT
                    # الطبقة 3: RSI intraday لا يكون في الذروة
                    and intraday_rsi < 70):

                score_t = (
                    close_str * 40 +
                    min(vol_ratio/3, 1) * 30 +
                    (1 - rsi/100) * 20 +
                    (1 if macd_dir > 0 else 0) * 10
                )
                results.append({
                    "date": today, "symbol": sym, "name": name,
                    "close_price": price, "closing_strength": close_str,
                    "vol_ratio": vol_ratio, "rsi": rsi,
                    "macd_dir": macd_dir, "ma50": ma50, "atr": atr,
                    "score": round(score_t, 1),
                    "intraday_rsi": intraday_rsi,
                    "intraday_candles": intraday_candles
                })
        except: continue

    if results:
        with get_tonight_db() as conn:
            conn.execute("DELETE FROM watchlist WHERE date=?", (today,))
            for r in results:
                conn.execute("""
                    INSERT INTO watchlist
                    (date,symbol,name,close_price,closing_strength,vol_ratio,
                     rsi,macd_dir,ma50,atr,score,intraday_rsi,intraday_candles)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (r["date"],r["symbol"],r["name"],r["close_price"],
                      r["closing_strength"],r["vol_ratio"],r["rsi"],
                      r["macd_dir"],r["ma50"],r["atr"],r["score"],
                      r["intraday_rsi"],r["intraday_candles"]))
            conn.commit()
    return sorted(results, key=lambda x: x["score"], reverse=True)

def load_tonight_list():
    today = now_riyadh().strftime("%Y-%m-%d")
    with get_tonight_db() as conn:
        rows = conn.execute(
            "SELECT * FROM watchlist WHERE date=? ORDER BY score DESC", (today,)
        ).fetchall()
    return [dict(r) for r in rows]

# ============================================================
# 12. Breakout اللحظي
# ============================================================

def check_breakout(sym, q, closes, volumes, now_mins, is_intraday=False):
    try:
        change_pct   = float(getattr(q, "change_percent", 0) or 0)
        today_volume = float(getattr(q, "volume", 0) or 0)
        if len(volumes) < 20: return False, 0.0

        if is_intraday:
            # لو intraday — نسبة الحجم الأخيرة شمعة vs متوسط الشمعات
            avg_vol     = sum(volumes[:-1]) / max(len(volumes)-1, 1)
            last_vol    = volumes[-1]
            intra_ratio = round(last_vol/avg_vol, 1) if avg_vol > 0 else 0.0
        else:
            avg_vol     = sum(volumes[-20:]) / 20
            time_elapsed = max(now_mins - MARKET_OPEN, 1)
            time_factor  = time_elapsed / 360
            expected_vol = avg_vol * time_factor
            intra_ratio  = round(today_volume/expected_vol, 1) if expected_vol > 0 else 0.0

        is_bo = (
            change_pct >= BREAKOUT_CHANGE
            and intra_ratio >= BREAKOUT_VOL
            and float(getattr(q,"price",0) or 0) > (closes[-1]*1.003 if closes else 0)
        )
        return is_bo, intra_ratio
    except:
        return False, 0.0

# ============================================================
# 13. Pre-market scanner
# ============================================================

def scan_premarket(tonight_syms, quotes_dict):
    results = []
    for item in tonight_syms:
        sym = item["symbol"]
        q   = quotes_dict.get(sym)
        if not q: continue
        try:
            cur  = float(getattr(q,"price",0) or 0)
            prev = float(item["close_price"])
            gap  = (cur-prev)/prev*100 if prev > 0 else 0
            if gap >= 0.3:
                results.append({**item, "gap_up": round(gap,2)})
        except: continue
    return sorted(results, key=lambda x: x.get("gap_up",0), reverse=True)

# ============================================================
# 14. تحليل الأسهم — الطبقة 3 مدمجة
# ============================================================

def analyze_stocks(stocks_list, quotes_dict, tasi_change, now_mins, tonight_syms):
    data, failed = [], []
    tonight_set  = {x["symbol"] for x in tonight_syms}

    for sym, name in stocks_list:
        try:
            q = quotes_dict.get(sym)
            if not q or not hasattr(q,"price") or not q.price:
                failed.append(sym); continue

            # ── الطبقة 3: أفضل بيانات متاحة ──
            closes, highs, lows, volumes, is_intraday, n_candles = get_best_data(sym, quotes_dict)

            if len(closes) < (INTRADAY_MIN_CANDLES if is_intraday else 30):
                failed.append(sym); continue

            price      = float(q.price)
            change_pct = float(getattr(q,"change_percent",0) or 0)

            # المؤشرات — نفس الدوال لكن على بيانات مختلفة
            rsi     = calc_rsi(closes)
            rsi_dir = calc_rsi_direction(closes)
            macd, macd_sig, macd_hist = calc_macd(closes)
            macd_dir = calc_macd_direction(closes)

            # MA: فقط لو بيانات يومية
            if is_intraday:
                ma20 = calc_ma(closes, 9)   # EMA9 بدل MA20
                ma50 = 0.0                   # لا معنى له intraday
            else:
                ma20 = calc_ma(closes, 20)
                ma50 = calc_ma(closes, 50)

            bb_up, _, bb_low = calc_bollinger(closes)
            atr = calc_atr(highs, lows, closes)

            # الحجم — intraday: حجم الشمعات | يومي: حجم أيام
            vol_high, vol_very, vol_ratio, avg_vol = calc_volume(volumes)

            # لو intraday: استخدم حجم اليوم الفعلي
            if is_intraday:
                today_vol = float(getattr(q,"volume",0) or 0)
                avg_hist  = sum(volumes) / max(len(volumes),1)
                vol_ratio = round(today_vol/avg_hist, 1) if avg_hist > 0 else vol_ratio
                vol_high  = vol_ratio >= 1.5
                vol_very  = vol_ratio >= 2.0

            liq_score = calc_liquidity_score(vol_ratio, avg_vol)
            slip_pct, slip_label = calc_slippage(liq_score)
            entry = round(price*(1+slip_pct), 2)

            score, reasons = get_strength(
                change_pct, rsi, rsi_dir, macd, macd_sig, macd_hist,
                macd_dir, ma20, ma50, price, vol_high, vol_very,
                vol_ratio, tasi_change, bb_low, bb_up, is_intraday
            )
            confidence = calc_confidence(score, rsi_dir, macd_dir,
                                         vol_high, vol_very, tasi_change)
            signal, sig_type = get_signal(
                score, rsi, confidence, price, ma50,
                change_pct, liq_score, vol_ratio, atr, is_intraday
            )
            stars = calc_stars(score)
            t1, t2, stop, t1_pct, t2_pct, model_label = calc_targets_and_sl(entry, atr, confidence)
            shares, amount = calc_position_size(entry, stop)
            is_bo, intra_ratio = check_breakout(sym, q, closes, volumes, now_mins, is_intraday)
            in_tonight = sym in tonight_set
            rsi_warn = "🔴 احذر ذروة!" if rsi > 70 else ("🟡 اقترب" if rsi > 65 else "")

            # تسجيل تلقائي
            signals_active = now_mins >= MARKET_SIGNALS and now_mins < MARKET_CLOSE
            if signals_active and st.session_state.bot_active:
                if sig_type in ["strong","normal"] and not signal_already_saved_today(sym):
                    save_signal(sym, name, signal, price, entry, t1, t2, stop,
                                confidence, rsi, macd, vol_ratio, slip_pct, liq_score,
                                0, int(is_intraday))
                elif is_bo and not signal_already_saved_today(sym):
                    save_signal(sym, name, "BREAKOUT 🚨", price, entry, t1, t2, stop,
                                confidence, rsi, macd, vol_ratio, slip_pct, liq_score,
                                1, int(is_intraday))

            data_layer = "📡 Intraday" if is_intraday else "📅 يومي"

            data.append({
                "الرمز": sym, "الاسم": name,
                "السعر": price, "التغيير%": round(change_pct,2),
                "النجوم": stars, "الإشارة": signal,
                "هدف1": t1, "هدف%1": f"+{t1_pct}%",
                "هدف2": t2, "هدف%2": f"+{t2_pct}%",
                "توقع النموذج": model_label,
                "Stop Loss": stop, "سعر الدخول": entry,
                "الثقة%": confidence, "RSI": rsi,
                "تحذير RSI": rsi_warn,
                "MACD": macd,
                "MACD زخم": "صاعد ✅" if macd_dir > 0 else "نازل ⚠️",
                "MA50": ma50, "ATR": atr,
                "حجم×": vol_ratio, "حجم لحظي×": intra_ratio,
                "السيولة": f"{liq_score}/10", "انزلاق": slip_label,
                "السوق يقبل": "✅ نعم" if liq_score >= 4 else "❌ لا",
                "الأسهم": shares, "المبلغ": amount,
                "القوة%": score,
                "طبقة البيانات": data_layer,
                "عدد الشمعات": n_candles,
                "Breakout": "🚨 نعم" if is_bo else "",
                "في قائمة الغد": "🌙 نعم" if in_tonight else "",
                "_signal_type": sig_type, "_confidence": confidence,
                "_liq_score": liq_score, "_entry": entry,
                "_t1": t1, "_t2": t2, "_stop": stop,
                "_rsi": rsi, "_macd": macd, "_vol": vol_ratio,
                "_sym": sym, "_name": name, "_slip": slip_pct,
                "_is_bo": is_bo, "_is_intraday": is_intraday,
                "_reasons": " | ".join(reasons),
            })
        except Exception as e:
            failed.append(f"{sym}({str(e)[:25]})")

    return data, failed

# ============================================================
# 15. CSS
# ============================================================

st.markdown("""
<style>
    .stApp { background-color: #f5f6fa; }
    .signal-card {
        padding:16px; border-radius:14px; margin-bottom:12px;
        border:1.5px solid #dde1ea; box-shadow:0 2px 8px rgba(0,0,0,0.07);
        background:#ffffff;
    }
    .buy-card      { background:#f0faf2; border-color:#4caf50; }
    .breakout-card { background:#fff8e1; border-color:#f0b429; border-width:2px; }
    .intraday-card { background:#e8f4fd; border-color:#1565c0; border-width:2px; }
    .wait-card     { background:#fffdf0; border-color:#f0b429; }
    .sell-card     { background:#fff5f5; border-color:#e53935; }
    .metric-row { display:flex; gap:6px; flex-wrap:wrap; margin:6px 0; }
    .badge { padding:3px 10px; border-radius:20px; font-size:11px; font-weight:700; }
    .badge-green  { background:#e6f4ea; color:#2e7d32; border:1px solid #a5d6a7; }
    .badge-yellow { background:#fff8e1; color:#f57f17; border:1px solid #ffe082; }
    .badge-red    { background:#ffebee; color:#c62828; border:1px solid #ef9a9a; }
    .badge-blue   { background:#e3f2fd; color:#1565c0; border:1px solid #90caf9; }
    .badge-purple { background:#ede7f6; color:#4527a0; border:1px solid #b39ddb; }
    .stButton > button {
        border-radius:8px; font-weight:600;
        border:1.5px solid #dde1ea; background:#ffffff; color:#1a1a2e;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 16. شريط الأدوات
# ============================================================

st_autorefresh(interval=30_000, key="autorefresh")

now      = now_riyadh()
now_mins = now.hour*60 + now.minute
weekday  = now.weekday()
is_workday_sa  = weekday in [6,0,1,2,3]
market_open    = is_workday_sa and MARKET_OPEN <= now_mins < MARKET_CLOSE
signals_active = is_workday_sa and now_mins >= MARKET_SIGNALS and now_mins < MARKET_CLOSE
pre_open       = is_workday_sa and MARKET_PRE_OPEN <= now_mins < MARKET_OPEN
first_15       = is_workday_sa and MARKET_OPEN <= now_mins < MARKET_FIRST15
after_close    = is_workday_sa and now_mins >= REPORT_TIME

market, _ = get_market()
tasi_change  = float(getattr(market,"index_change_percent",0) or 0) if market else 0.0
tasi_value   = float(getattr(market,"index_value",0) or 0) if market else 0.0
circuit_break = tasi_change < -3.0

st.title("📊 داشبورد التداول — test11 (الطبقة 3)")

# بنر حالة intraday
if st.session_state.intraday_supported is True:
    st.success("📡 **الطبقة 3 نشطة** — مؤشرات Intraday حقيقية كل 5 دقائق")
elif st.session_state.intraday_supported is False:
    st.warning("📅 **الطبقة 3 غير مدعومة** — يعمل على بيانات يومية (نفس test10)")
else:
    st.info("⏳ جاري التحقق من دعم Intraday...")

if st.session_state.paper_mode:
    st.warning("🧪 وضع المحاكاة")
if circuit_break:
    st.error(f"🚨 Circuit Breaker — TASI {tasi_change:.2f}%")
if not st.session_state.bot_active:
    st.error("🛑 البوت موقوف")
if first_15:
    st.info("⏰ أول 15 دقيقة — راقب Breakout بدقة")

c1,c2,c3,c4,c5 = st.columns(5)
with c1:
    if not is_workday_sa: st.warning("🔒 عطلة")
    elif market_open:     st.success("🟢 مفتوح")
    else:                 st.info("🔒 مغلق")
with c2:
    col = "normal" if tasi_change >= 0 else "inverse"
    st.metric("TASI", f"{tasi_value:,.0f}", f"{tasi_change:+.2f}%", delta_color=col)
with c3:
    ind = "📡 Intraday" if st.session_state.intraday_supported else "📅 يومي"
    st.metric("طبقة البيانات", ind)
with c4:
    pnl_color = "normal" if st.session_state.daily_pnl >= 0 else "inverse"
    st.metric("ربح/خسارة", f"{st.session_state.daily_pnl:+,.0f} ﷼", delta_color=pnl_color)
with c5:
    st.caption(f"🕐 {now.strftime('%H:%M:%S')}")

st.divider()

ctrl1,ctrl2,ctrl3,ctrl4 = st.columns(4)
with ctrl1:
    if st.button("🔄 تحديث"):
        st.cache_data.clear(); st.rerun()
with ctrl2:
    lbl = "🧪 إيقاف المحاكاة" if st.session_state.paper_mode else "🧪 تفعيل المحاكاة"
    if st.button(lbl):
        st.session_state.paper_mode = not st.session_state.paper_mode; st.rerun()
with ctrl3:
    lbl2 = "🛑 إيقاف البوت" if st.session_state.bot_active else "✅ تفعيل البوت"
    if st.button(lbl2):
        st.session_state.bot_active = not st.session_state.bot_active; st.rerun()
with ctrl4:
    st.caption(f"Intraday: {'✅' if st.session_state.intraday_supported else '❌'}")

# ============================================================
# 17. جلب وتحليل البيانات
# ============================================================

with st.spinner("جاري التحليل..."):
    quotes_dict, api_errors = get_all_quotes()
    tonight_list = load_tonight_list()
    premarket_list = scan_premarket(tonight_list, quotes_dict) if pre_open else []

    # إزالة تكرار من القوائم
    seen_syms = set()
    all_stocks_unique = []
    for s in STOCKS_ACTIVE + STOCKS_SCAN:
        if s[0] not in seen_syms:
            seen_syms.add(s[0])
            all_stocks_unique.append(s)

    data1, failed1 = analyze_stocks(STOCKS_ACTIVE, quotes_dict, tasi_change, now_mins, tonight_list)
    scan_only = [(s,n) for s,n in STOCKS_SCAN if s not in {x[0] for x in STOCKS_ACTIVE}]
    data2, failed2 = analyze_stocks(scan_only, quotes_dict, tasi_change, now_mins, tonight_list)
    all_data = data1 + data2

    if signals_active or after_close:
        eval_signals_continuous(quotes_dict)
    if after_close and all_data:
        scan_tonight(all_stocks_unique, quotes_dict)

# ============================================================
# 18. دالة عرض البطاقة
# ============================================================

def render_card(row, key_suffix=""):
    sig_type   = row.get("_signal_type","wait")
    is_bo      = row.get("_is_bo", False)
    is_intra   = row.get("_is_intraday", False)
    card_cls   = ("intraday-card" if is_intra and sig_type in ["strong","normal"]
                  else "breakout-card" if is_bo
                  else "buy-card" if sig_type in ["strong","normal"]
                  else "sell-card" if sig_type=="sell"
                  else "wait-card")
    liq_b = "green" if row.get("_liq_score",0)>=7 else "yellow" if row.get("_liq_score",0)>=4 else "red"
    intra_badge = "<span class='badge badge-purple'>📡 Intraday</span>" if is_intra else "<span class='badge badge-yellow'>📅 يومي</span>"
    bo_badge    = "<span class='badge badge-yellow'>🚨 Breakout</span>" if is_bo else ""
    to_badge    = "<span class='badge badge-blue'>🌙 قائمة الغد</span>" if row.get("في قائمة الغد") else ""

    st.markdown(f"""
    <div class='signal-card {card_cls}'>
        <div style='display:flex;justify-content:space-between;align-items:center'>
            <h4 style='margin:0'>{row['الرمز']} — {row['الاسم']}</h4>
            <span>{row['النجوم']}</span>
        </div>
        <div class='metric-row'>
            <span class='badge badge-{"green" if sig_type in ["strong","normal"] else "red" if sig_type=="sell" else "yellow"}'>{row['الإشارة']}</span>
            <span class='badge badge-blue'>ثقة {row['الثقة%']}%</span>
            <span class='badge badge-{liq_b}'>سيولة {row['السيولة']}</span>
            {intra_badge}{bo_badge}{to_badge}
        </div>
        <div style='font-size:13px;color:#222;line-height:1.9;margin-top:8px'>
            💰 <b>السعر:</b> {row['السعر']}
            &nbsp;|&nbsp; 📥 <b>الدخول:</b> {row['سعر الدخول']} ({row['انزلاق']})<br>
            🎯 <b>هدف1:</b> {row['هدف1']} <b style='color:#2e7d32'>({row['هدف%1']})</b>
            &nbsp;|&nbsp; 🎯 <b>هدف2:</b> {row['هدف2']} <b style='color:#1565c0'>({row['هدف%2']})</b><br>
            🛑 <b>Stop:</b> {row['Stop Loss']} &nbsp;|&nbsp; 🤖 {row['توقع النموذج']}<br>
            📊 <b>RSI:</b> {row['RSI']} {row.get('تحذير RSI','')}
            &nbsp;|&nbsp; 📈 <b>MACD:</b> {row['MACD']} {row['MACD زخم']}<br>
            📦 <b>حجم×:</b> {row['حجم×']} (لحظي: {row['حجم لحظي×']}×)
            &nbsp;|&nbsp; <b>القوة%:</b> {row['القوة%']}
            &nbsp;|&nbsp; 📦 {row['الأسهم']} سهم = <b>{row['المبلغ']:,.0f} ﷼</b><br>
            <small style='color:#888'>شمعات: {row['عدد الشمعات']} | {row['طبقة البيانات']}</small>
        </div>
        <details style='margin-top:6px;font-size:12px'>
            <summary>أسباب الإشارة 🔍</summary>
            <p style='color:#555'>{row.get('_reasons','')}</p>
        </details>
    </div>
    """, unsafe_allow_html=True)

    ca,cb = st.columns(2)
    with ca:
        if st.button(f"ادخل 🚀", key=f"e_{row['الرمز']}_{key_suffix}"):
            save_signal(row["_sym"],row["_name"],row["الإشارة"],
                        row["السعر"],row["_entry"],row["_t1"],row["_t2"],row["_stop"],
                        row["_confidence"],row["_rsi"],row["_macd"],row["_vol"],
                        row["_slip"],row["_liq_score"],
                        1 if is_bo else 0, int(is_intra))
            st.success("✅ تم!")
    with cb:
        if st.button(f"احسب 🧮", key=f"c_{row['الرمز']}_{key_suffix}"):
            st.session_state[f"sc_{row['الرمز']}"] = True
    if st.session_state.get(f"sc_{row['الرمز']}"):
        amt = st.number_input("المبلغ:", 1000, 200000, 20000, key=f"a_{row['الرمز']}_{key_suffix}")
        qty = int(amt/row["_entry"])
        st.info(f"الكمية: {qty} | هدف1: +{round(qty*(row['_t1']-row['_entry']),0):,.0f} ﷼ | هدف2: +{round(qty*(row['_t2']-row['_entry']),0):,.0f} ﷼ | خسارة: -{round(qty*(row['_entry']-row['_stop']),0):,.0f} ﷼")

# ============================================================
# 19. دالة عرض الجدول
# ============================================================

def render_table(data_list, key_prefix):
    if not data_list:
        st.warning("لا توجد بيانات"); return
    df = pd.DataFrame(data_list)
    cols = ["الرمز","الاسم","السعر","التغيير%","النجوم","الإشارة",
            "هدف1","هدف2","Stop Loss","سعر الدخول","الثقة%",
            "RSI","تحذير RSI","MACD زخم","حجم×","حجم لحظي×",
            "السيولة","القوة%","طبقة البيانات","عدد الشمعات",
            "Breakout","في قائمة الغد"]
    cols = [c for c in cols if c in df.columns]
    df_d = df[cols].copy()

    f1,f2,f3,f4,f5 = st.columns(5)
    with f1: sb = st.checkbox("BUY فقط", key=f"{key_prefix}_b")
    with f2: si = st.checkbox("📡 Intraday فقط", key=f"{key_prefix}_i")
    with f3: hr = st.checkbox("إخفاء ذروة RSI", key=f"{key_prefix}_r")
    with f4: so = st.selectbox("ترتيب:", ["القوة%","الثقة%","RSI","حجم×"], key=f"{key_prefix}_s")
    with f5: st.caption(f"إجمالي: {len(df_d)}")

    df_d = df_d.sort_values(so, ascending=(so=="RSI"))
    if sb: df_d = df_d[df_d["الإشارة"]=="BUY 🟢"]
    if si: df_d = df_d[df_d["طبقة البيانات"]=="📡 Intraday"]
    if hr and "تحذير RSI" in df_d.columns:
        df_d = df_d[df_d["تحذير RSI"]==""]

    st.dataframe(df_d, use_container_width=True, height=450,
        column_config={
            "القوة%": st.column_config.ProgressColumn("القوة%", min_value=0, max_value=100),
            "الثقة%": st.column_config.ProgressColumn("الثقة%", min_value=0, max_value=100),
        })

    buy_df = df[df["الإشارة"]=="BUY 🟢"]
    bo_df  = df[df["Breakout"]=="🚨 نعم"]
    intra_df = df[df["طبقة البيانات"]=="📡 Intraday"] if "طبقة البيانات" in df.columns else pd.DataFrame()
    if not buy_df.empty:
        st.success(f"🔔 BUY ({len(buy_df)}): {', '.join(buy_df['الرمز'].tolist()[:8])}")
    if not bo_df.empty:
        st.warning(f"🚨 Breakout ({len(bo_df)}): {', '.join(bo_df['الرمز'].tolist()[:8])}")
    if not intra_df.empty:
        st.info(f"📡 Intraday ({len(intra_df)} سهم)")

# ============================================================
# 20. التابات
# ============================================================

tab1,tab2,tab3,tab4,tab5,tab6,tab7,tab8,tab9,tab10 = st.tabs([
    "📈 السوق", "⚡ أفضل الفرص", "🚨 Breakout",
    "🌙 قائمة الغد", "📡 حالة Intraday",
    "🔍 الأسهم النشطة", "🔎 المسح الشامل",
    "📋 سجل اليوم", "📊 التقارير",
    "🧪 Scan into test11",
])

# ─── تاب 1: السوق ───
with tab1:
    st.subheader("📈 حركة السوق")
    g,l,v,_ = get_movers()
    c1,c2,c3 = st.columns(3)
    with c1:
        st.markdown("**🟢 الصاعدون**")
        try: st.dataframe(pd.DataFrame([{"الرمز":x.symbol,"الاسم":x.name,"السعر":x.price,"التغيير%":x.change_percent} for x in g.movers]), use_container_width=True)
        except: st.info("—")
    with c2:
        st.markdown("**🔴 الهابطون**")
        try: st.dataframe(pd.DataFrame([{"الرمز":x.symbol,"الاسم":x.name,"السعر":x.price,"التغيير%":x.change_percent} for x in l.movers]), use_container_width=True)
        except: st.info("—")
    with c3:
        st.markdown("**💹 الأكثر تداولاً**")
        try: st.dataframe(pd.DataFrame([{"الرمز":x.symbol,"الاسم":x.name,"الحجم":x.volume} for x in v.movers]), use_container_width=True)
        except: st.info("—")
    if tasi_change < -3: st.error("🚨 السوق ضعيف جداً")
    elif tasi_change < 0: st.warning("⚠️ السوق في هبوط")
    else: st.success("✅ السوق إيجابي")

# ─── تاب 2: أفضل الفرص ───
with tab2:
    st.subheader("⚡ أفضل الفرص — BUY")
    if not signals_active: st.warning("⏳ الإشارات تبدأ 10:15")
    df_all = pd.DataFrame(all_data) if all_data else pd.DataFrame()
    if not df_all.empty:
        df_buy = df_all[df_all["الإشارة"]=="BUY 🟢"].sort_values("الثقة%", ascending=False)
        if not df_buy.empty:
            st.markdown("### 🏆 أقوى 3 فرص")
            top3 = df_buy.head(3)
            cols = st.columns(3)
            for i,(_,row) in enumerate(top3.iterrows()):
                with cols[i]: render_card(row.to_dict(), f"b{i}")
            st.divider()
            show_c = ["الرمز","الاسم","السعر","التغيير%","النجوم","الإشارة",
                      "هدف1","هدف2","Stop Loss","الثقة%","RSI","حجم×",
                      "طبقة البيانات","القوة%"]
            show_c = [c for c in show_c if c in df_buy.columns]
            st.dataframe(df_buy[show_c].head(20), use_container_width=True,
                column_config={
                    "القوة%": st.column_config.ProgressColumn("القوة%", min_value=0, max_value=100),
                    "الثقة%": st.column_config.ProgressColumn("الثقة%", min_value=0, max_value=100),
                })
        else:
            st.info("لا توجد إشارات BUY حالياً ✅")

# ─── تاب 3: Breakout ───
with tab3:
    st.subheader("🚨 Breakout اللحظي")
    if first_15: st.warning("⏰ أول 15 دقيقة — أقوى وقت للـ Breakout")
    if all_data:
        df_bo = pd.DataFrame(all_data)
        df_bo = df_bo[df_bo["Breakout"]=="🚨 نعم"].sort_values("حجم لحظي×", ascending=False)
        if not df_bo.empty:
            st.success(f"🚨 {len(df_bo)} إشارة Breakout الآن")
            cols = st.columns(min(3,len(df_bo)))
            for i,(_,row) in enumerate(df_bo.iterrows()):
                with cols[i%3]: render_card(row.to_dict(), f"bo{i}")
        else:
            st.info("لا توجد Breakout الآن")

# ─── تاب 4: قائمة الغد ───
with tab4:
    st.subheader("🌙 قائمة مرشحي الغد")
    if pre_open and premarket_list:
        st.success(f"🌅 Pre-market — {len(premarket_list)} سهم Gap Up")
        st.dataframe(pd.DataFrame(premarket_list)[["symbol","name","close_price","gap_up","vol_ratio","rsi"]], use_container_width=True)
        st.divider()
    tonight_data = load_tonight_list()
    if tonight_data:
        df_tn = pd.DataFrame(tonight_data)
        st.success(f"📋 {len(tonight_data)} سهم في قائمة الغد")
        show_cols_tn = ["symbol","name","close_price","closing_strength","vol_ratio","rsi","intraday_rsi","intraday_candles","score"]
        show_cols_tn = [c for c in show_cols_tn if c in df_tn.columns]
        st.dataframe(df_tn[show_cols_tn].head(15), use_container_width=True,
            column_config={
                "score": st.column_config.ProgressColumn("score", min_value=0, max_value=100),
                "intraday_rsi": st.column_config.NumberColumn("RSI Intraday", format="%.1f"),
            })
    else:
        st.info("القائمة تُبنى بعد 15:15" if not after_close else "جاري البناء...")

# ─── تاب 5: حالة Intraday (جديد) ───
with tab5:
    st.subheader("📡 حالة الطبقة 3 — Intraday")

    if st.session_state.intraday_supported is True:
        st.success("✅ API يدعم Intraday — الطبقة 3 نشطة")
        st.markdown("""
        **ما يعمل الآن:**
        - RSI محسوب على شمعات 5 دقائق حقيقية
        - MACD يتغير مع كل شمعة
        - ATR يعكس تذبذب اليوم الفعلي
        - Breakout مبني على حجم الشمعات لا حجم اليوم الكلي
        - قائمة الغد تستخدم RSI intraday للتصفية
        """)
        if all_data:
            df_intra = pd.DataFrame(all_data)
            if "طبقة البيانات" in df_intra.columns:
                intra_count = len(df_intra[df_intra["طبقة البيانات"]=="📡 Intraday"])
                daily_count = len(df_intra[df_intra["طبقة البيانات"]=="📅 يومي"])
                c1,c2 = st.columns(2)
                c1.metric("📡 أسهم Intraday", intra_count)
                c2.metric("📅 أسهم يومية", daily_count)

    elif st.session_state.intraday_supported is False:
        st.error("❌ API لا يدعم Intraday")
        st.markdown("""
        **النموذج يعمل على بيانات يومية (نفس test10)**

        **لتفعيل الطبقة 3 تحتاج:**
        - التحقق من خطة API الحالية
        - طلب تفعيل `client.intraday()` من مزود الـ API
        - لو مدعوم: سيتفعل تلقائياً بدون أي تعديل في الكود
        """)
        st.info("💡 كل باقي الميزات تعمل بشكل طبيعي — الطبقة 3 فقط غير متاحة")

    else:
        st.info("⏳ جاري التحقق من دعم Intraday...")

    # اختبار يدوي
    st.divider()
    st.markdown("**🔧 اختبار يدوي لـ Intraday:**")
    test_sym = st.text_input("أدخل رمز سهم للاختبار:", "2222")
    if st.button("اختبر Intraday"):
        with st.spinner("جاري الاختبار..."):
            i_c, i_h, i_l, i_v, i_t, supported = get_intraday(test_sym)
        if supported and len(i_c) > 0:
            st.success(f"✅ Intraday مدعوم — {len(i_c)} شمعة لـ {test_sym}")
            df_test = pd.DataFrame({"close":i_c,"high":i_h,"low":i_l,"volume":i_v})
            st.dataframe(df_test.tail(10), use_container_width=True)
            st.write(f"RSI intraday: {calc_rsi(i_c)}")
            m,ms,mh = calc_macd(i_c)
            st.write(f"MACD: {m} | Signal: {ms} | Hist: {mh}")
        else:
            st.error(f"❌ Intraday غير مدعوم أو لا بيانات لـ {test_sym}")
            st.info("النموذج يعمل على البيانات اليومية بدلاً منه")

# ─── تاب 6 و 7: الجداول ───
with tab6:
    st.subheader(f"🔍 الأسهم النشطة ({len(STOCKS_ACTIVE)} سهم)")
    render_table(data1, "active")

with tab7:
    st.subheader(f"🔎 المسح الشامل ({len(scan_only)} سهم)")
    render_table(data2, "scan")

# ─── تاب 8: سجل اليوم ───
with tab8:
    st.subheader("📋 سجل اليوم")
    today_sigs = load_today_signals()
    if today_sigs:
        df_log = pd.DataFrame(today_sigs)
        total  = len(today_sigs)
        buy_n  = len([s for s in today_sigs if "BUY" in s.get("signal_type","")])
        bo_n   = len([s for s in today_sigs if s.get("is_breakout",0)==1])
        intra_n = len([s for s in today_sigs if s.get("is_intraday",0)==1])
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("إجمالي", total)
        c2.metric("BUY", buy_n)
        c3.metric("Breakout", bo_n)
        c4.metric("📡 Intraday", intra_n)
        st.dataframe(df_log, use_container_width=True)
        csv = df_log.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ تحميل", csv, f"signals_{now.strftime('%Y_%m_%d')}.csv", "text/csv")
    else:
        st.info("لا توجد سجلات اليوم")

# ─── تاب 9: التقارير ───
with tab9:
    st.subheader("📊 التقارير")
    r1,r2 = st.tabs(["📅 اليوم","📈 الأداء الكلي"])
    with r1:
        today_sigs = load_today_signals()
        if today_sigs:
            df_t = pd.DataFrame(today_sigs)
            won  = len([s for s in today_sigs if str(s.get("result_24h","")).startswith("✅")])
            lost = len([s for s in today_sigs if str(s.get("result_24h","")).startswith("❌")])
            pend = len([s for s in today_sigs if str(s.get("result_24h","")).startswith("⏳")])
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("إجمالي",len(today_sigs)); c2.metric("✅ وصل",won)
            c3.metric("❌ Stop",lost); c4.metric("⏳ جارٍ",pend)
            st.dataframe(df_t, use_container_width=True)
        else: st.info("لا توجد إشارات اليوم")
    with r2:
        try:
            with get_db_conn() as conn:
                df_all_s = pd.read_sql_query("SELECT * FROM signals ORDER BY signal_id DESC", conn)
            if not df_all_s.empty:
                total_all = len(df_all_s)
                completed = df_all_s[df_all_s["result_24h"]!=""]
                success   = len(completed[completed["profit_loss"].astype(str).str.startswith("+")])
                intra_all = len(df_all_s[df_all_s.get("is_intraday",pd.Series([0]*len(df_all_s)))==1]) if "is_intraday" in df_all_s.columns else 0
                p1,p2,p3,p4 = st.columns(4)
                p1.metric("إجمالي",total_all); p2.metric("مكتملة",len(completed))
                p3.metric("ناجحة",success); p4.metric("📡 Intraday",intra_all)
                if len(completed)>0:
                    rate = round(success/len(completed)*100,1)
                    st.metric("نسبة النجاح",f"{rate}%")
                    if rate>=65: st.success(f"🎯 {rate}% ممتاز!")
                    elif rate>=55: st.warning(f"📊 {rate}% جيد")
                    else: st.error(f"⚠️ {rate}% تحتاج مراجعة")
                st.dataframe(df_all_s.head(50), use_container_width=True)
        except:
            st.info("ستظهر بعد أول إشارة")

    if after_close and all_data:
        df_save = pd.DataFrame(all_data)
        path = os.path.join(DAILY_DIR, f"{now.strftime('%Y_%m_%d')}.csv")
        save_c = ["الرمز","الاسم","السعر","التغيير%","النجوم","الإشارة",
                  "هدف1","هدف2","Stop Loss","الثقة%","RSI","حجم×",
                  "القوة%","طبقة البيانات","Breakout"]
        save_c = [c for c in save_c if c in df_save.columns]
        df_save[save_c].to_csv(path, index=False, encoding="utf-8-sig")

# ─── تاب 10: اختبار النموذج — Backtesting ───
with tab10:
    st.subheader("🧪 Scan into test11 — آخر 20 يوم تداول")
    st.caption("يشغّل نفس منطق test11 على بيانات تاريخية ويقارن بما حدث فعلاً")

    # ============================================================
    # دوال الـ Backtesting
    # ============================================================

    def get_trading_days(closes_dates, n=20):
        """يرجع آخر N يوم تداول من البيانات"""
        # نستخدم عدد الإغلاقات كمؤشر للأيام
        return min(n, len(closes_dates) - 30)  # نترك 30 يوم للمؤشرات

    def backtest_one_stock(sym, name, n_days=20):
        """
        يختبر سهم واحد على آخر n_days يوم
        لكل يوم:
          - يحسب الإشارة بناءً على البيانات حتى ذلك اليوم فقط
          - يرى ما حدث في اليوم التالي (النتيجة الفعلية)
        """
        try:
            closes, highs, lows, volumes = get_historical(sym)
            if len(closes) < n_days + 50:
                return []

            results = []
            # نختبر آخر n_days يوم
            start_idx = len(closes) - n_days

            for i in range(start_idx, len(closes) - 1):
                # البيانات حتى يوم الإشارة (لا نرى المستقبل)
                c = closes[:i]
                h = highs[:i]
                l = lows[:i]
                v = volumes[:i]

                if len(c) < 30:
                    continue

                # سعر يوم الإشارة
                price      = closes[i-1]
                change_pct = (closes[i-1] - closes[i-2]) / closes[i-2] * 100 if i > 1 else 0

                # حساب المؤشرات على البيانات حتى أمس
                rsi      = calc_rsi(c)
                rsi_dir  = calc_rsi_direction(c)
                macd, macd_sig, macd_hist = calc_macd(c)
                macd_dir = calc_macd_direction(c)
                ma20     = calc_ma(c, 20)
                ma50     = calc_ma(c, 50)
                bb_up, _, bb_low = calc_bollinger(c)
                atr      = calc_atr(h, l, c)
                vol_high, vol_very, vol_ratio, avg_vol = calc_volume(v)

                liq_score = calc_liquidity_score(vol_ratio, avg_vol)
                slip_pct, _ = calc_slippage(liq_score)
                entry = round(price * (1 + slip_pct), 2)

                # نفس منطق test11 بدون TASI (لا نعرف TASI التاريخي)
                score, reasons = get_strength(
                    change_pct, rsi, rsi_dir, macd, macd_sig, macd_hist,
                    macd_dir, ma20, ma50, price, vol_high, vol_very,
                    vol_ratio, 0.0, bb_low, bb_up, False
                )
                confidence = calc_confidence(score, rsi_dir, macd_dir,
                                             vol_high, vol_very, 0.0)
                signal, sig_type = get_signal(
                    score, rsi, confidence, price, ma50,
                    change_pct, liq_score, vol_ratio, atr or 0, False
                )

                if not atr or atr == 0:
                    continue

                t1, t2, stop, t1_pct, t2_pct, _ = calc_targets_and_sl(
                    entry, atr, confidence
                )

                # ── النتيجة الفعلية في اليوم التالي ──
                next_close = closes[i]
                next_high  = highs[i]
                next_low   = lows[i]
                actual_chg = round((next_close - price) / price * 100, 2)

                # هل وصل الهدف أو الـ Stop؟
                hit_t2   = next_high >= t2
                hit_t1   = next_high >= t1
                hit_stop = next_low <= stop

                if hit_t2:
                    outcome = "✅ هدف 2"
                    pnl_pct = t2_pct
                elif hit_t1 and not hit_stop:
                    outcome = "🟡 هدف 1"
                    pnl_pct = t1_pct
                elif hit_stop and not hit_t1:
                    outcome = "❌ Stop Loss"
                    pnl_pct = round((stop - entry) / entry * 100, 2)
                elif hit_t1 and hit_stop:
                    # وصل الاثنين — لو هدف1 أولاً ثم stop
                    outcome = "🟡 هدف 1 ثم Stop"
                    pnl_pct = t1_pct / 2  # نصف الكمية
                else:
                    outcome = "⏳ لم يصل"
                    pnl_pct = actual_chg

                results.append({
                    "الرمز":       sym,
                    "الاسم":       name,
                    "يوم_الإشارة": i - start_idx + 1,
                    "السعر":       price,
                    "الإشارة":     signal,
                    "نوع الإشارة": sig_type,
                    "القوة%":      score,
                    "الثقة%":      confidence,
                    "RSI":         rsi,
                    "MACD":        macd,
                    "هدف1":        t1,
                    "هدف2":        t2,
                    "Stop":        stop,
                    "هدف1%":       t1_pct,
                    "هدف2%":       t2_pct,
                    "إغلاق_التالي": next_close,
                    "أعلى_التالي":  next_high,
                    "أدنى_التالي":  next_low,
                    "تغيير_فعلي%":  actual_chg,
                    "النتيجة":      outcome,
                    "ربح/خسارة%":   pnl_pct,
                    "ناجحة":        1 if "✅" in outcome or "🟡" in outcome else 0,
                })

            return results
        except Exception as e:
            return []

    def run_backtest(stocks_list, n_days=20):
        """يشغّل الاختبار على كل الأسهم"""
        all_results = []
        prog = st.progress(0)
        stat = st.empty()
        total = len(stocks_list)

        for i, (sym, name) in enumerate(stocks_list):
            stat.text(f"اختبار {i+1}/{total}: {sym} — {name}")
            results = backtest_one_stock(sym, name, n_days)
            all_results.extend(results)
            prog.progress((i+1)/total)

        prog.empty(); stat.empty()
        return all_results

    # ============================================================
    # واجهة الـ Backtesting
    # ============================================================

    st.markdown("""
    **كيف يعمل:**
    - يأخذ البيانات التاريخية لكل سهم
    - لكل يوم: يحسب الإشارة بناءً على ما قبله فقط
    - يرى ما حدث في اليوم التالي (الإغلاق + الأعلى + الأدنى)
    - يحكم: هل وصل الهدف؟ هل ضرب الـ Stop؟
    """)

    col_bt1, col_bt2, col_bt3 = st.columns(3)
    with col_bt1:
        bt_days = st.slider("عدد أيام الاختبار:", 5, 20, 20)
    with col_bt2:
        bt_scope = st.selectbox("النطاق:", ["أسهم نشطة فقط", "كل القوائم"])
    with col_bt3:
        bt_filter = st.selectbox("فلتر الإشارات:", ["BUY فقط", "كل الإشارات"])

    run_bt = st.button("🚀 ابدأ الاختبار", type="primary")

    if run_bt:
        stocks_to_test = STOCKS_ACTIVE if bt_scope == "أسهم نشطة فقط" else STOCKS_ACTIVE + STOCKS_SCAN

        with st.spinner(f"جاري اختبار {len(stocks_to_test)} سهم على آخر {bt_days} يوم..."):
            bt_results = run_backtest(stocks_to_test, bt_days)

        if not bt_results:
            st.error("❌ لم تُنتج أي نتائج — تحقق من البيانات")
        else:
            df_bt = pd.DataFrame(bt_results)

            # فلتر BUY
            if bt_filter == "BUY فقط":
                df_bt_show = df_bt[df_bt["نوع الإشارة"].isin(["strong","normal"])]
            else:
                df_bt_show = df_bt.copy()

            # ── إحصاءات كلية ──
            total_signals = len(df_bt_show)
            buy_signals   = len(df_bt_show[df_bt_show["نوع الإشارة"].isin(["strong","normal"])])
            won           = df_bt_show["ناجحة"].sum()
            success_rate  = round(won/total_signals*100, 1) if total_signals > 0 else 0
            avg_win       = df_bt_show[df_bt_show["ناجحة"]==1]["ربح/خسارة%"].mean()
            avg_loss      = df_bt_show[df_bt_show["ناجحة"]==0]["ربح/خسارة%"].mean()
            hit_t2        = len(df_bt_show[df_bt_show["النتيجة"]=="✅ هدف 2"])
            hit_t1        = len(df_bt_show[df_bt_show["النتيجة"].str.contains("هدف 1",na=False)])
            hit_stop      = len(df_bt_show[df_bt_show["النتيجة"]=="❌ Stop Loss"])

            # ── عرض الإحصاءات ──
            st.divider()
            st.markdown("### 📊 نتائج الاختبار")

            m1,m2,m3,m4 = st.columns(4)
            m1.metric("إجمالي الإشارات", total_signals)
            m2.metric("ناجحة", int(won))
            m3.metric("نسبة النجاح", f"{success_rate}%",
                      delta=f"+{success_rate-50:.1f}% عن العشوائي")
            m4.metric("BUY إشارات", buy_signals)

            m5,m6,m7,m8 = st.columns(4)
            m5.metric("✅ وصل هدف 2", hit_t2)
            m6.metric("🟡 وصل هدف 1", hit_t1)
            m7.metric("❌ ضرب Stop", hit_stop)
            m8.metric("متوسط الربح", f"{avg_win:.2f}%" if avg_win == avg_win else "—")

            # حكم على النموذج
            st.divider()
            if success_rate >= 65:
                st.success(f"🎯 **النموذج ممتاز** — نسبة نجاح {success_rate}% على آخر {bt_days} يوم")
            elif success_rate >= 55:
                st.warning(f"📊 **النموذج جيد** — نسبة نجاح {success_rate}% — هامش ربح مع R/R 1:2")
            elif success_rate >= 45:
                st.warning(f"⚠️ **النموذج متوسط** — {success_rate}% — يحتاج تحسين")
            else:
                st.error(f"❌ **النموذج ضعيف** — {success_rate}% — راجع الفلاتر")

            # ── توزيع النتائج ──
            st.divider()
            st.markdown("### 📈 تفاصيل النتائج")

            bt_tab1, bt_tab2, bt_tab3, bt_tab4 = st.tabs([
                "📋 كل الإشارات",
                "✅ الناجحة",
                "❌ الخاسرة",
                "📊 أداء كل سهم"
            ])

            show_cols = ["الرمز","الاسم","الإشارة","القوة%","الثقة%",
                         "RSI","هدف1%","هدف2%","تغيير_فعلي%","النتيجة","ربح/خسارة%"]
            show_cols = [c for c in show_cols if c in df_bt_show.columns]

            with bt_tab1:
                st.dataframe(
                    df_bt_show[show_cols].sort_values("ربح/خسارة%", ascending=False),
                    use_container_width=True, height=500,
                    column_config={
                        "القوة%":  st.column_config.ProgressColumn("القوة%", min_value=0, max_value=100),
                        "الثقة%":  st.column_config.ProgressColumn("الثقة%", min_value=0, max_value=100),
                        "ربح/خسارة%": st.column_config.NumberColumn("ربح/خسارة%", format="%.2f%%"),
                        "تغيير_فعلي%": st.column_config.NumberColumn("تغيير_فعلي%", format="%.2f%%"),
                    }
                )
                csv_bt = df_bt_show[show_cols].to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
                st.download_button("⬇️ تحميل النتائج", csv_bt, f"backtest_{bt_days}days.csv", "text/csv")

            with bt_tab2:
                df_won = df_bt_show[df_bt_show["ناجحة"]==1].sort_values("ربح/خسارة%", ascending=False)
                if not df_won.empty:
                    st.success(f"{len(df_won)} إشارة ناجحة | متوسط الربح: {df_won['ربح/خسارة%'].mean():.2f}%")
                    st.dataframe(df_won[show_cols], use_container_width=True, height=400,
                        column_config={
                            "القوة%": st.column_config.ProgressColumn("القوة%", min_value=0, max_value=100),
                            "ربح/خسارة%": st.column_config.NumberColumn("ربح/خسارة%", format="%.2f%%"),
                        })
                else:
                    st.info("لا توجد إشارات ناجحة")

            with bt_tab3:
                df_lost = df_bt_show[df_bt_show["ناجحة"]==0].sort_values("ربح/خسارة%")
                if not df_lost.empty:
                    st.error(f"{len(df_lost)} إشارة خاسرة | متوسط الخسارة: {df_lost['ربح/خسارة%'].mean():.2f}%")
                    st.dataframe(df_lost[show_cols], use_container_width=True, height=400,
                        column_config={
                            "القوة%": st.column_config.ProgressColumn("القوة%", min_value=0, max_value=100),
                            "ربح/خسارة%": st.column_config.NumberColumn("ربح/خسارة%", format="%.2f%%"),
                        })
                else:
                    st.success("لا توجد إشارات خاسرة! ✅")

            with bt_tab4:
                if "الرمز" in df_bt_show.columns:
                    stock_perf = df_bt_show.groupby(["الرمز","الاسم"]).agg(
                        إشارات        = ("الإشارة","count"),
                        ناجحة         = ("ناجحة","sum"),
                        متوسط_الربح   = ("ربح/خسارة%","mean"),
                        أفضل_يوم      = ("ربح/خسارة%","max"),
                        أسوأ_يوم      = ("ربح/خسارة%","min"),
                    ).reset_index()
                    stock_perf["نسبة_النجاح%"] = round(stock_perf["ناجحة"]/stock_perf["إشارات"]*100, 1)
                    stock_perf = stock_perf.sort_values("نسبة_النجاح%", ascending=False)

                    st.markdown("**أداء كل سهم على آخر {} يوم:**".format(bt_days))
                    st.dataframe(stock_perf, use_container_width=True, height=500,
                        column_config={
                            "نسبة_النجاح%": st.column_config.ProgressColumn("نسبة النجاح%", min_value=0, max_value=100),
                            "متوسط_الربح": st.column_config.NumberColumn("متوسط الربح%", format="%.2f%%"),
                        })

                    # أفضل 5 أسهم
                    top5 = stock_perf.head(5)
                    st.markdown("**🏆 أفضل 5 أسهم في النموذج:**")
                    for _, row in top5.iterrows():
                        col_s1, col_s2, col_s3 = st.columns(3)
                        col_s1.metric(f"{row['الرمز']} {row['الاسم']}", f"{row['نسبة_النجاح%']}%")
                        col_s2.metric("متوسط الربح", f"{row['متوسط_الربح']:.2f}%")
                        col_s3.metric("إشارات", int(row["إشارات"]))


if abs(st.session_state.daily_pnl)>=DAILY_LOSS_STOP and st.session_state.daily_pnl<0:
    st.error(f"🚨 حد الخسارة ({DAILY_LOSS_STOP:,.0f} ﷼) — توقف!")

st.divider()
st.caption("⚠️ للمعلومات فقط — ليست توصية استثمارية")
