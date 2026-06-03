
# ============ المتطلبات: pip install streamlit streamlit-autorefresh pandas python-dotenv sahmk ============

import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
from datetime import datetime
# ============ تحميل المفاتيح من .env (أمان) ============
API_KEY = st.secrets["API_KEY"]
if "auth" not in st.session_state:
    st.session_state.auth = False
if not st.session_state.auth:
    pwd = st.text_input("كلمة المرور", type="password")
    if st.button("دخول"):
        if pwd == "Theapp1994":
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("خاطئة")
    st.stop()

try:
    from sahmk import SahmkClient
    client = SahmkClient(api_key=API_KEY)
except Exception as e:
    st.error(f"❌ خطأ في الاتصال بـ API: {e}")
    st.stop()

# ============ الأسهم ============
STOCKS_ACTIVE = [
    ("2222", "أرامكو"), ("1120", "الراجحي"), ("7010", "STC"),
    ("1180", "الأهلي"), ("1050", "بنك الرياض"), ("1211", "معادن"),
    ("2082", "أكوا باور"), ("2010", "سابك"), ("4030", "البلاد"),
    ("1020", "الجزيرة"), ("2350", "سافكو"), ("4200", "الاتصالات"),
    ("4210", "زين"), ("4220", "موبايلي"), ("2060", "نماء"),
    ("1150", "البنك الأهلي"), ("4300", "جرير"), ("4001", "الشرق"),
    ("2150", "التعمير"), ("4260", "الوطنية"), ("4031", "بن داود"),
    ("1140", "البنك السعودي"), ("4050", "سالك"), ("2330", "أدوية"),
    ("1030", "الرياض"), ("2380", "بترو رابغ"), ("1810", "أملاك"),
    ("4240", "بنده"), ("2360", "بترو كيم"), ("1060", "البلاد2"),
    ("2290", "أبوقير"), ("2160", "رالكو"), ("4160", "تكامين"),
    ("2190", "جبسكو"), ("4280", "المملكة"), ("2370", "مصافي"),
    ("4310", "عسير"), ("4320", "اليمامة"), ("2250", "سدافكو"),
    ("4180", "فتيحي"), ("2100", "وفرة"), ("4130", "بنك البلاد"),
    ("3002", "التعاونية"), ("3003", "ملاذ"), ("3007", "ولاء"),
    ("3010", "الدرع العربي"), ("4150", "المراعي"), ("4051", "فواز"),
    ("4060", "عبدالله العثيم"), ("4190", "الخزف"),
]

STOCKS_SCAN = [
    ("1010", "الأسمنت السعودية"), ("1040", "السعودية للصناعات"),
    ("1070", "التصنيع"), ("1080", "الخليج"), ("1090", "الزامل"),
    ("1111", "دار الأركان"), ("1160", "الأهلي للتمويل"),
    ("1170", "SABB"), ("1301", "أسمنت العربية"), ("1302", "أسمنت اليمامة"),
    ("1303", "أسمنت السعودية"), ("1304", "أسمنت القصيم"),
    ("1305", "أسمنت الجنوب"), ("1310", "أسمنت ينبع"),
    ("1320", "أسمنت تبوك"), ("1330", "أسمنت نجران"),
    ("2001", "كيان"), ("2030", "البتروكيم"),
    ("2080", "ابن رشد"), ("2130", "المجموعة السعودية"),
    ("2170", "الجبيل"), ("2180", "الزامل للصناعة"),
    ("2200", "أراضي"), ("2230", "كيمانول"),
    ("2240", "إنترانس"), ("2270", "سابك للمغذيات"),
    ("2300", "السعودية للخدمات"), ("2310", "المتحدة"),
    ("2390", "الرياض للصناعة"), ("3001", "سلامة"),
    ("3004", "الأهلية"), ("3005", "البلاد للتأمين"),
    ("3006", "الراجحي للتأمين"), ("3008", "الاتحاد الخليجي"),
    ("3009", "بوبا العربية"), ("3011", "أمانة"), ("3012", "وقاية"),
    ("3015", "تكافل الراجحي"), ("3016", "أليانز"),
    ("3017", "المتحدة للتأمين"), ("3020", "ميدغلف"),
    ("4002", "المطاحن"), ("4003", "الغذائية"), ("4004", "الزاد"),
    ("4005", "هرفي"), ("4011", "البحري"),
    ("4020", "طيران ناس"), ("4040", "الحكير"), ("4070", "الأندلس"),
    ("4090", "الفرسان"), ("4100", "الموارد"),
    ("4140", "أنعام"), ("4170", "الدريم"), ("4230", "المتقدمة للتقنية"),
    ("4270", "سدير"), ("4290", "تهامة"),
    ("4340", "النخيل"), ("4345", "الشرق الأوسط"),
    ("2040", "الخليج للبتروكيم"), ("2090", "نماء للكيماويات"),
    ("2140", "اليانسون"), ("2210", "نفط الهلال"),
    ("2260", "الشرقية للتنمية"), ("2320", "الخليج الدولية"),
    ("2340", "وادي النيل"), ("3013", "الخليج للتأمين"),
    ("3014", "الصقر"), ("3018", "الاتحاد للتأمين"),
    ("4007", "الجوف"), ("4008", "تبوك الزراعية"),
    ("4080", "المتطورة"), ("4346", "الخليج"),
]

# ============ أهداف الربح الثلاثة (بالمئة) ============
TARGET_1_PCT = 1.5   # هدف 1 - محافظ
TARGET_2_PCT = 3.0   # هدف 2 - متوسط
TARGET_3_PCT = 5.0   # هدف 3 - جريء

# ============ جلب البيانات ============
@st.cache_data(ttl=60)
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
                errors.append(f"batch {i}: {str(e)[:50]}")
        return quotes_dict, errors
    except Exception as e:
        return {}, [str(e)]

@st.cache_data(ttl=1800)
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

@st.cache_data(ttl=60)
def get_market():
    try:
        return client.market_summary(), None
    except Exception as e:
        return None, str(e)

@st.cache_data(ttl=3600)
def get_movers():
    try:
        return client.gainers(), client.losers(), client.volume_leaders(), None
    except Exception as e:
        return None, None, None, str(e)

# ============ المؤشرات الفنية (محسّنة رياضياً) ============
def calc_ema_series(data, period):
    """حساب EMA صحيح على كامل السلسلة"""
    if len(data) < period:
        return []
    k = 2.0 / (period + 1)
    ema = [sum(data[:period]) / period]  # SMA كبداية
    for price in data[period:]:
        ema.append(price * k + ema[-1] * (1 - k))
    return ema

def calc_rsi(closes, period=14):
    """RSI بطريقة Wilder's smoothing الصحيحة"""
    if len(closes) < period + 1:
        return 50.0
    deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
    gains = [max(d, 0.0) for d in deltas]
    losses = [max(-d, 0.0) for d in deltas]
    
    # Wilder's smoothing
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 1)

def calc_macd(closes):
    """MACD صحيح مع EMA كامل"""
    if len(closes) < 35:
        return 0.0, 0.0, 0.0
    ema12 = calc_ema_series(closes, 12)
    ema26 = calc_ema_series(closes, 26)
    min_len = min(len(ema12), len(ema26))
    macd_line = [ema12[-(min_len - i)] - ema26[-(min_len - i)] 
                 for i in range(min_len)]
    if len(macd_line) < 9:
        return 0.0, 0.0, 0.0
    signal_line = calc_ema_series(macd_line, 9)
    macd_val = macd_line[-1]
    signal_val = signal_line[-1] if signal_line else 0.0
    histogram = macd_val - signal_val
    return round(macd_val, 3), round(signal_val, 3), round(histogram, 3)

def calc_ma(closes, period):
    if len(closes) < period:
        return 0.0
    return round(sum(closes[-period:]) / period, 2)

def calc_bollinger(closes, period=20, std_dev=2):
    if len(closes) < period:
        return 0.0, 0.0, 0.0
    recent = closes[-period:]
    ma = sum(recent) / period
    variance = sum((x - ma) ** 2 for x in recent) / period
    std = variance ** 0.5
    return round(ma + std_dev * std, 2), round(ma, 2), round(ma - std_dev * std, 2)

def calc_atr(highs, lows, closes, period=14):
    """Average True Range لقياس التذبذب"""
    if len(closes) < period + 1:
        return 0.0
    tr_list = []
    for i in range(1, len(closes)):
        h, l, prev_c = highs[i], lows[i], closes[i-1]
        tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
        tr_list.append(tr)
    if len(tr_list) < period:
        return 0.0
    atr = sum(tr_list[-period:]) / period
    return round(atr, 3)

def calc_candles(closes, highs, lows):
    """فحص نمط الشمعات مع منطق أدق"""
    if len(closes) < 4:
        return False, "—"
    
    # Engulfing صاعد
    if (closes[-2] < closes[-3] and  # شمعة حمراء
        closes[-1] > closes[-2] and   # شمعة خضراء
        closes[-1] > closes[-3] and   # تجاوزت الافتتاح السابق
        lows[-1] < lows[-2]):         # ابتلعت القاع
        return True, "ابتلاع 🟢"
    
    # Hammer
    body = abs(closes[-1] - closes[-2])
    candle_range = highs[-1] - lows[-1]
    lower_shadow = min(closes[-1], closes[-2]) - lows[-1]
    if candle_range > 0 and lower_shadow / candle_range > 0.6 and closes[-1] > closes[-2]:
        return True, "مطرقة 🔨"
    
    # 3 شمعات صاعدة متتالية
    if all(closes[i] > closes[i-1] for i in range(-2, 0)):
        return True, "صاعد 3 📈"
    
    return False, "—"

def calc_volume(volumes):
    if len(volumes) < 20:
        return False, 0.0, 0.0
    avg_20 = sum(volumes[-20:-1]) / 19
    avg_5 = sum(volumes[-5:]) / 5
    ratio = volumes[-1] / avg_20 if avg_20 > 0 else 0.0
    trend = avg_5 / avg_20 if avg_20 > 0 else 1.0
    return ratio > 1.5, round(ratio, 1), round(trend, 1)

def get_strength(change_pct, rsi, macd, macd_signal, macd_hist,
                  ma20, ma50, ma200, price, vol_high, vol_ratio,
                  bullish_candle, tasi_bullish, bb_lower, bb_upper, atr):
    """نظام نقاط محسّن مع أوزان أكثر منطقية"""
    score = 0
    reasons = []

    # === RSI (25 نقطة) ===
    if rsi < 30:
        score += 25; reasons.append(f"RSI تشبع بيع ({rsi})")
    elif rsi < 40:
        score += 18; reasons.append(f"RSI منطقة شراء ({rsi})")
    elif 40 <= rsi < 55:
        score += 10; reasons.append(f"RSI متوازن ({rsi})")
    elif rsi > 70:
        score -= 10; reasons.append(f"RSI تشبع شراء ({rsi}) ⚠️")

    # === MACD (20 نقطة) ===
    if macd > 0 and macd_hist > 0 and macd > macd_signal:
        score += 20; reasons.append("MACD إشارة شراء قوية")
    elif macd > macd_signal and macd_hist > 0:
        score += 12; reasons.append("MACD تقاطع صاعد")
    elif macd > 0:
        score += 6
    elif macd_hist < 0:
        score -= 5; reasons.append("MACD ضعيف ⚠️")

    # === المتوسطات المتحركة (20 نقطة) ===
    if ma200 > 0 and price > ma200 > 0:
        score += 8; reasons.append("فوق MA200")
    if ma50 > 0 and price > ma50:
        score += 6; reasons.append("فوق MA50")
    if ma20 > 0 and price > ma20:
        score += 6; reasons.append("فوق MA20")
    if ma20 > 0 and ma50 > 0 and ma20 > ma50:
        score += 5; reasons.append("MA20 > MA50 (Golden)")  # bonus

    # === حجم التداول (15 نقطة) ===
    if vol_high and vol_ratio >= 3:
        score += 15; reasons.append(f"حجم استثنائي ×{vol_ratio}")
    elif vol_high and vol_ratio >= 2:
        score += 10; reasons.append(f"حجم عالٍ ×{vol_ratio}")
    elif vol_high:
        score += 6; reasons.append(f"حجم مرتفع ×{vol_ratio}")

    # === نمط الشمعات (10 نقاط) ===
    if bullish_candle:
        score += 10; reasons.append("نمط شمعة إيجابي")

    # === TASI (5 نقاط) ===
    if tasi_bullish:
        score += 5; reasons.append("السوق صاعد")

    # === بولينجر (5 نقاط) ===
    if bb_lower > 0 and price <= bb_lower * 1.01:
        score += 5; reasons.append("عند الحد الأدنى BB")
    elif bb_upper > 0 and price >= bb_upper * 0.99:
        score -= 5; reasons.append("عند الحد الأعلى BB ⚠️")

    return min(max(score, 0), 100), reasons

def get_signal(score, change_pct, rsi):
    """إشارة مبنية على Score + فلاتر إضافية"""
    if score >= 75 and rsi < 70:
        return "BUY 🟢", "strong"
    elif score >= 60 and rsi < 65:
        return "BUY 🟢", "normal"
    elif score < 35 or change_pct < -2 or rsi > 75:
        return "SELL 🔴", "sell"
    else:
        return "WAIT 🟡", "wait"

def calc_targets(price, atr):
    """
    حساب الأهداف الثلاثة بالنسب المئوية
    الهدف 1: محافظ
    الهدف 2: متوسط
    الهدف 3: جريء
    """
    t1 = round(price * (1 + TARGET_1_PCT / 100), 2)
    t2 = round(price * (1 + TARGET_2_PCT / 100), 2)
    t3 = round(price * (1 + TARGET_3_PCT / 100), 2)
    return t1, t2, t3

# ============ تحليل الأسهم ============
def analyze_stocks(stocks_list, quotes_dict, tasi_bullish):
    data, failed = [], []
    for sym, name in stocks_list:
        try:
            q = quotes_dict.get(sym)
            if not q or not hasattr(q, 'price') or not q.price:
                failed.append(f"{sym}(لا سعر)")
                continue

            closes, highs, lows, volumes = get_historical(sym)
            if len(closes) < 30:
                failed.append(f"{sym}(بيانات قليلة)")
                continue

            price = float(q.price)
            change_pct = float(getattr(q, 'change_percent', 0) or 0)

            rsi = calc_rsi(closes)
            macd, macd_signal, macd_hist = calc_macd(closes)
            ma20 = calc_ma(closes, 20)
            ma50 = calc_ma(closes, 50)
            ma200 = calc_ma(closes, 200)
            bb_upper, bb_mid, bb_lower = calc_bollinger(closes)
            atr = calc_atr(highs, lows, closes)
            bullish, candle_pattern = calc_candles(closes, highs, lows)
            vol_high, vol_ratio, vol_trend = calc_volume(volumes)

            score, reasons = get_strength(
                change_pct, rsi, macd, macd_signal, macd_hist,
                ma20, ma50, ma200, price, vol_high, vol_ratio,
                bullish, tasi_bullish, bb_lower, bb_upper, atr
            )

            signal, signal_type = get_signal(score, change_pct, rsi)
            t1, t2, t3 = calc_targets(price, atr)

            data.append({
                "الرمز": sym,
                "الاسم": name,
                "السعر": price,
                "التغيير%": round(change_pct, 2),
                "RSI": rsi,
                "MACD": macd,
                "Hist": macd_hist,
                "MA20": ma20,
                "MA50": ma50,
                "MA200": ma200,
                "ATR": atr,
                "BB+": bb_upper,
                "BB-": bb_lower,
                "حجم×": vol_ratio,
                "شمعة": candle_pattern,
                "القوة%": score,
                "الإشارة": signal,
                f"هدف1 ({TARGET_1_PCT}%)": t1,
                f"هدف2 ({TARGET_2_PCT}%)": t2,
                f"هدف3 ({TARGET_3_PCT}%)": t3,
                "_reasons": " | ".join(reasons),
                "_signal_type": signal_type,
            })
        except Exception as e:
            failed.append(f"{sym}({str(e)[:30]})")

    return data, failed

# ============ الواجهة ============
st.set_page_config(
    page_title="داشبورد التداول السعودي",
    layout="wide",
    page_icon="📊",
    initial_sidebar_state="collapsed"
)
st_autorefresh(interval=60000, key="autorefresh")

st.markdown("""
<style>
    .stMetric label { font-size: 14px !important; }
    .stDataFrame { font-size: 13px; }
    .target-box { padding: 8px; border-radius: 6px; text-align: center; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

st.title("📊 داشبورد التداول السعودي")

now = datetime.now()
market_open = 10 <= now.hour < 15

market, market_err = get_market()
tasi_bullish = False
if market:
    try:
        tasi_bullish = (getattr(market, 'market_mood', '') == 'Bullish' or
                        getattr(market, 'advancing', 0) > getattr(market, 'declining', 0))
    except:
        pass

# ============ شريط الحالة ============
c1, c2, c3, c4 = st.columns(4)
with c1:
    if now.hour < 10:
        mins = (10 - now.hour) * 60 - now.minute
        st.warning(f"⏳ يفتح بعد {mins} دقيقة")
    elif now.hour == 10 and now.minute < 15:
        st.error(f"⛔ انتظر {15 - now.minute} دقيقة")
    elif market_open:
        st.success("✅ السوق مفتوح")
    else:
        st.warning("🔒 السوق أغلق")

with c2:
    if market:
        try:
            st.metric("TASI", f"{market.index_value:,.0f}", f"{market.index_change_percent:+.2f}%")
        except:
            st.metric("TASI", "—")

with c3:
    st.metric("هدف 1", f"{TARGET_1_PCT}%", "محافظ")

with c4:
    st.metric("هدف 2 / 3", f"{TARGET_2_PCT}% / {TARGET_3_PCT}%", "متوسط / جريء")

if market:
    try:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("صاعدة 🟢", getattr(market, 'advancing', '—'))
        col2.metric("هابطة 🔴", getattr(market, 'declining', '—'))
        col3.metric("ثابتة", getattr(market, 'unchanged', '—'))
        col4.metric("مزاج السوق", getattr(market, 'market_mood', '—'))
    except:
        pass

st.divider()

# ============ وضع الدخول ============
col_mode, col_min = st.columns([2, 3])
with col_mode:
    mode = st.radio("وضع الدخول:", ["🛡️ محافظ (60+)", "⚡ جريء (75+)", "🔬 مسح (كل شيء)"],
                    horizontal=True)

if "محافظ" in mode:
    min_strength = 60
elif "جريء" in mode:
    min_strength = 75
else:
    min_strength = 0

if not market_open:
    min_strength = 0

with col_min:
    if now.hour == 10 and now.minute < 15:
        st.warning("⛔ أول 15 دقيقة - تقلبات عالية - ينصح بالانتظار")
    elif not market_open:
        st.info("🔒 السوق مغلق - البيانات للمراجعة فقط")

# ============ جلب وتحليل البيانات ============
with st.spinner("جاري تحليل الأسهم..."):
    quotes_dict, api_errors = get_all_quotes()
    data1, failed1 = analyze_stocks(STOCKS_ACTIVE, quotes_dict, tasi_bullish)
    data2, failed2 = analyze_stocks(STOCKS_SCAN, quotes_dict, tasi_bullish)

total_ok = len(data1) + len(data2)
total_fail = len(failed1) + len(failed2)

st.caption(
    f"🕐 {now.strftime('%H:%M:%S')} | "
    f"✅ {total_ok} سهم محلل | "
    f"❌ {total_fail} مفقود | "
    f"تحديث الأسعار: 60ث | تحديث المؤشرات: 30د"
)

if failed1 or failed2 or api_errors:
    with st.expander(f"⚠️ تفاصيل المشاكل ({total_fail} سهم مفقود)"):
        if api_errors:
            st.error("أخطاء API: " + str(api_errors))
        if failed1:
            st.write("النشطة المفقودة:", failed1)
        if failed2:
            st.write("المسح المفقودة:", failed2)

st.divider()

# ============ دالة عرض الجدول ============
def render_table(data_list, key_prefix):
    if not data_list:
        st.warning("لا توجد بيانات")
        return

    df = pd.DataFrame(data_list)

    # إخفاء الأعمدة الداخلية
    display_cols = [c for c in df.columns if not c.startswith("_")]
    df_display = df[display_cols].copy()

    # فلتر الإشارة
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        show_buy = st.checkbox("BUY فقط 🟢", key=f"{key_prefix}_buy")
    with col_f2:
        show_strong = st.checkbox("قوة 75%+ فقط", key=f"{key_prefix}_strong")
    with col_f3:
        sort_by = st.selectbox("ترتيب حسب:", ["القوة%", "RSI", "التغيير%", "حجم×"],
                               key=f"{key_prefix}_sort")

    df_display = df_display.sort_values(sort_by, ascending=(sort_by == "RSI"))

    if show_buy:
        df_display = df_display[df_display["الإشارة"] == "BUY 🟢"]
    if show_strong:
        df_display = df_display[df_display["القوة%"] >= 75]
    
    st.dataframe(
        df_display,
        use_container_width=True,
        height=500,
        column_config={
            "القوة%": st.column_config.ProgressColumn("القوة%", min_value=0, max_value=100),
            "RSI": st.column_config.NumberColumn("RSI", format="%.1f"),
            "التغيير%": st.column_config.NumberColumn("التغيير%", format="%.2f%%"),
        }
    )

    buy_df = df_display[df_display["الإشارة"] == "BUY 🟢"]
    if not buy_df.empty:
        symbols = buy_df["الرمز"].tolist()
        st.success(f"🔔 إشارات BUY ({len(symbols)}): {', '.join(symbols[:8])}" +
                   (" وأخرى..." if len(symbols) > 8 else ""))

# ============ التابات ============
tab1, tab2, tab3, tab4 = st.tabs([
    "📈 حركة السوق", "⚡ الأسهم النشطة", "🔍 المسح الشامل", "🌅 أفضل الفرص"
])

with tab1:
    st.subheader("📈 حركة السوق اليوم")
    g, l, v, movers_err = get_movers()
    if movers_err:
        st.warning(f"تعذر تحميل بيانات السوق: {movers_err}")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("**🟢 أعلى الصاعدين**")
        try:
            gdf = pd.DataFrame([{
                "الرمز": x.symbol, "الاسم": x.name,
                "السعر": x.price, "التغيير%": x.change_percent
            } for x in g.movers])
            st.dataframe(gdf, use_container_width=True)
        except:
            st.info("لا توجد بيانات")

    with col2:
        st.markdown("**🔴 أكثر الهابطين**")
        try:
            ldf = pd.DataFrame([{
                "الرمز": x.symbol, "الاسم": x.name,
                "السعر": x.price, "التغيير%": x.change_percent
            } for x in l.movers])
            st.dataframe(ldf, use_container_width=True)
        except:
            st.info("لا توجد بيانات")

    with col3:
        st.markdown("**💹 الأكثر تداولاً**")
        try:
            vdf = pd.DataFrame([{
                "الرمز": x.symbol, "الاسم": x.name,
                "السعر": x.price, "الحجم": x.volume
            } for x in v.movers])
            st.dataframe(vdf, use_container_width=True)
        except:
            st.info("لا توجد بيانات")

with tab2:
    st.subheader("⚡ الأسهم النشطة (50 سهم)")
    render_table(data1, "active")

with tab3:
    st.subheader("🔍 المسح الشامل (80 سهم)")
    render_table(data2, "scan")

with tab4:
    st.subheader("🌅 أفضل الفرص - ملخص شامل")
    all_data = data1 + data2

    if all_data:
        df_all = pd.DataFrame(all_data)
        df_buy = df_all[df_all["الإشارة"] == "BUY 🟢"].sort_values("القوة%", ascending=False)

        if not df_buy.empty:
            st.markdown("### ⭐ أقوى إشارات الشراء")

            # بطاقات للأفضل 3
            top3 = df_buy.head(3)
            cols = st.columns(3)
            for i, (_, row) in enumerate(top3.iterrows()):
                with cols[i]:
                    st.markdown(f"""
                    <div style='background:#1a3a1a;padding:12px;border-radius:10px;border:1px solid #2d6a2d'>
                    <h4 style='color:#4CAF50;margin:0'>{row['الرمز']} - {row['الاسم']}</h4>
                    <p style='margin:4px 0'>💰 السعر: <b>{row['السعر']}</b></p>
                    <p style='margin:4px 0'>📊 القوة: <b>{row['القوة%']}%</b></p>
                    <p style='margin:4px 0'>📈 RSI: {row['RSI']}</p>
                    <hr style='border-color:#2d6a2d'>
                    <p style='margin:4px 0;color:#88dd88'>🎯 هدف 1 ({TARGET_1_PCT}%): <b>{row[f'هدف1 ({TARGET_1_PCT}%)']}</b></p>
                    <p style='margin:4px 0;color:#ffcc44'>🎯 هدف 2 ({TARGET_2_PCT}%): <b>{row[f'هدف2 ({TARGET_2_PCT}%)']}</b></p>
                    <p style='margin:4px 0;color:#ff8844'>🎯 هدف 3 ({TARGET_3_PCT}%): <b>{row[f'هدف3 ({TARGET_3_PCT}%)']}</b></p>
                    <p style='margin:4px 0;font-size:11px;color:#aaa'>{row['_reasons'][:80]}</p>
                    </div>
                    """, unsafe_allow_html=True)

            st.divider()
            st.markdown("### 📋 جميع إشارات BUY")
            target_cols = [c for c in df_buy.columns if not c.startswith("_")]
            st.dataframe(
                df_buy[target_cols].head(20),
                use_container_width=True,
                column_config={
                    "القوة%": st.column_config.ProgressColumn("القوة%", min_value=0, max_value=100),
                }
            )
        else:
            st.info("لا توجد إشارات BUY بالمعايير الحالية")
    else:
        st.warning("لا توجد بيانات")

st.divider()
col_r1, col_r2 = st.columns([1, 4])
with col_r1:
    if st.button("تحديث يدوي 🔄"):
        st.cache_data.clear()
        st.rerun()
with col_r2:
    st.caption("⚠️ هذه الأداة للمعلومات فقط وليست توصية استثمارية")
