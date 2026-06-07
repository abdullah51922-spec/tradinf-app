# ================================================================
# داشبورد RSI Divergence — مبني على test16
# الاستراتيجية: الدخول عند اختلاف الاتجاه بين السعر و RSI
#
# الفريمات المدعومة:
#   - 5 دقائق  (intraday)
#   - 60 دقيقة (hourly)
#   - يومي     (daily)
#
# قواعد الدخول:
#   Bullish Divergence: سعر يصنع قاعاً أدنى + RSI يصنع قاعاً أعلى → BUY
#                       + شرط جديد: RSI الحالي < 45 (ضمان منطقة ضعف)
#   Bearish Divergence: سعر يصنع قمة أعلى + RSI يصنع قمة أدنى → WAIT
#
# [v1.1 — تعديلات بناءً على Backtest]
#   - ATR_SL_MULT: 2.0 → 1.5  (وقف أضيق → R/R أحسن)
#   - ATR_T1_MULT: 2.0 → 1.5  (هدف 1 أقرب → يُصاب أكثر)
#   - ATR_T2_MULT: 3.5 → 3.0  (هدف 2 معقول)
#   - BULLISH_RSI_MAX: جديد = 45 (فلتر جودة للـ Bullish)
# ================================================================

import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import numpy as np
import sqlite3, os, io
from datetime import datetime, timedelta
import pytz

# ─────────────────────────────────────────────────────────────
# 0. إعدادات الصفحة
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RSI Divergence — داشبورد",
    layout="wide",
    page_icon="📡",
    initial_sidebar_state="collapsed"
)

API_KEY     = "shmk_live_96ab6bb9e4cbc219ba23d1d8836d5f13766b6fb43450e245"
RIYADH_TZ   = pytz.timezone("Asia/Riyadh")
DATA_DIR    = "data_rsi_div"
SIGNALS_DB  = os.path.join(DATA_DIR, "rsi_div_signals.db")
os.makedirs(DATA_DIR, exist_ok=True)

def now_riyadh():
    return datetime.now(RIYADH_TZ)

# ─────────────────────────────────────────────────────────────
# 1. الإعدادات — RSI Divergence
# ─────────────────────────────────────────────────────────────
RSI_PERIOD       = 14
ATR_PERIOD       = 14
LOOKBACK_SWING   = 5    # عدد الشموع لتحديد القمة/القاع
LOOKBACK_DIV     = 30   # أبعد نطاق نبحث فيه عن divergence
CONFIRM_CANDLES  = 2    # عدد الشموع للتأكيد قبل الدخول
RSI_OB           = 65   # RSI ذروة شراء (Bearish Div)
RSI_OS           = 35   # RSI ذروة بيع (Bullish Div)
BULLISH_RSI_MAX  = 45   # [v1.1] RSI الحالي لازم < 45 للـ Bullish — فلتر جودة إضافي
ATR_SL_MULT      = 1.5  # [v1.1] خُفّض من 2.0 → وقف أضيق = R/R أحسن
ATR_T1_MULT      = 1.5  # [v1.1] خُفّض من 2.0 → هدف 1 أقرب = يُصاب أكثر
ATR_T2_MULT      = 3.0  # [v1.1] خُفّض من 3.5 → هدف 2 معقول
MIN_RSI_DIFF     = 3.0  # أقل فرق RSI مقبول لتأكيد الـ divergence
MIN_PRICE_DIFF   = 0.3  # أقل فرق سعري % مقبول
MIN_LIQ          = 5    # أقل سيولة مقبولة
VOL_CONFIRM_MULT  = 1.2  # حجم اليوم لازم > 1.2× المتوسط 20 يوم

# تايم فريمات
TIMEFRAMES = {
    "5 دقائق (Intraday)":  "5min",
    "60 دقيقة (Hourly)":   "60min",
    "يومي (Daily)":        "daily",
}

# الأسهم — نفس قائمة test16
ALL_STOCKS = [
    # ── البنوك ──
    ("1010","بنك الرياض"),("1020","بنك الجزيرة"),("1030","البنك السعودي للإستثمار"),
    ("1050","بي اس اف"),("1060","البنك السعودي الأول"),("1080","العربي"),
    ("1120","مصرف الراجحي"),("1140","بنك البلاد"),("1150","مصرف الإنماء"),
    ("1180","البنك الأهلي السعودي"),("1111","شركة مجموعة تداول السعودية القابضة"),
    # ── التمويل ──
    ("1182","شركة أملاك العالمية للتمويل"),("1183","شركة سهل للتمويل"),
    # ── المواد الأساسية والصناعة ──
    ("1201","شركة تكوين المتطورة للصناعات"),("1202","مبكو"),
    ("1210","شركة الصناعات الكيميائية الأساسية"),("1211","شركة التعدين العربية السعودية"),
    ("1212","مجموعة أسترا الصناعية"),("1213","شركة نسيج العالمية التجارية"),
    ("1214","شركة الحسن غازي إبراهيم شاكر"),
    ("1301","شركة إتحاد مصانع الأسلاك"),("1302","شركة بوان"),
    ("1303","شركة الصناعات الكهربائية"),("1304","شركة اليمامة للصناعات الحديدية"),
    ("1320","الشركة السعودية لأنابيب الصلب"),("1321","شركة أنابيب الشرق المتكاملة"),
    ("1322","شركة المصانع الكبرى للتعدين"),("1323","يو سي آي سي"),
    ("1324","شركة صالح عبدالعزيز الراشد وأولاده"),
    # ── الترفيه والموارد البشرية ──
    ("1810","مجموعة سيرا القابضة"),("1820","شركة مجموعة بان القابضة"),
    ("1830","لجام للرياضة"),("1831","شركة مهارة للموارد البشرية"),
    ("1832","شركة صدر للخدمات اللوجستية"),("1833","شركة الموارد للقوى البشرية"),
    ("1834","الشركة السعودية لحلول القوى البشرية"),("1835","تمكين"),
    # ── البتروكيماويات والطاقة ──
    ("2001","شركة كيمائيات الميثانول"),("2010","الشركة السعودية للصناعات الأساسية"),
    ("2020","سابك للمغذيات الزراعية"),("2030","شركة المصافي العربية السعودية"),
    ("2040","شركة الخزف السعودي"),("2050","مجموعة صافولا"),
    ("2060","شركة التصنيع الوطنية"),("2070","الدوائية"),
    ("2080","شركة الغاز والتصنيع الأهلية"),("2081","شركة الخريف لتقنية المياه والطاقة"),
    ("2082","شركة أكوا باور"),("2090","شركة الجبس الأهلية"),
    ("2100","شركة وفرة للصناعة والتنمية"),("2110","شركة الكابلات السعودية"),
    ("2130","الشركة السعودية للتنمية الصناعية"),("2140","شركة أيان للإستثمار"),
    ("2150","شركة الصناعات الزجاجية الوطنية"),("2160","شركة أميانتيت العربية السعودية"),
    ("2170","شركة اللجين"),("2180","شركة تصنيع مواد التعبئة والتغليف"),
    ("2190","شركة البنى التحتية المستدامة القابضة"),("2200","الشركة العربية للأنابيب"),
    ("2210","شركة نماء للكيماويات"),("2220","الشركة الوطنية لتصنيع وسبك المعادن"),
    ("2222","شركة الزيت العربية السعودية"),
    ("2223","شركة أرامكو السعودية لزيوت الأساس"),
    ("2230","الشركة الكيميائية السعودية القابضة"),
    ("2240","شركة صناعات البناء المتقدمة"),("2250","المجموعة السعودية للإستثمار الصناعي"),
    ("2270","الشركة السعودية لمنتجات الألبان والأغذية"),
    ("2280","شركة المراعي"),("2281","شركة التنمية الغذائية"),("2282","شركة نقي للمياه"),
    ("2283","شركة المطاحن الأولى"),("2284","شركة المطاحن الحديثة"),
    ("2285","شركة المطاحن العربية"),("2286","شركة المطاحن الرابعة"),
    ("2287","الشركة العربية للاستثمار الزراعي"),("2288","شركة نفوذ للمنتجات الغذائية"),
    ("2290","شركة ينبع الوطنية للبتروكيماويات"),("2300","الشركة السعودية لصناعة الورق"),
    ("2310","شركة الصحراء العالمية للبتروكيماويات"),
    ("2320","شركة البابطين للطاقة والإتصالات"),("2330","الشركة المتقدمة للبتروكيماويات"),
    ("2340","شركة ارتيكس للاستثمار الصناعي"),("2350","شركة كيان السعودية للبتروكيماويات"),
    ("2360","الشركة السعودية لإنتاج الأنابيب الفخارية"),
    ("2370","شركة الشرق الأوسط للكابلات المتخصصة"),
    ("2380","شركة رابغ للتكرير والبتروكيماويات"),
    ("2381","شركة الحفر العربية"),("2382","شركة أديس القابضة"),
    # ── الأسمنت ──
    ("3002","شركة أسمنت نجران"),("3003","أسمنت المدينة"),
    ("3004","شركة أسمنت المنطقة الشمالية"),("3005","شركة أسمنت ام القرى"),
    ("3007","شركة زهرة الواحة للتجارة"),("3008","شركة الكثيري القابضة"),
    ("3010","شركة الأسمنت العربية"),("3020","شركة أسمنت اليمامة"),
    ("3030","شركة الأسمنت السعودية"),("3040","شركة أسمنت القصيم"),
    ("3050","شركة أسمنت المنطقة الجنوبية"),("3060","شركة أسمنت ينبع"),
    ("3080","شركة أسمنت المنطقة الشرقية"),("3090","شركة أسمنت تبوك"),
    ("3091","شركة أسمنت الجوف"),("3092","شركة أسمنت الرياض"),
    # ── الرعاية الصحية والتجزئة ──
    ("4001","شركة أسواق عبدالله العثيم"),("4002","شركة المواساة للخدمات الطبية"),
    ("4003","الشركة المتحدة للإلكترونيات"),("4004","شركة دله للخدمات الصحية"),
    ("4005","الشركة الوطنية للرعاية الطبية"),("4006","الشركة السعودية للتسويق"),
    ("4007","شركة الحمادي القابضة"),("4008","الشركة السعودية للعدد والأدوات"),
    ("4009","شركة الشرق الأوسط للرعاية الصحية"),
    ("4011","شركة لازوردي للمجوهرات"),("4012","شركة ثوب الأصيل"),
    ("4013","مجموعة الدكتور سليمان الحبيب"),("4014","شركة دار المعدات الطبية"),
    ("4015","شركة مصنع جمجوم للأدوية"),("4016","شركة الشرق الأوسط للصناعات الدوائية"),
    ("4017","فقيه الطبية"),("4018","الموسى"),("4019","الشركة الطبية التخصصية"),
    ("4020","الشركة العقارية السعودية"),("4021","شركة مجمع المركز الكندي الطبي"),
    # ── النقل والخدمات ──
    ("4030","الشركة الوطنية السعودية للنقل البحري"),
    ("4031","الشركة السعودية للخدمات الأرضية"),
    ("4040","الشركة السعودية للنقل الجماعي"),
    ("4050","الشركة السعودية لخدمات السيارات والمعدات"),("4051","شركة باعظيم التجارية"),
    ("4061","مجموعة أنعام الدولية القابضة"),
    ("4070","تهامة"),("4071","الشركة العربية للتعهدات الفنية"),
    ("4072","شركة مجموعة إم بي سي"),
    ("4080","شركة سناد القابضة"),("4090","شركة طيبة للإستثمار"),
    ("4100","شركة مكة للإنشاء والتعمير"),("4110","شركة باتك للإستثمار"),
    ("4130","شركة الباحة للإستثمار والتنمية"),("4140","الشركة السعودية للصادرات الصناعية"),
    ("4141","شركة العمران للصناعة"),("4142","شركة مجموعة كابلات الرياض"),
    ("4143","شركة مجموعة التيسير"),("4144","شركة رؤوم التجارية"),
    ("4145","شركة العبيكان للزجاج"),("4146","شركة جاز العربية للخدمات"),
    ("4147","شركة اتحاد جروننفلدر سعدي"),("4148","شركة الوسائل الصناعية"),
    ("4150","شركة الرياض للتعمير"),("4160","شركة ثمار التنمية القابضة"),
    ("4161","شركة بن داود القابضة"),("4162","شركة المنجم للأغذية"),
    ("4163","شركة الدواء للخدمات الطبية"),("4164","شركة النهدي الطبية"),
    ("4170","شركة المشروعات السياحية"),("4180","مجموعة فتيحي القابضة"),
    ("4190","شركة جرير للتسويق"),("4191","أبو معطي"),
    ("4192","شركة متاجر السيف"),("4193","نايس ون"),
    ("4194","شركة مجموعة منزل التسويق"),("4200","شركة الدريس للخدمات البترولية"),
    ("4210","الأبحاث والإعلام"),("4220","إعمار المدينة الإقتصادية"),
    ("4230","شركة البحر الأحمر العالمية"),("4240","سينومي ريتيل"),
    ("4260","الشركة المتحدة الدولية للمواصلات"),
    ("4261","شركة ذيب لتأجير السيارات"),("4262","شركة لومي للتأجير"),
    ("4263","شركة سال السعودية للخدمات اللوجستية"),("4264","طيران ناس"),
    ("4265","شركة شري للتجارة"),
    ("4270","الشركة السعودية للطباعة والتغليف"),
    ("4280","شركة المملكة القابضة"),
    ("4290","شركة الخليج للتدريب والتعليم"),("4291","الوطنية للتعليم"),
    ("4292","شركة عطاء التعليمية"),
    ("4300","شركة دار الأركان للتطوير العقاري"),
    ("4320","شركة الأندلس العقارية"),
    # ── الريت ──
    ("4330","صندوق الرياض ريت"),("4331","صندوق الجزيرة ريت"),
    ("4332","صندوق جدوى ريت الحرمين"),("4333","صندوق تعليم ريت"),
    ("4334","صندوق المعذر ريت"),("4335","صندوق مشاركة ريت"),
    ("4336","ملكية ريت"),("4337","صندوق العزيزية ريت"),
    ("4340","صندوق الراجحي ريت"),("4342","صندوق جدوى ريت السعودية"),
    ("4344","صندوق سدكو كابيتال ريت"),("4345","صندوق الإنماء ريت"),
    ("4346","صندوق ميفك ريت"),
    # ── الطاقة ──
    ("5110","الشركة السعودية للطاقة"),
    # ── الأغذية والزراعة ──
    ("6001","شركة حلواني إخوان"),("6002","شركة هرفي للخدمات الغذائية"),
    ("6004","شركة كاتريون للتموين"),
    ("6010","الشركة الوطنية للتنمية الزراعية"),("6012","شركة ريدان الغذائية"),
    ("6013","شركة الأعمال التطويرية الغذائية"),("6014","شركة الآمار الغذائية"),
    ("6015","أمريكانا للمطاعم العالمية"),("6016","شركة مطاعم بيت الشطيرة"),
    ("6017","شركة جاهز الدولية"),("6018","شركة الأندية للرياضة"),
    ("6019","شركة المسار الشامل للتعليم"),("6020","شركة القصيم القابضة"),
    ("6040","شركة تبوك للتنمية الزراعية"),("6050","الشركة السعودية للأسماك"),
    ("6060","شركة الشرقية للتنمية"),("6070","الجوف"),("6090","جازادكو"),
    # ── الاتصالات والتقنية ──
    ("7010","شركة الإتصالات السعودية"),("7020","شركة إتحاد إتصالات"),
    ("7030","شركة الإتصالات المتنقلة السعودية"),("7040","قو للإتصالات"),
    ("7205","شركة دار البلد لحلول الأعمال"),
]

seen_s = set()
UNIQUE_STOCKS = []
for sym, name in ALL_STOCKS:
    if sym not in seen_s:
        seen_s.add(sym)
        UNIQUE_STOCKS.append((sym, name))

# ─────────────────────────────────────────────────────────────
# 2. Session State
# ─────────────────────────────────────────────────────────────
for k, v in {
    "auth": False,
    "scan_results": [],
    "bt_results": {},
    "last_scan": None,
    "scan_count": 0,
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ─────────────────────────────────────────────────────────────
# 3. تسجيل الدخول
# ─────────────────────────────────────────────────────────────
if not st.session_state.auth:
    st.markdown("""
    <div style='display:flex;flex-direction:column;align-items:center;
                justify-content:center;height:60vh;gap:16px'>
      <h1 style='font-size:36px;font-weight:900;color:#0f172a;margin:0'>
        📡 RSI Divergence
      </h1>
      <p style='color:#64748b;font-size:15px;margin:0'>داشبورد اختبار الاستراتيجية</p>
    </div>
    """, unsafe_allow_html=True)
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

# ─────────────────────────────────────────────────────────────
# 4. API Client
# ─────────────────────────────────────────────────────────────
try:
    from sahmk import SahmkClient
    client = SahmkClient(api_key=API_KEY)
except Exception as e:
    st.error(f"❌ خطأ في الاتصال بـ API: {e}")
    st.stop()

# ─────────────────────────────────────────────────────────────
# 5. جلب البيانات
# ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def get_market():
    try:
        return client.market_summary()
    except:
        return None

@st.cache_data(ttl=30)
def get_quote(sym):
    try:
        result = client.quotes([sym])
        if result and result.quotes:
            return result.quotes[0]
    except:
        pass
    return None

@st.cache_data(ttl=300)
def get_intraday_5min(sym):
    """بيانات 5 دقائق"""
    try:
        h = client.intraday(sym, interval="5min")
        rows = []
        for item in h.data:
            if item.close and item.close > 0:
                rows.append({
                    "close": float(item.close),
                    "high":  float(item.high  or item.close),
                    "low":   float(item.low   or item.close),
                    "open":  float(item.open  or item.close),
                    "volume":float(item.volume or 0),
                })
        return pd.DataFrame(rows) if rows else pd.DataFrame()
    except:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def get_intraday_60min(sym):
    """
    بيانات 60 دقيقة — مبنية بطريقتين:
    1. نحاول API مباشرة مع from_date
    2. fallback: نجمع شموع الـ 5 دقائق يدوياً كل 12 شمعة = 60 دقيقة
    """
    # ── الطريقة 1: API مباشر مع تاريخ ──
    try:
        h = client.historical(sym, interval="60min", from_date="2024-01-01")
        rows = []
        for item in h.data:
            if item.close and item.close > 0:
                rows.append({
                    "close": float(item.close),
                    "high":  float(item.high  or item.close),
                    "low":   float(item.low   or item.close),
                    "open":  float(item.open  or item.close),
                    "volume":float(item.volume or 0),
                })
        if len(rows) >= 50:
            return pd.DataFrame(rows)
    except:
        pass

    # ── الطريقة 2: نجمع الـ 5 دقائق يدوياً ──
    try:
        h = client.intraday(sym, interval="5min")
        rows_5 = []
        for item in h.data:
            if item.close and item.close > 0:
                rows_5.append({
                    "close": float(item.close),
                    "high":  float(item.high  or item.close),
                    "low":   float(item.low   or item.close),
                    "open":  float(item.open  or item.close),
                    "volume":float(item.volume or 0),
                })
        if len(rows_5) < 12:
            return pd.DataFrame()
        # كل 12 شمعة × 5 دقائق = 60 دقيقة
        rows_60 = []
        chunk = 12
        for i in range(0, len(rows_5) - chunk + 1, chunk):
            group = rows_5[i:i+chunk]
            rows_60.append({
                "open":   group[0]["open"],
                "high":   max(r["high"]   for r in group),
                "low":    min(r["low"]    for r in group),
                "close":  group[-1]["close"],
                "volume": sum(r["volume"] for r in group),
            })
        return pd.DataFrame(rows_60) if rows_60 else pd.DataFrame()
    except:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_daily(sym):
    """بيانات يومية — مع timeout handling"""
    try:
        h = client.historical(sym, from_date="2024-01-01")
        rows = []
        for item in h.data:
            if item.close and item.close > 0:
                rows.append({
                    "close": float(item.close),
                    "high":  float(item.high  or item.close),
                    "low":   float(item.low   or item.close),
                    "open":  float(item.open  or item.close),
                    "volume":float(item.volume or 0),
                })
        return pd.DataFrame(rows) if rows else pd.DataFrame()
    except:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_daily_batch(syms_tuple):
    """جلب بيانات مجموعة أسهم مع cache مشترك"""
    results = {}
    for sym in syms_tuple:
        results[sym] = get_daily(sym)
    return results

def get_data_for_tf(sym, tf_key):
    """جلب البيانات بحسب التايم فريم"""
    if tf_key == "5min":
        return get_intraday_5min(sym)
    elif tf_key == "60min":
        return get_intraday_60min(sym)
    else:
        return get_daily(sym)

# ─────────────────────────────────────────────────────────────
# 6. المؤشرات
# ─────────────────────────────────────────────────────────────
def calc_rsi(closes_arr, period=14):
    """RSI — Wilder smoothing"""
    if len(closes_arr) < period + 1:
        return np.full(len(closes_arr), 50.0)
    closes = np.array(closes_arr, dtype=float)
    deltas = np.diff(closes)
    gains  = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)
    ag = gains[:period].mean()
    al = losses[:period].mean()
    rsi_vals = np.full(len(closes), 50.0)
    for i in range(period, len(closes)):
        ag = (ag * (period - 1) + gains[i-1]) / period
        al = (al * (period - 1) + losses[i-1]) / period
        rs = ag / al if al > 0 else 100.0
        rsi_vals[i] = 100 - 100 / (1 + rs)
    return rsi_vals

def calc_atr(highs, lows, closes, period=14):
    """ATR"""
    if len(closes) < period + 1:
        return 0.0
    trs = []
    for i in range(1, len(closes)):
        tr = max(highs[i] - lows[i],
                 abs(highs[i] - closes[i-1]),
                 abs(lows[i]  - closes[i-1]))
        trs.append(tr)
    if len(trs) < period:
        return 0.0
    return round(sum(trs[-period:]) / period, 4)



def vol_is_confirmed(volumes, i, mult=None):
    """
    حجم التداول عند نقطة الـ divergence لازم أعلى من المتوسط
    mult: مضاعف المتوسط المطلوب (افتراضي VOL_CONFIRM_MULT)
    """
    if mult is None:
        mult = VOL_CONFIRM_MULT
    period = 20
    if i < period:
        return True, 0.0  # بيانات قليلة — لا نفلتر
    avg_vol = np.mean(volumes[i-period:i])
    if avg_vol == 0:
        return True, 0.0
    ratio = volumes[i] / avg_vol
    return ratio >= mult, round(ratio, 2)

def calc_macd(closes, fast=12, slow=26, signal=9):
    """MACD — EMA fast - EMA slow + Signal line"""
    if len(closes) < slow + signal:
        return 0.0, 0.0, 0.0
    closes = np.array(closes, dtype=float)

    def ema(arr, period):
        k = 2.0 / (period + 1)
        result = np.zeros(len(arr))
        result[0] = arr[0]
        for i in range(1, len(arr)):
            result[i] = arr[i] * k + result[i-1] * (1 - k)
        return result

    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return round(macd_line[-1], 4), round(signal_line[-1], 4), round(histogram[-1], 4)

def macd_is_bullish(closes, i):
    """
    MACD bullish عند نقطة i:
    1. MACD Line تتحسن (histogram يرتفع مقارنة بـ 3 شموع قبل)
    2. MACD تحت الصفر أو يقترب منه (لسه في منطقة شراء)
    3. Signal line تقترب من MACD أو MACD يتجاوزها
    """
    if i < 35:
        return False, 0.0, 0.0, 0.0
    c = closes[:i+1]
    macd, sig, hist = calc_macd(c)
    # نحسب histogram قبل 3 شموع للمقارنة
    if i >= 38:
        _, _, hist_prev = calc_macd(closes[:i-2])
    else:
        hist_prev = hist - 0.001

    improving   = hist > hist_prev          # histogram يتحسن
    not_overbought = macd < 0.5             # MACD مش في ذروة صعود
    crossing    = macd > sig or (hist > 0)  # تجاوز أو إيجابي

    bullish = improving and not_overbought
    return bullish, round(macd, 4), round(sig, 4), round(hist, 4)

def is_swing_low(lows, i, n=LOOKBACK_SWING):
    """هل هذه الشمعة قاع محلي؟"""
    if i < n or i >= len(lows) - n:
        return False
    return all(lows[i] <= lows[i-k] for k in range(1, n+1)) and \
           all(lows[i] <= lows[i+k] for k in range(1, n+1))

def is_swing_high(highs, i, n=LOOKBACK_SWING):
    """هل هذه الشمعة قمة محلية؟"""
    if i < n or i >= len(highs) - n:
        return False
    return all(highs[i] >= highs[i-k] for k in range(1, n+1)) and \
           all(highs[i] >= highs[i+k] for k in range(1, n+1))

# ─────────────────────────────────────────────────────────────
# 6b. أنماط Price Action — تأكيد إضافي للـ Divergence
# ─────────────────────────────────────────────────────────────

def detect_pa_pattern(opens, highs, lows, closes, i):
    """
    يكتشف أنماط PA البولشية عند نقطة الـ divergence
    يرجع: (اسم النمط, قوة النمط 1-3)
    """
    if i < 1 or i >= len(closes):
        return "لا نمط", 0

    o, h, l, c = opens[i], highs[i], lows[i], closes[i]
    po, ph, pl, pc = opens[i-1], highs[i-1], lows[i-1], closes[i-1]

    body      = abs(c - o)
    full_range = h - l
    if full_range == 0:
        return "لا نمط", 0

    upper_wick = h - max(o, c)
    lower_wick = min(o, c) - l
    body_pct   = body / full_range

    # ── Pin Bar / Hammer ──
    # جسم صغير + ذيل سفلي طويل (> 60% من الشمعة) + ذيل علوي صغير
    if (lower_wick >= full_range * 0.6
            and body_pct <= 0.35
            and upper_wick <= full_range * 0.15
            and c > o):  # إغلاق صاعد
        return "🔨 Hammer", 3

    # ── Bullish Engulfing ──
    # الشمعة الحالية تبتلع الشمعة السابقة بالكامل
    if (pc > po          # الشمعة السابقة هابطة
            and c > o    # الشمعة الحالية صاعدة
            and c > ph   # إغلاق فوق أعلى الشمعة السابقة
            and o < pl): # فتح تحت أدنى الشمعة السابقة
        return "🟢 Engulfing", 3

    # ── Bullish Engulfing جزئي ──
    if (pc > po and c > o and c > pc and o <= po):
        return "🟢 Engulfing جزئي", 2

    # ── Doji عند القاع (تردد = فرصة انعكاس) ──
    if body_pct <= 0.15 and full_range > 0:
        return "➖ Doji", 1

    # ── Morning Star (3 شموع) ──
    if i >= 2:
        o2, h2, l2, c2 = opens[i-2], highs[i-2], lows[i-2], closes[i-2]
        body2 = abs(c2 - o2)
        body_range2 = h2 - l2
        if (c2 < o2                          # شمعة 1 هابطة
                and body_pct <= 0.3           # شمعة 2 صغيرة (نجمة)
                and c > o                     # شمعة 3 صاعدة
                and c > (o2 + c2) / 2         # إغلاق فوق منتصف الشمعة 1
                and body2 > 0 and body_range2 > 0
                and (body2/body_range2) > 0.4):
            return "⭐ Morning Star", 3

    # ── شمعة صاعدة قوية ──
    if c > o and body_pct >= 0.6 and c > pc:
        return "📈 شمعة صاعدة", 2

    # ── لا نمط واضح ──
    if c > o:
        return "↑ صاعدة", 1
    return "↓ هابطة", 0


def pa_score(pattern_name, pattern_strength):
    """يحول نمط PA إلى نقطة تأكيد — الأقوى يأخذ أولوية في الفلترة"""
    return pattern_strength  # 0=لا تأكيد، 1=ضعيف، 2=متوسط، 3=قوي

# ─────────────────────────────────────────────────────────────
# 7. كاشف الـ RSI Divergence
# ─────────────────────────────────────────────────────────────
def find_divergences(df):
    """
    Bullish  Divergence: سعر يصنع قاعاً أدنى + RSI يصنع قاعاً أعلى → BUY
    Bearish  Divergence: سعر يصنع قمة أعلى  + RSI يصنع قمة أدنى  → تحذير
    + تأكيد PA: Hammer / Engulfing / Morning Star
    """
    if df.empty or len(df) < RSI_PERIOD + LOOKBACK_SWING + LOOKBACK_DIV:
        return []

    closes  = df["close"].values
    highs   = df["high"].values
    lows    = df["low"].values
    opens   = df["open"].values   if "open"   in df.columns else closes.copy()
    volumes = df["volume"].values if "volume" in df.columns else np.ones(len(closes))
    rsi    = calc_rsi(closes, RSI_PERIOD)
    atr    = calc_atr(highs, lows, closes, ATR_PERIOD)

    divs = []
    n = len(closes)

    for i in range(LOOKBACK_SWING + LOOKBACK_DIV, n - LOOKBACK_SWING):
        # ── Bullish Divergence ──
        if is_swing_low(lows, i, LOOKBACK_SWING):
            # ابحث عن قاع سابق في نطاق LOOKBACK_DIV
            for j in range(i - LOOKBACK_DIV, i - LOOKBACK_SWING):
                if j < 0: continue
                if is_swing_low(lows, j, LOOKBACK_SWING):
                    price_lower = lows[i] < lows[j] * (1 - MIN_PRICE_DIFF/100)
                    rsi_higher  = rsi[i]   > rsi[j] + MIN_RSI_DIFF
                    rsi_os      = rsi[j]   < RSI_OS  # القاع القديم في منطقة ذروة البيع
                    rsi_curr_ok = rsi[i] < BULLISH_RSI_MAX  # [v1.1] فلتر RSI الحالي
                    if price_lower and rsi_higher and rsi_os and rsi_curr_ok:
                        # ── PA تأكيد — شرط إلزامي ──
                        pa_name, pa_str = detect_pa_pattern(opens, highs, lows, closes, i)
                        if pa_str == 0:
                            break  # لا نمط = لا إشارة
                        # ── حجم التداول — شرط إلزامي ──
                        vol_ok, vol_ratio = vol_is_confirmed(volumes, i)
                        if not vol_ok:
                            break  # حجم ضعيف = لا إشارة
                        entry_i = min(i + CONFIRM_CANDLES, n - 1)
                        entry_p = closes[entry_i]
                        sl      = round(entry_p - atr * ATR_SL_MULT, 3)
                        t1      = round(entry_p + atr * ATR_T1_MULT, 3)
                        t2      = round(entry_p + atr * ATR_T2_MULT, 3)
                        sig_label = "BUY ⭐ قوي" if pa_str >= 2 else "BUY 🟢"
                        divs.append({
                            "type":       "bullish",
                            "signal":     sig_label,
                            "index":      i,
                            "entry_index":entry_i,
                            "price":      round(closes[i], 3),
                            "entry_price":round(entry_p, 3),
                            "stop_loss":  sl,
                            "target1":    t1,
                            "target2":    t2,
                            "rsi_now":    round(rsi[i], 1),
                            "rsi_prev":   round(rsi[j], 1),
                            "rsi_diff":   round(rsi[i] - rsi[j], 1),
                            "price_diff": round((lows[j] - lows[i]) / lows[j] * 100, 2),
                            "atr":        round(atr, 4),
                            "t1_pct":     round((t1 - entry_p) / entry_p * 100, 2),
                            "t2_pct":     round((t2 - entry_p) / entry_p * 100, 2),
                            "sl_pct":     round((entry_p - sl)  / entry_p * 100, 2),
                            "prev_index": j,
                            "pa_pattern": pa_name,
                            "pa_strength":pa_str,
                            "vol_ratio":  vol_ratio,
                        })
                        break  # أقوى divergence فقط

        # ── Bearish Divergence ──
        if is_swing_high(highs, i, LOOKBACK_SWING):
            for j in range(i - LOOKBACK_DIV, i - LOOKBACK_SWING):
                if j < 0: continue
                if is_swing_high(highs, j, LOOKBACK_SWING):
                    price_higher = highs[i] > highs[j] * (1 + MIN_PRICE_DIFF/100)
                    rsi_lower    = rsi[i]   < rsi[j] - MIN_RSI_DIFF
                    rsi_ob       = rsi[j]   > RSI_OB  # القمة القديمة في منطقة ذروة الشراء
                    if price_higher and rsi_lower and rsi_ob:
                        entry_i = min(i + CONFIRM_CANDLES, n - 1)
                        entry_p = closes[entry_i]
                        sl      = round(entry_p + atr * ATR_SL_MULT, 3)
                        t1      = round(entry_p - atr * ATR_T1_MULT, 3)
                        t2      = round(entry_p - atr * ATR_T2_MULT, 3)
                        divs.append({
                            "type":       "bearish",
                            "signal":     "WAIT ⚠️",   # السوق السعودي لا short — نتجنب الدخول
                            "index":      i,
                            "entry_index":entry_i,
                            "price":      round(closes[i], 3),
                            "entry_price":round(entry_p, 3),
                            "stop_loss":  sl,
                            "target1":    t1,
                            "target2":    t2,
                            "rsi_now":    round(rsi[i], 1),
                            "rsi_prev":   round(rsi[j], 1),
                            "rsi_diff":   round(rsi[j] - rsi[i], 1),
                            "price_diff": round((highs[i] - highs[j]) / highs[j] * 100, 2),
                            "atr":        round(atr, 4),
                            "t1_pct":     round((entry_p - t1) / entry_p * 100, 2),
                            "t2_pct":     round((entry_p - t2) / entry_p * 100, 2),
                            "sl_pct":     round((sl - entry_p)  / entry_p * 100, 2),
                            "prev_index": j,
                        })
                        break

    return divs

def get_latest_divergence(divs, closes):
    """أحدث divergence فقط — القريب من الآن"""
    if not divs: return None
    n = len(closes)
    # نختار الأحدث ضمن آخر 15 شمعة
    recent = [d for d in divs if d["entry_index"] >= n - 15]
    if not recent: return None
    return sorted(recent, key=lambda x: x["entry_index"], reverse=True)[0]

# ─────────────────────────────────────────────────────────────
# 8. Backtest RSI Divergence
# ─────────────────────────────────────────────────────────────
def backtest_rsi_div(sym, name, df):
    """
    Backtest على البيانات المتاحة:
    - يكتشف كل Divergences التاريخية
    - يقيس: هل وصل الهدف؟ في كم شمعة؟
    - يسجّل نمط PA لكل إشارة
    """
    if df.empty or len(df) < RSI_PERIOD + LOOKBACK_SWING * 2 + LOOKBACK_DIV:
        return []

    closes  = df["close"].values
    highs   = df["high"].values
    lows    = df["low"].values
    opens   = df["open"].values   if "open"   in df.columns else closes.copy()
    volumes = df["volume"].values if "volume" in df.columns else np.ones(len(closes))
    rsi    = calc_rsi(closes, RSI_PERIOD)

    trades = []
    used_indices = set()  # تجنب تكرار الإشارة في نفس المنطقة

    for i in range(LOOKBACK_SWING + LOOKBACK_DIV, len(closes) - LOOKBACK_SWING - 10):
        if i in used_indices: continue

        atr = calc_atr(highs[:i+1], lows[:i+1], closes[:i+1], ATR_PERIOD)
        if atr == 0: continue

        # ── Bullish Divergence ──
        if is_swing_low(lows, i, LOOKBACK_SWING):
            for j in range(i - LOOKBACK_DIV, i - LOOKBACK_SWING):
                if j < 0: continue
                if is_swing_low(lows, j, LOOKBACK_SWING):
                    price_lower = lows[i] < lows[j] * (1 - MIN_PRICE_DIFF/100)
                    rsi_higher  = rsi[i]  > rsi[j] + MIN_RSI_DIFF
                    rsi_os      = rsi[j]  < RSI_OS
                    rsi_curr_ok = rsi[i] < BULLISH_RSI_MAX  # [v1.1]
                    if price_lower and rsi_higher and rsi_os and rsi_curr_ok:
                        # ── PA — شرط إلزامي ──
                        pa_name, pa_str = detect_pa_pattern(opens, highs, lows, closes, i)
                        if pa_str == 0:
                            break  # لا نمط = لا إشارة
                        # ── حجم التداول — شرط إلزامي ──
                        vol_ok, vol_ratio = vol_is_confirmed(volumes, i)
                        if not vol_ok:
                            break  # حجم ضعيف = لا إشارة
                        entry_i = min(i + CONFIRM_CANDLES, len(closes) - 1)
                        entry_p = closes[entry_i]
                        sl      = entry_p - atr * ATR_SL_MULT
                        t1      = entry_p + atr * ATR_T1_MULT
                        t2      = entry_p + atr * ATR_T2_MULT

                        # قياس النتيجة خلال 20 شمعة
                        outcome = "⏳ لم يصل"
                        exit_candle = None
                        pnl_pct     = 0.0
                        for k in range(entry_i + 1, min(entry_i + 21, len(closes))):
                            if highs[k] >= t2:
                                outcome = "✅ هدف 2"
                                pnl_pct = round((t2 - entry_p) / entry_p * 100, 2)
                                exit_candle = k - entry_i
                                break
                            elif highs[k] >= t1:
                                outcome = "🟡 هدف 1"
                                pnl_pct = round((t1 - entry_p) / entry_p * 100, 2)
                                exit_candle = k - entry_i
                                break
                            elif lows[k] <= sl:
                                outcome = "❌ Stop"
                                pnl_pct = round((sl - entry_p) / entry_p * 100, 2)
                                exit_candle = k - entry_i
                                break

                        if outcome == "⏳ لم يصل" and entry_i + 20 < len(closes):
                            pnl_pct = round((closes[entry_i + 20] - entry_p) / entry_p * 100, 2)

                        trades.append({
                            "الرمز":        sym,
                            "الاسم":        name,
                            "النوع":        "Bullish 📈",
                            "نمط PA":       pa_name,
                            "قوة PA":       pa_str,
                            "حجم×":         vol_ratio,
                            "سعر الدخول":  round(entry_p, 3),
                            "RSI الآن":    round(rsi[i], 1),
                            "RSI السابق":  round(rsi[j], 1),
                            "فرق RSI":     round(rsi[i] - rsi[j], 1),
                            "ATR":          round(atr, 4),
                            "هدف1%":       round((t1 - entry_p) / entry_p * 100, 2),
                            "هدف2%":       round((t2 - entry_p) / entry_p * 100, 2),
                            "وقف%":        round((entry_p - sl) / entry_p * 100, 2),
                            "النتيجة":      outcome,
                            "ربح/خسارة%":  pnl_pct,
                            "شموع_للخروج": exit_candle,
                            "ناجحة":       1 if ("✅" in outcome or "🟡" in outcome) else 0,
                        })
                        used_indices.update(range(i - 3, i + 4))
                        break

        # ── Bearish Divergence — نسجل للمعرفة فقط (لا short) ──
        if is_swing_high(highs, i, LOOKBACK_SWING):
            for j in range(i - LOOKBACK_DIV, i - LOOKBACK_SWING):
                if j < 0: continue
                if is_swing_high(highs, j, LOOKBACK_SWING):
                    price_higher = highs[i] > highs[j] * (1 + MIN_PRICE_DIFF/100)
                    rsi_lower    = rsi[i]   < rsi[j] - MIN_RSI_DIFF
                    rsi_ob       = rsi[j]   > RSI_OB
                    if price_higher and rsi_lower and rsi_ob:
                        # نقيس التراجع التالي فقط للدراسة
                        entry_p = closes[min(i + CONFIRM_CANDLES, len(closes)-1)]
                        sl      = entry_p + atr * ATR_SL_MULT
                        t1      = entry_p - atr * ATR_T1_MULT
                        t2      = entry_p - atr * ATR_T2_MULT
                        outcome = "⏳ لم يصل"
                        pnl_pct = 0.0
                        exit_candle = None
                        entry_i = min(i + CONFIRM_CANDLES, len(closes) - 1)
                        for k in range(entry_i + 1, min(entry_i + 21, len(closes))):
                            if lows[k] <= t2:
                                outcome = "✅ انخفض للهدف 2"
                                pnl_pct = round((entry_p - t2) / entry_p * 100, 2)
                                exit_candle = k - entry_i; break
                            elif lows[k] <= t1:
                                outcome = "🟡 انخفض للهدف 1"
                                pnl_pct = round((entry_p - t1) / entry_p * 100, 2)
                                exit_candle = k - entry_i; break
                            elif highs[k] >= sl:
                                outcome = "❌ لم يتراجع"
                                exit_candle = k - entry_i; break
                        trades.append({
                            "الرمز":       sym,
                            "الاسم":       name,
                            "النوع":       "Bearish ⚠️",
                            "سعر الدخول": round(entry_p, 3),
                            "RSI الآن":   round(rsi[i], 1),
                            "RSI السابق": round(rsi[j], 1),
                            "فرق RSI":    round(rsi[j] - rsi[i], 1),
                            "ATR":         round(atr, 4),
                            "هدف1%":      round((entry_p - t1) / entry_p * 100, 2),
                            "هدف2%":      round((entry_p - t2) / entry_p * 100, 2),
                            "وقف%":       round((sl - entry_p) / entry_p * 100, 2),
                            "النتيجة":     outcome,
                            "ربح/خسارة%": pnl_pct,
                            "شموع_للخروج":exit_candle,
                            "ناجحة":      1 if ("✅" in outcome or "🟡" in outcome) else 0,
                        })
                        used_indices.update(range(i - 3, i + 4))
                        break

    return trades

# ─────────────────────────────────────────────────────────────
# 9. مسح جميع الأسهم
# ─────────────────────────────────────────────────────────────
def scan_all(tf_key, max_stocks=None):
    stocks = UNIQUE_STOCKS[:max_stocks] if max_stocks else UNIQUE_STOCKS
    results = []
    prog  = st.progress(0)
    stat  = st.empty()
    total = len(stocks)

    for i, (sym, name) in enumerate(stocks):
        stat.text(f"⏳ {i+1}/{total}: {sym} — {name}")
        prog.progress((i+1)/total)
        try:
            df = get_data_for_tf(sym, tf_key)
            if df.empty or len(df) < RSI_PERIOD + LOOKBACK_SWING + LOOKBACK_DIV:
                continue
            divs = find_divergences(df)
            latest = get_latest_divergence(divs, df["close"].values)
            if latest:
                q = get_quote(sym)
                cur_price = float(getattr(q, "price", 0) or 0) if q else latest["entry_price"]
                change_pct = float(getattr(q, "change_percent", 0) or 0) if q else 0.0
                results.append({
                    "الرمز":          sym,
                    "الاسم":          name,
                    "الإشارة":        latest["signal"],
                    "النوع":          "Bullish 📈" if latest["type"] == "bullish" else "Bearish ⚠️",
                    "السعر الحالي":   cur_price,
                    "التغيير%":       round(change_pct, 2),
                    "سعر الدخول":    latest["entry_price"],
                    "هدف 1":         latest["target1"],
                    "هدف%1":         f"+{latest['t1_pct']}%",
                    "هدف 2":         latest["target2"],
                    "هدف%2":         f"+{latest['t2_pct']}%",
                    "وقف الخسارة":   latest["stop_loss"],
                    "وقف%":          f"-{latest['sl_pct']}%",
                    "RSI الآن":      latest["rsi_now"],
                    "RSI السابق":    latest["rsi_prev"],
                    "فرق RSI":       latest["rsi_diff"],
                    "ATR":            latest["atr"],
                    "pa_pattern":     latest.get("pa_pattern", "—"),
                    "pa_strength":    latest.get("pa_strength", 0),
                    "vol_ratio":      latest.get("vol_ratio", 0),
                    "_type":          latest["type"],
                })
        except Exception as e:
            pass

    prog.empty()
    stat.empty()
    return results

# ─────────────────────────────────────────────────────────────
# 10. CSS
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;600;700;900&display=swap');

* { font-family: 'IBM Plex Sans Arabic', sans-serif !important; }

.stApp { background: #f1f5f9; }

/* بطاقة إشارة */
.div-card {
    background: #fff;
    border-radius: 14px;
    padding: 0;
    margin-bottom: 12px;
    overflow: hidden;
    box-shadow: 0 1px 4px rgba(0,0,0,0.08);
}
.div-card-bull .div-card-head { border-top: 4px solid #16a34a; background: #f0fdf4; }
.div-card-bear .div-card-head { border-top: 4px solid #dc2626; background: #fff1f2; }
.div-card-head {
    padding: 12px 16px 10px;
    display: flex; justify-content: space-between; align-items: flex-start;
}
.div-sym   { font-size: 16px; font-weight: 800; color: #0f172a; }
.div-name  { font-size: 12px; color: #64748b; margin-top: 2px; }
.div-sig   { font-size: 13px; font-weight: 700; }
.div-body  { padding: 10px 16px 14px; display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; }
.div-cell  { }
.div-label { font-size: 11px; color: #94a3b8; margin-bottom: 3px; }
.div-val   { font-size: 14px; font-weight: 700; color: #0f172a; }
.div-val-g { color: #16a34a; }
.div-val-r { color: #dc2626; }
.div-val-b { color: #1d4ed8; }
.div-rsi   { padding: 8px 16px 12px; background: #f8fafc; font-size: 12px; color: #475569; }

/* شريط أعلى */
.top-bar {
    background: #0f172a; color: #e2e8f0;
    border-radius: 14px; padding: 14px 24px;
    display: flex; gap: 28px; align-items: center;
    flex-wrap: wrap; margin-bottom: 16px;
}
.tb-item { text-align: center; }
.tb-label { font-size: 11px; color: #64748b; margin-bottom: 4px; }
.tb-val   { font-size: 20px; font-weight: 800; }
.tb-sub   { font-size: 11px; color: #94a3b8; }

/* شريط نتائج */
.results-bar {
    display: flex; gap: 12px; flex-wrap: wrap;
    margin-bottom: 14px;
}
.rb-item {
    background: #fff; border-radius: 10px;
    padding: 10px 18px; flex: 1; min-width: 100px;
    text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.07);
}
.rb-num   { font-size: 26px; font-weight: 900; color: #0f172a; }
.rb-label { font-size: 11px; color: #64748b; margin-top: 2px; }

.stTabs [data-baseweb="tab"] { font-weight: 700; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# 11. Auto-refresh & حالة السوق
# ─────────────────────────────────────────────────────────────
st_autorefresh(interval=60_000, key="autorefresh")

now      = now_riyadh()
now_mins = now.hour * 60 + now.minute
weekday  = now.weekday()
is_workday     = weekday in [6, 0, 1, 2, 3]
market_open    = is_workday and 600 <= now_mins < 900
market = get_market()
tasi_change = float(getattr(market, "index_change_percent", 0) or 0) if market else 0.0
tasi_value  = float(getattr(market, "index_value",  0) or 0) if market else 0.0
tasi_up     = int(getattr(market, "advancing", 0) or 0)   if market else 0
tasi_down   = int(getattr(market, "declining", 0) or 0)   if market else 0

# ─────────────────────────────────────────────────────────────
# 12. الهيدر
# ─────────────────────────────────────────────────────────────
st.markdown("""
<div style='padding:16px 0 10px'>
  <h1 style='margin:0;font-size:26px;font-weight:900;color:#0f172a'>
    📡 RSI Divergence — اختبار الاستراتيجية
  </h1>
  <p style='margin:4px 0 0;font-size:13px;color:#64748b'>
    السوق السعودي — الدخول عند اختلاف الاتجاه بين السعر و RSI
  </p>
</div>
""", unsafe_allow_html=True)

# ── شريط TASI ──
tasi_c = "#22c55e" if tasi_change >= 0 else "#ef4444"
status_lbl = "🟢 مفتوح" if market_open else "🔴 مغلق"
st.markdown(f"""
<div class='top-bar'>
  <div class='tb-item'>
    <div class='tb-label'>تاسي</div>
    <div class='tb-val'>{tasi_value:,.0f}</div>
    <div class='tb-sub' style='color:{tasi_c};font-weight:700'>{tasi_change:+.2f}%</div>
  </div>
  <div class='tb-item'>
    <div class='tb-label'>صاعد / هابط</div>
    <div class='tb-val'><span style='color:#22c55e'>{tasi_up}</span> / <span style='color:#ef4444'>{tasi_down}</span></div>
  </div>
  <div class='tb-item'>
    <div class='tb-label'>السوق</div>
    <div class='tb-val' style='font-size:16px'>{status_lbl}</div>
    <div class='tb-sub'>{now.strftime("%H:%M")}</div>
  </div>
  <div class='tb-item'>
    <div class='tb-label'>الاستراتيجية</div>
    <div class='tb-val' style='font-size:13px'>RSI Divergence</div>
    <div class='tb-sub'>RSI {RSI_PERIOD} | ATR SL ×{ATR_SL_MULT}</div>
  </div>
  <div class='tb-item'>
    <div class='tb-label'>الإعدادات</div>
    <div class='tb-val' style='font-size:12px'>OB {RSI_OB} / OS {RSI_OS}</div>
    <div class='tb-sub'>T1 ×{ATR_T1_MULT} | T2 ×{ATR_T2_MULT}</div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# 13. التابات الرئيسية
# ─────────────────────────────────────────────────────────────
tab_live, tab_bt, tab_settings = st.tabs([
    "⚡ مسح حي — RSI Divergence",
    "🧪 Backtest — اختبار الاستراتيجية",
    "⚙️ الإعدادات",
])

# ═══════════════════════════════════════════════════════════
# TAB 1 — المسح الحي
# ═══════════════════════════════════════════════════════════
with tab_live:
    st.markdown("### ⚡ مسح RSI Divergence الآن")

    col_tf, col_scope, col_run = st.columns([2, 2, 1])
    with col_tf:
        tf_label = st.selectbox("التايم فريم:", list(TIMEFRAMES.keys()))
        tf_key   = TIMEFRAMES[tf_label]
    with col_scope:
        scope = st.selectbox("النطاق:", ["أسهم سريعة (15 سهم)", "كل الأسهم (200+ سهم)"])
    with col_run:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        run_scan = st.button("🔍 مسح الآن", type="primary", use_container_width=True)

    if run_scan:
        max_s = 15 if "سريع" in scope else None
        with st.spinner(f"جاري مسح الأسهم على {tf_label}..."):
            results = scan_all(tf_key, max_s)
        st.session_state.scan_results = results
        st.session_state.last_scan    = now.strftime("%H:%M:%S")
        st.session_state.scan_count  += 1

    results = st.session_state.scan_results
    if results:
        df_res  = pd.DataFrame(results)
        bull    = df_res[df_res["_type"] == "bullish"]
        bear    = df_res[df_res["_type"] == "bearish"]
        last_t  = st.session_state.last_scan or "—"

        # ── إحصائيات ──
        st.markdown(f"""
        <div class='results-bar'>
          <div class='rb-item'>
            <div class='rb-num'>{len(results)}</div>
            <div class='rb-label'>إجمالي الإشارات</div>
          </div>
          <div class='rb-item'>
            <div class='rb-num' style='color:#16a34a'>{len(bull)}</div>
            <div class='rb-label'>Bullish 📈</div>
          </div>
          <div class='rb-item'>
            <div class='rb-num' style='color:#dc2626'>{len(bear)}</div>
            <div class='rb-label'>Bearish ⚠️</div>
          </div>
          <div class='rb-item'>
            <div class='rb-num' style='font-size:16px'>{last_t}</div>
            <div class='rb-label'>آخر مسح</div>
          </div>
        </div>
        """, unsafe_allow_html=True)

        # ── عرض البطاقات ──
        filter_type = st.radio("عرض:", ["الكل", "Bullish فقط", "Bearish فقط"], horizontal=True)

        show_res = results
        if filter_type == "Bullish فقط":
            show_res = [r for r in results if r["_type"] == "bullish"]
        elif filter_type == "Bearish فقط":
            show_res = [r for r in results if r["_type"] == "bearish"]

        # عرض بطاقات — عمودين
        cols = st.columns(2)
        for i, r in enumerate(show_res):
            card_cls = "div-card-bull" if r["_type"] == "bullish" else "div-card-bear"
            chg_col  = "#16a34a" if r["التغيير%"] >= 0 else "#dc2626"
            pa_info  = f" | PA: {r.get('pa_pattern','—')} (قوة {r.get('pa_strength',0)})" if r.get('pa_pattern') else ""
            vol_info = f" | حجم×: {r.get('vol_ratio',0)}" if r.get('vol_ratio') else ""
            rsi_info = f"RSI الآن: {r['RSI الآن']} | RSI السابق: {r['RSI السابق']} | فرق: +{r['فرق RSI']}{pa_info}{vol_info}"

            with cols[i % 2]:
                st.markdown(f"""
                <div class='div-card {card_cls}'>
                  <div class='div-card-head'>
                    <div>
                      <div class='div-sym'>{r['الرمز']} <span style='font-weight:400;font-size:13px;color:#475569'>{r['الاسم']}</span></div>
                      <div class='div-name'>{r['النوع']}</div>
                    </div>
                    <div>
                      <div class='div-sig'>{r['الإشارة']}</div>
                      <div style='font-size:12px;color:{chg_col};font-weight:600;text-align:right'>{r['التغيير%']:+.2f}%</div>
                    </div>
                  </div>
                  <div class='div-body'>
                    <div class='div-cell'>
                      <div class='div-label'>سعر الدخول</div>
                      <div class='div-val div-val-b'>{r['سعر الدخول']}</div>
                    </div>
                    <div class='div-cell'>
                      <div class='div-label'>هدف 1</div>
                      <div class='div-val div-val-g'>{r['هدف 1']} <small>{r['هدف%1']}</small></div>
                    </div>
                    <div class='div-cell'>
                      <div class='div-label'>هدف 2</div>
                      <div class='div-val div-val-g'>{r['هدف 2']} <small>{r['هدف%2']}</small></div>
                    </div>
                    <div class='div-cell'>
                      <div class='div-label'>وقف الخسارة</div>
                      <div class='div-val div-val-r'>{r['وقف الخسارة']} <small>{r['وقف%']}</small></div>
                    </div>
                    <div class='div-cell'>
                      <div class='div-label'>السعر الحالي</div>
                      <div class='div-val'>{r['السعر الحالي']}</div>
                    </div>
                    <div class='div-cell'>
                      <div class='div-label'>ATR</div>
                      <div class='div-val'>{r['ATR']}</div>
                    </div>
                  </div>
                  <div class='div-rsi'>📊 {rsi_info}</div>
                </div>
                """, unsafe_allow_html=True)

        # جدول كامل
        with st.expander("📋 جدول كامل"):
            show_cols = ["الرمز","الاسم","الإشارة","النوع","السعر الحالي","التغيير%",
                         "سعر الدخول","هدف 1","هدف%1","هدف 2","هدف%2",
                         "وقف الخسارة","وقف%","RSI الآن","RSI السابق","فرق RSI","ATR"]
            show_cols = [c for c in show_cols if c in df_res.columns]
            st.dataframe(df_res[show_cols], use_container_width=True)
            csv = df_res[show_cols].to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button("⬇️ CSV", csv, f"rsi_div_{now.strftime('%Y%m%d_%H%M')}.csv", "text/csv")
    else:
        st.info("اضغط 'مسح الآن' لاكتشاف إشارات RSI Divergence")

# ═══════════════════════════════════════════════════════════
# TAB 2 — Backtest
# ═══════════════════════════════════════════════════════════
with tab_bt:
    st.markdown("### 🧪 Backtest — اختبار RSI Divergence على البيانات التاريخية")
    st.markdown("""
    **المنهجية:**
    - يكتشف كل نقاط Divergence التاريخية لكل سهم
    - يقيس هل وصل الهدف خلال 20 شمعة؟
    - يحسب نسبة النجاح، R/R الفعلي، متوسط الشموع للهدف
    """)

    bc1, bc2, bc3, bc4 = st.columns(4)
    with bc1:
        bt_tf_label = st.selectbox("التايم فريم:", list(TIMEFRAMES.keys()), key="bt_tf")
        bt_tf_key   = TIMEFRAMES[bt_tf_label]
    with bc2:
        bt_scope = st.selectbox("النطاق:", ["كل الأسهم (200+ سهم)", "سريع (50 سهم)", "تجربة (15 سهم)"], key="bt_scope")
    with bc3:
        bt_type_filter = st.selectbox("نوع Divergence:", ["الكل", "Bullish فقط", "Bearish فقط"], key="bt_type")
    with bc4:
        st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)
        st.caption("💡 كل الأسهم = أبطأ لكن أشمل")

    run_bt = st.button("🚀 ابدأ Backtest", type="primary")

    if run_bt:
        if "تجربة" in bt_scope:
            stocks_bt = UNIQUE_STOCKS[:15]
        elif "50" in bt_scope:
            stocks_bt = UNIQUE_STOCKS[:50]
        else:
            stocks_bt = UNIQUE_STOCKS
        all_bt_trades = []

        prog  = st.progress(0)
        stat  = st.empty()
        total = len(stocks_bt)

        for i, (sym, name) in enumerate(stocks_bt):
            stat.text(f"⏳ {i+1}/{total}: {sym} — {name}")
            prog.progress((i+1)/total)
            try:
                df = get_data_for_tf(sym, bt_tf_key)
                if not df.empty:
                    trades = backtest_rsi_div(sym, name, df)
                    all_bt_trades.extend(trades)
            except:
                pass

        prog.empty()
        stat.empty()
        st.session_state.bt_results = {
            "trades": all_bt_trades,
            "tf":     bt_tf_label,
        }

    bt_data = st.session_state.bt_results
    if bt_data and bt_data.get("trades"):
        all_t = bt_data["trades"]

        # فلترة بحسب النوع
        if bt_type_filter == "Bullish فقط":
            all_t = [t for t in all_t if "Bullish" in t.get("النوع","")]
        elif bt_type_filter == "Bearish فقط":
            all_t = [t for t in all_t if "Bearish" in t.get("النوع","")]

        df_bt = pd.DataFrame(all_t)
        total_t   = len(df_bt)
        won_t     = df_bt["ناجحة"].sum()
        t2_count  = df_bt["النتيجة"].str.contains("هدف 2", na=False).sum()
        t1_count  = df_bt["النتيجة"].str.contains("هدف 1", na=False).sum()
        stop_count= df_bt["النتيجة"].str.contains("Stop", na=False).sum()
        pending   = df_bt["النتيجة"].str.contains("⏳", na=False).sum()
        win_rate  = round(won_t / total_t * 100, 1) if total_t > 0 else 0
        avg_win   = df_bt[df_bt["ناجحة"]==1]["ربح/خسارة%"].mean()
        avg_loss  = df_bt[df_bt["ناجحة"]==0]["ربح/خسارة%"].mean()
        avg_candles = df_bt[df_bt["شموع_للخروج"].notna()]["شموع_للخروج"].mean()

        st.divider()
        st.markdown(f"### 📊 نتائج Backtest — {bt_data['tf']}")

        # ── ملخص ──
        m1,m2,m3,m4,m5 = st.columns(5)
        m1.metric("إجمالي الإشارات", total_t)
        m2.metric("ناجحة ✅",  int(won_t))
        m3.metric("نسبة النجاح", f"{win_rate}%",
                  delta=f"{win_rate-50:+.1f}% عن العشوائي")
        m4.metric("R/R فعلي", f"{round(t2_count/(stop_count+1),2)}:1")
        m5.metric("⏳ معلقة", pending)

        m6,m7,m8,m9 = st.columns(4)
        m6.metric("✅ هدف 2", t2_count)
        m7.metric("🟡 هدف 1", t1_count)
        m8.metric("❌ Stop",  stop_count)
        m9.metric("متوسط شموع للخروج", f"{avg_candles:.1f}" if avg_candles == avg_candles else "—")

        m10,m11 = st.columns(2)
        m10.metric("متوسط ربح الناجحة", f"{avg_win:.2f}%" if avg_win==avg_win else "—")
        m11.metric("متوسط خسارة الفاشلة", f"{avg_loss:.2f}%" if avg_loss==avg_loss else "—")

        # ── حكم النموذج ──
        st.divider()
        if win_rate >= 60:
            st.success(f"🎯 الاستراتيجية ممتازة على {bt_data['tf']} — نسبة {win_rate}%")
        elif win_rate >= 50:
            st.warning(f"📊 الاستراتيجية جيدة — {win_rate}% مع R/R مناسب")
        elif win_rate >= 40:
            st.warning(f"⚠️ متوسطة — {win_rate}% — جرب تايم فريم آخر أو عدّل الإعدادات")
        else:
            st.error(f"❌ ضعيفة على هذا التايم فريم — {win_rate}% — غيّر الإعدادات")

        # ── تبويبات التفاصيل ──
        dt1, dt2, dt3, dt4, dt5 = st.tabs([
            "📋 كل الإشارات", "✅ الناجحة", "❌ الخاسرة",
            "📈 أداء الأسهم", "📊 مقارنة التايم فريمات"
        ])

        show_cols_bt = ["الرمز","الاسم","النوع","نمط PA","قوة PA","حجم×","سعر الدخول",
                        "RSI الآن","RSI السابق","فرق RSI",
                        "هدف1%","هدف2%","وقف%",
                        "النتيجة","ربح/خسارة%","شموع_للخروج"]
        show_cols_bt = [c for c in show_cols_bt if c in df_bt.columns]

        with dt1:
            st.dataframe(
                df_bt[show_cols_bt].sort_values("ربح/خسارة%", ascending=False),
                use_container_width=True, height=500
            )
            csv_bt = df_bt[show_cols_bt].to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button("⬇️ CSV", csv_bt, f"backtest_rsi_div.csv", "text/csv")

            # Excel
            bt_excel = io.BytesIO()
            with pd.ExcelWriter(bt_excel, engine="openpyxl") as bw:
                df_bt.to_excel(bw, sheet_name="كل الإشارات", index=False)
                df_bt[df_bt["ناجحة"]==1].to_excel(bw, sheet_name="الناجحة", index=False)
                df_bt[df_bt["ناجحة"]==0].to_excel(bw, sheet_name="الخاسرة", index=False)
                pd.DataFrame({
                    "المقياس": ["إجمالي","ناجحة","نسبة%","هدف2","هدف1","Stop","معلقة",
                                "متوسط ربح%","متوسط خسارة%","متوسط شموع"],
                    "القيمة":  [total_t, int(won_t), win_rate, t2_count, t1_count,
                                stop_count, pending,
                                round(avg_win,2) if avg_win==avg_win else 0,
                                round(avg_loss,2) if avg_loss==avg_loss else 0,
                                round(avg_candles,1) if avg_candles==avg_candles else 0]
                }).to_excel(bw, sheet_name="الملخص", index=False)
            bt_excel.seek(0)
            st.download_button("⬇️ Excel كامل", bt_excel.getvalue(),
                               f"backtest_rsi_div_{bt_tf_key}.xlsx",
                               "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        with dt2:
            won_df = df_bt[df_bt["ناجحة"]==1].sort_values("ربح/خسارة%", ascending=False)
            if not won_df.empty:
                st.success(f"{len(won_df)} إشارة ناجحة | متوسط: {won_df['ربح/خسارة%'].mean():.2f}%")
                st.dataframe(won_df[show_cols_bt], use_container_width=True)
            else:
                st.info("لا توجد إشارات ناجحة")

        with dt3:
            lost_df = df_bt[df_bt["ناجحة"]==0].sort_values("ربح/خسارة%")
            if not lost_df.empty:
                st.error(f"{len(lost_df)} إشارة خاسرة | متوسط: {lost_df['ربح/خسارة%'].mean():.2f}%")
                st.dataframe(lost_df[show_cols_bt], use_container_width=True)
            else:
                st.success("لا توجد إشارات خاسرة ✅")

        with dt4:
            if "الرمز" in df_bt.columns:
                stock_p = df_bt.groupby(["الرمز","الاسم"]).agg(
                    إشارات=("النتيجة","count"),
                    ناجحة=("ناجحة","sum"),
                    متوسط_ربح=("ربح/خسارة%","mean"),
                    أفضل=("ربح/خسارة%","max"),
                    أسوأ=("ربح/خسارة%","min"),
                ).reset_index()
                stock_p["نسبة%"] = (stock_p["ناجحة"] / stock_p["إشارات"] * 100).round(1)
                st.dataframe(
                    stock_p.sort_values("نسبة%", ascending=False),
                    use_container_width=True, height=500,
                    column_config={"نسبة%": st.column_config.ProgressColumn("نسبة%",min_value=0,max_value=100)}
                )

        with dt5:
            st.info("""
            **لمقارنة التايم فريمات:** شغّل الـ Backtest 3 مرات — مرة على كل تايم فريم —
            ثم قارن نسب النجاح والشموع المطلوبة للخروج.

            **توقعات مبدئية:**
            - 5 دقائق → إشارات كثيرة، ضجيج أكثر، احتمال نسبة أقل
            - 60 دقيقة → توازن جيد بين الكمية والجودة
            - يومي → إشارات أقل، جودة أعلى، يحتاج صبر
            """)

            # توزيع النتائج
            if not df_bt.empty:
                outcome_dist = df_bt.groupby("النتيجة").size().reset_index(name="عدد")
                outcome_dist["نسبة%"] = (outcome_dist["عدد"] / len(df_bt) * 100).round(1)
                st.dataframe(outcome_dist, use_container_width=True)

                # توزيع RSI
                st.markdown("**توزيع فرق RSI في الإشارات الناجحة:**")
                won_rsi = df_bt[df_bt["ناجحة"]==1]["فرق RSI"] if "فرق RSI" in df_bt.columns else pd.Series()
                if not won_rsi.empty:
                    st.markdown(f"""
                    - أقل فرق: `{won_rsi.min():.1f}`
                    - أكبر فرق: `{won_rsi.max():.1f}`
                    - المتوسط: `{won_rsi.mean():.1f}`
                    """)

                # ── تحليل PA ──
                if "نمط PA" in df_bt.columns and "قوة PA" in df_bt.columns:
                    st.divider()
                    st.markdown("**📊 أداء كل نمط PA:**")
                    pa_perf = df_bt.groupby("نمط PA").agg(
                        إشارات=("ناجحة","count"),
                        ناجحة=("ناجحة","sum"),
                        متوسط_ربح=("ربح/خسارة%","mean"),
                    ).reset_index()
                    pa_perf["نسبة%"] = (pa_perf["ناجحة"] / pa_perf["إشارات"] * 100).round(1)
                    pa_perf = pa_perf.sort_values("نسبة%", ascending=False)
                    st.dataframe(pa_perf, use_container_width=True,
                        column_config={"نسبة%": st.column_config.ProgressColumn("نسبة%",min_value=0,max_value=100)})

                    # إشارات PA قوية فقط (قوة >= 2)
                    if "قوة PA" in df_bt.columns:
                        strong_pa = df_bt[df_bt["قوة PA"] >= 2]
                        if not strong_pa.empty:
                            s_won  = strong_pa["ناجحة"].sum()
                            s_rate = round(s_won / len(strong_pa) * 100, 1)
                            all_rate = round(df_bt["ناجحة"].sum() / len(df_bt) * 100, 1)
                            st.markdown(f"""
                            **🔍 فلترة PA قوية (Hammer + Engulfing + Morning Star):**
                            - إشارات PA قوية: **{len(strong_pa)}** من {len(df_bt)}
                            - نسبة نجاحها: **{s_rate}%**
                            - مقارنة بالكل: **{all_rate}%**
                            - الفرق: **{s_rate - all_rate:+.1f}%** {"✅ PA تحسّن النتائج" if s_rate > all_rate else "⚠️ PA لم تحسّن"}
                            """)

# ═══════════════════════════════════════════════════════════
# TAB 3 — الإعدادات
# ═══════════════════════════════════════════════════════════
with tab_settings:
    st.markdown("### ⚙️ إعدادات الاستراتيجية")
    st.markdown("""
    هذه الإعدادات الحالية للاستراتيجية — عدّلها في الكود مباشرةً ثم أعد تشغيل التطبيق.
    """)

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown("#### RSI")
        st.info(f"""
        - **فترة RSI:** `{RSI_PERIOD}` شمعة
        - **ذروة الشراء (OB):** `{RSI_OB}` — للـ Bearish Divergence
        - **ذروة البيع (OS):** `{RSI_OS}` — للـ Bullish Divergence
        - **فلتر RSI الحالي (Bullish):** < `{BULLISH_RSI_MAX}` — يضمن منطقة ضعف ✅
        - **أقل فرق RSI:** `{MIN_RSI_DIFF}` نقطة
        """)

        st.markdown("#### التأكيد")
        st.info(f"""
        - **شموع التأكيد:** `{CONFIRM_CANDLES}` شمعة قبل الدخول
        - **نطاق البحث:** آخر `{LOOKBACK_DIV}` شمعة
        - **تحديد القمة/القاع:** `{LOOKBACK_SWING}` شمعة يميناً ويساراً
        """)

    with col_s2:
        st.markdown("#### ATR والأهداف")
        st.info(f"""
        - **فترة ATR:** `{ATR_PERIOD}` شمعة
        - **وقف الخسارة:** ATR × `{ATR_SL_MULT}` *(خُفّض من 2.0)*
        - **الهدف 1:** ATR × `{ATR_T1_MULT}` → R:R 1:1 *(خُفّض من 2.0)*
        - **الهدف 2:** ATR × `{ATR_T2_MULT}` → R:R 1:2 *(خُفّض من 3.5)*
        - **أقل تغيير سعري:** `{MIN_PRICE_DIFF}%`
        """)

        st.markdown("#### قواعد الإشارة")
        st.info(f"""
        - **Bullish Divergence:** سعر أدنى + RSI أعلى → **BUY**
        - **Bearish Divergence:** سعر أعلى + RSI أدنى → **WAIT** (لا short)
        - **الخروج الزمني (Backtest):** 20 شمعة إذا لم يصل للهدف
        """)

    st.divider()
    st.markdown("#### 📌 كيف تقرأ النتائج")
    st.markdown("""
    | المقياس | المعنى |
    |---------|--------|
    | **نسبة النجاح > 55%** | الاستراتيجية مربحة مع R:R 1:1.75 |
    | **متوسط شموع < 10** | الإشارة سريعة التحقق |
    | **فرق RSI > 5** | إشارة divergence قوية |
    | **Bullish على 60min يومي** | الأكثر موثوقية في السوق السعودي |
    """)

st.divider()
st.caption(f"📡 RSI Divergence v1.3 — RSI Div + PA + Volume — آخر مسح: {st.session_state.last_scan or '—'} | للمعلومات فقط، ليست توصية استثمارية")
