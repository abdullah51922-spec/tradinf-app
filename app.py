# ================================================================
# داشبورد — test14
# مسح شامل لكل الأسهم + كل المميزات + تقارير Excel يومية وأسبوعية
# التحسينات عن test12:
#   1. رفع MIN_SCORE إلى 65 وMIN_CONFIDENCE إلى 62 (تقليل الإشارات الوهمية)
#   2. شرط استثنائي إلزامي في get_signal — لا BUY بدون شيء غير طبيعي
#   3. القوة النسبية vs التاسي في نظام النقاط
#   4. Cooldown 5 أيام في الـ Backtest (نتائج أمينة)
#   5. طبقة الـ 60min كتأكيد اتجاه بين اليومي والـ 5min
#   6. نمط الحجم داخل الجلسة (3 فترات: افتتاح/منتصف/إغلاق)
#   7. Bid/Ask Spread في حساب سعر الدخول
# ================================================================

import streamlit as st
from streamlit_autorefresh import st_autorefresh
import pandas as pd
import sqlite3, os, io
from datetime import datetime, timedelta
import pytz

GROUP_TITLE = "النسخة الكاملة — test14"
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

ATR_RISK_MULT   = 1.5
ATR_T1_MULT     = 1.0
ATR_T2_MULT     = 2.5

MIN_SCORE       = 65   # ↑ من 55 — يمنع الأسهم العادية من الدخول
MIN_CONFIDENCE  = 62   # ↑ من 50 — يشترط ثقة حقيقية
MIN_SCORE_STR   = 78   # ↑ من 70 — BUY قوي فقط لما فيه شيء استثنائي فعلاً
MIN_CONF_STR    = 68   # ↑ من 60
MIN_LIQ         = 3
MIN_ATR_PCT     = 0.005
MIN_VOL_RATIO   = 0.6
MAX_CHANGE_NEG  = -1.5
BREAKOUT_CHANGE = 1.0
BREAKOUT_VOL    = 2.0
TONIGHT_VOL     = 1.5
TONIGHT_CLOSE   = 0.75
TONIGHT_RSI_MAX = 65
INTRADAY_TTL    = 300
INTRADAY_MIN_CANDLES = 14

DATA_DIR    = "data"
DAILY_DIR   = os.path.join(DATA_DIR, "daily_reports")
TONIGHT_DB  = os.path.join(DATA_DIR, "tonight_watchlist_test14.db")
SIGNALS_DB  = os.path.join(DATA_DIR, "signals_test14.db")
for d in [DATA_DIR, DAILY_DIR]:
    os.makedirs(d, exist_ok=True)

# ============================================================
# 2. قائمة الأسهم الكاملة — محقَّقة من API
# ============================================================

ALL_STOCKS = [
    # البنوك
    ("1010","بنك الرياض"),("1020","بنك الجزيرة"),("1030","البنك السعودي للإستثمار"),
    ("1050","بي اس اف"),("1060","البنك السعودي الأول"),("1080","العربي"),
    ("1120","مصرف الراجحي"),("1140","بنك البلاد"),("1150","مصرف الإنماء"),
    ("1180","البنك الأهلي السعودي"),("1111","شركة مجموعة تداول السعودية القابضة"),
    # التمويل
    ("1182","شركة أملاك العالمية للتمويل"),("1183","شركة سهل للتمويل"),
    # المواد الأساسية
    ("1201","شركة تكوين المتطورة للصناعات"),("1202","مبكو"),
    ("1210","شركة الصناعات الكيميائية الأساسية"),("1211","شركة التعدين العربية السعودية"),
    ("1212","مجموعة أسترا الصناعية"),("1213","شركة نسيج العالمية التجارية"),
    ("1214","شركة الحسن غازي إبراهيم شاكر"),
    ("1301","شركة إتحاد مصانع الأسلاك"),("1302","شركة بوان"),
    ("1303","شركة الصناعات الكهربائية"),("1304","شركة اليمامة للصناعات الحديدية"),
    ("1320","الشركة السعودية لأنابيب الصلب"),("1321","شركة أنابيب الشرق المتكاملة"),
    ("1322","شركة المصانع الكبرى للتعدين"),("1323","يو سي آي سي"),
    ("1324","شركة صالح عبدالعزيز الراشد وأولاده"),
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
    ("2223","شركة أرامكو السعودية لزيوت الأساس"),("2230","الشركة الكيميائية السعودية القابضة"),
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
    # الأسمنت
    ("3002","شركة أسمنت نجران"),("3003","أسمنت المدينة"),
    ("3004","شركة أسمنت المنطقة الشمالية"),("3005","شركة أسمنت ام القرى"),
    ("3007","شركة زهرة الواحة للتجارة"),("3008","شركة الكثيري القابضة"),
    ("3010","شركة الأسمنت العربية"),("3020","شركة أسمنت اليمامة"),
    ("3030","شركة الأسمنت السعودية"),("3040","شركة أسمنت القصيم"),
    ("3050","شركة أسمنت المنطقة الجنوبية"),("3060","شركة أسمنت ينبع"),
    ("3080","شركة أسمنت المنطقة الشرقية"),("3090","شركة أسمنت تبوك"),
    ("3091","شركة أسمنت الجوف"),("3092","شركة أسمنت الرياض"),
    # الرعاية الصحية
    ("4002","شركة المواساة للخدمات الطبية"),("4004","شركة دله للخدمات الصحية"),
    ("4005","الشركة الوطنية للرعاية الطبية"),("4007","شركة الحمادي القابضة"),
    ("4009","شركة الشرق الأوسط للرعاية الصحية"),
    ("4013","مجموعة الدكتور سليمان الحبيب"),("4014","شركة دار المعدات الطبية"),
    ("4015","شركة مصنع جمجوم للأدوية"),("4016","شركة الشرق الأوسط للصناعات الدوائية"),
    ("4017","فقيه الطبية"),("4018","الموسى"),("4019","الشركة الطبية التخصصية"),
    ("4021","شركة مجمع المركز الكندي الطبي"),
    # التجزئة
    ("4001","شركة أسواق عبدالله العثيم"),("4003","الشركة المتحدة للإلكترونيات"),
    ("4006","الشركة السعودية للتسويق"),("4008","الشركة السعودية للعدد والأدوات"),
    ("4011","شركة لازوردي للمجوهرات"),("4012","شركة ثوب الأصيل"),
    ("4050","الشركة السعودية لخدمات السيارات والمعدات"),("4051","شركة باعظيم التجارية"),
    ("4061","مجموعة أنعام الدولية القابضة"),("4190","شركة جرير للتسويق"),
    ("4191","أبو معطي"),("4192","شركة متاجر السيف"),("4193","نايس ون"),
    ("4194","شركة مجموعة منزل التسويق"),("4200","شركة الدريس للخدمات البترولية"),
    ("4240","سينومي ريتيل"),
    # العقارات
    ("4020","الشركة العقارية السعودية"),("4100","شركة مكة للإنشاء والتعمير"),
    ("4130","شركة الباحة للإستثمار والتنمية"),("4150","شركة الرياض للتعمير"),
    ("4220","إعمار المدينة الإقتصادية"),("4230","شركة البحر الأحمر العالمية"),
    ("4280","شركة المملكة القابضة"),("4300","شركة دار الأركان للتطوير العقاري"),
    ("4320","شركة الأندلس العقارية"),
    # ريت
    ("4330","صندوق الرياض ريت"),("4331","صندوق الجزيرة ريت"),
    ("4332","صندوق جدوى ريت الحرمين"),("4333","صندوق تعليم ريت"),
    ("4334","صندوق المعذر ريت"),("4335","صندوق مشاركة ريت"),
    ("4336","ملكية ريت"),("4337","صندوق العزيزية ريت"),
    ("4340","صندوق الراجحي ريت"),("4342","صندوق جدوى ريت السعودية"),
    ("4344","صندوق سدكو كابيتال ريت"),("4345","صندوق الإنماء ريت"),
    ("4346","صندوق ميفك ريت"),
    # ترفيه وخدمات
    ("1810","مجموعة سيرا القابضة"),("1820","شركة مجموعة بان القابضة"),
    ("1830","لجام للرياضة"),("4070","تهامة"),
    ("4071","الشركة العربية للتعهدات الفنية"),("4072","شركة مجموعة إم بي سي"),
    ("4090","شركة طيبة للإستثمار"),("4160","شركة ثمار التنمية القابضة"),
    ("4161","شركة بن داود القابضة"),("4162","شركة المنجم للأغذية"),
    ("4163","شركة الدواء للخدمات الطبية"),("4164","شركة النهدي الطبية"),
    ("4170","شركة المشروعات السياحية"),("4210","الأبحاث والإعلام"),
    ("4260","الشركة المتحدة الدولية للمواصلات"),
    ("4270","الشركة السعودية للطباعة والتغليف"),
    ("4290","شركة الخليج للتدريب والتعليم"),("4291","الوطنية للتعليم"),
    ("4292","شركة عطاء التعليمية"),
    # موارد بشرية ولوجستيك
    ("1831","شركة مهارة للموارد البشرية"),("1832","شركة صدر للخدمات اللوجستية"),
    ("1833","شركة الموارد للقوى البشرية"),("1834","الشركة السعودية لحلول القوى البشرية"),
    ("1835","تمكين"),("4080","شركة سناد القابضة"),
    ("4110","شركة باتك للإستثمار"),("4140","الشركة السعودية للصادرات الصناعية"),
    ("4141","شركة العمران للصناعة"),("4142","شركة مجموعة كابلات الرياض"),
    ("4143","شركة مجموعة التيسير"),("4144","شركة رؤوم التجارية"),
    ("4145","شركة العبيكان للزجاج"),("4146","شركة جاز العربية للخدمات"),
    ("4147","شركة اتحاد جروننفلدر سعدي"),("4148","شركة الوسائل الصناعية"),
    ("4180","مجموعة فتيحي القابضة"),("6004","شركة كاتريون للتموين"),
    # النقل
    ("4030","الشركة الوطنية السعودية للنقل البحري"),
    ("4031","الشركة السعودية للخدمات الأرضية"),
    ("4040","الشركة السعودية للنقل الجماعي"),
    ("4261","شركة ذيب لتأجير السيارات"),("4262","شركة لومي للتأجير"),
    ("4263","شركة سال السعودية للخدمات اللوجستية"),("4264","طيران ناس"),
    ("4265","شركة شري للتجارة"),
    # الأغذية والزراعة
    ("6001","شركة حلواني إخوان"),("6002","شركة هرفي للخدمات الغذائية"),
    ("6010","الشركة الوطنية للتنمية الزراعية"),("6012","شركة ريدان الغذائية"),
    ("6013","شركة الأعمال التطويرية الغذائية"),("6014","شركة الآمار الغذائية"),
    ("6015","أمريكانا للمطاعم العالمية"),("6016","شركة مطاعم بيت الشطيرة"),
    ("6017","شركة جاهز الدولية"),("6018","شركة الأندية للرياضة"),
    ("6019","شركة المسار الشامل للتعليم"),("6020","شركة القصيم القابضة"),
    ("6040","شركة تبوك للتنمية الزراعية"),("6050","الشركة السعودية للأسماك"),
    ("6060","شركة الشرقية للتنمية"),("6070","الجوف"),("6090","جازادكو"),
    # الطاقة
    ("5110","الشركة السعودية للطاقة"),
    # الاتصالات والتقنية
    ("7010","شركة الإتصالات السعودية"),("7020","شركة إتحاد إتصالات"),
    ("7030","شركة الإتصالات المتنقلة السعودية"),("7040","قو للإتصالات"),
    ("7205","شركة دار البلد لحلول الأعمال"),
    # أرامكو
    ("2222","شركة الزيت العربية السعودية"),
]

seen_s = set()
UNIQUE_STOCKS = []
for sym, name in ALL_STOCKS:
    if sym not in seen_s:
        seen_s.add(sym)
        UNIQUE_STOCKS.append((sym, name))

# ============================================================
# 3. الصفحة
# ============================================================

st.set_page_config(
    page_title="داشبورد — test14",
    layout="wide",
    page_icon="📊",
    initial_sidebar_state="collapsed"
)

API_KEY = st.secrets["API_KEY"]

for key, val in {
    "auth": False,
    "daily_pnl": 0.0,
    "signal_log": [],
    "tonight_list": [],
    "intraday_supported": None,
    "all_data": [],
    "last_scan_time": None,
    "scan_count": 0,
}.items():
    if key not in st.session_state:
        st.session_state[key] = val

if not st.session_state.auth:
    st.markdown("<h2 style='text-align:center;margin-top:100px'>📊 داشبورد — test14</h2>", unsafe_allow_html=True)
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
# 4. جلب البيانات
# ============================================================

@st.cache_data(ttl=30)
def get_all_quotes():
    all_syms = list({s for s, _ in UNIQUE_STOCKS})
    quotes_dict, errors = {}, []
    for i in range(0, len(all_syms), 5):
        batch = all_syms[i:i+5]
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

@st.cache_data(ttl=3600)
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

@st.cache_data(ttl=600)
def get_company_info(sym):
    try:
        return client.company(sym)
    except:
        return None

@st.cache_data(ttl=600)
def get_events(sym):
    try:
        ev = client.events(sym)
        if ev and hasattr(ev, "events") and ev.events:
            e = ev.events[0]
            return {
                "type": getattr(e, "event_type", ""),
                "sentiment": getattr(e, "sentiment", "neutral"),
                "importance": getattr(e, "importance", "regular"),
                "desc": getattr(e, "description", ""),
            }
    except:
        pass
    return None

@st.cache_data(ttl=INTRADAY_TTL)
def get_intraday(sym):
    try:
        h = client.intraday(sym, interval="5min")
        closes, highs, lows, volumes, times = [], [], [], [], []
        for item in h.data:
            if item.close and item.close > 0:
                closes.append(float(item.close))
                highs.append(float(item.high or item.close))
                lows.append(float(item.low or item.close))
                volumes.append(float(item.volume or 0))
                times.append(getattr(item, "time", ""))
        return closes, highs, lows, volumes, times, True
    except:
        return [], [], [], [], [], False

@st.cache_data(ttl=60)
def get_historical_60min(sym):
    try:
        h = client.historical(sym, interval="60min")
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

@st.cache_data(ttl=30)
def get_market():
    try:
        return client.market_summary(), None
    except Exception as e:
        return None, str(e)

@st.cache_data(ttl=30)
def get_movers():
    try:
        return client.gainers(), client.losers(), client.volume_leaders(), None
    except Exception as e:
        return None, None, None, str(e)

def get_best_data(sym, quotes_dict):
    i_closes, i_highs, i_lows, i_vols, i_times, supported = get_intraday(sym)
    if supported and len(i_closes) >= INTRADAY_MIN_CANDLES:
        if st.session_state.intraday_supported is None:
            st.session_state.intraday_supported = True
        return i_closes, i_highs, i_lows, i_vols, True, len(i_closes)
    if st.session_state.intraday_supported is None:
        st.session_state.intraday_supported = False
    h_closes, h_highs, h_lows, h_vols = get_historical(sym)
    return h_closes, h_highs, h_lows, h_vols, False, len(h_closes)

# ============================================================
# 5. المؤشرات الفنية
# ============================================================

def calc_ema_series(data, period):
    if len(data) < period: return []
    k = 2.0 / (period + 1)
    ema = [sum(data[:period]) / period]
    for price in data[period:]:
        ema.append(price * k + ema[-1] * (1 - k))
    return ema

def calc_rsi(closes, period=14):
    if len(closes) < period + 1: return 50.0
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
    if len(closes) < period + lookback + 1: return 0.0
    return round(calc_rsi(closes, period) - calc_rsi(closes[:-lookback], period), 1)

def calc_macd(closes):
    if len(closes) < 35: return 0.0, 0.0, 0.0
    e12 = calc_ema_series(closes, 12)
    e26 = calc_ema_series(closes, 26)
    ml  = min(len(e12), len(e26))
    macd_line = [e12[-(ml-i)] - e26[-(ml-i)] for i in range(ml)]
    if len(macd_line) < 9: return 0.0, 0.0, 0.0
    sig = calc_ema_series(macd_line, 9)
    return round(macd_line[-1],3), round(sig[-1],3), round(macd_line[-1]-sig[-1],3)

def calc_macd_direction(closes, lookback=3):
    if len(closes) < 38 + lookback: return 0.0
    _, _, h1 = calc_macd(closes)
    _, _, h2 = calc_macd(closes[:-lookback])
    return round(h1 - h2, 4)

def calc_ma(closes, period):
    if len(closes) < period: return 0.0
    return round(sum(closes[-period:]) / period, 2)

def calc_bollinger(closes, period=20):
    if len(closes) < period: return 0.0, 0.0, 0.0
    r  = closes[-period:]
    ma = sum(r) / period
    std = (sum((x-ma)**2 for x in r)/period)**0.5
    return round(ma+2*std,2), round(ma,2), round(ma-2*std,2)

def calc_atr(highs, lows, closes, period=14):
    if len(closes) < period + 1: return 0.0
    trs = [max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
           for i in range(1, len(closes))]
    if len(trs) < period: return 0.0
    return round(sum(trs[-period:]) / period, 3)

def calc_volume(volumes, period=20):
    if len(volumes) < period: return False, False, 0.0, 0.0
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

def calc_stochastic(h, l, c, k=14):
    if len(c) < k: return 50.0
    lowest  = min(l[-k:])
    highest = max(h[-k:])
    if highest == lowest: return 50.0
    return round(100 * (c[-1] - lowest) / (highest - lowest), 1)

def calc_vwap(h, l, c, v):
    if not c or not v: return 0.0
    typical = [(h[i]+l[i]+c[i])/3 for i in range(len(c))]
    total_pv = sum(typical[i]*v[i] for i in range(len(c)))
    total_v  = sum(v)
    return round(total_pv/total_v, 2) if total_v > 0 else 0.0

def calc_momentum(c, period=10):
    if len(c) < period + 1: return 0.0
    return round(c[-1] - c[-period-1], 4)

def calc_williams_r(h, l, c, period=14):
    if len(c) < period: return -50.0
    highest = max(h[-period:])
    lowest  = min(l[-period:])
    if highest == lowest: return -50.0
    return round(-100 * (highest - c[-1]) / (highest - lowest), 1)

# ============================================================
# 6. نظام النقاط الموسّع — يستخدم كل المميزات المتاحة
# ============================================================

def get_strength_v12(change_pct, rsi, rsi_dir, macd, macd_signal, macd_hist,
                     macd_dir, ma20, ma50, price, vol_high, vol_very,
                     vol_ratio, tasi_change, tasi_up, tasi_down,
                     bb_lower, bb_upper, is_intraday,
                     stoch_k, williams_r, momentum,
                     net_liquidity, analyst_consensus, fair_price,
                     event_sentiment, event_importance,
                     beta=None, liq_score=5):
    score, reasons = 0, []

    # ── RSI ──
    if rsi < 30:
        score += 30; reasons.append(f"RSI تشبع بيع ({rsi}) 🔥")
    elif rsi < 40:
        score += 22; reasons.append(f"RSI منطقة شراء ({rsi})")
    elif 40 <= rsi < 55:
        score += 12; reasons.append(f"RSI متوازن ({rsi})")
    elif rsi >= 70:
        score -= 15; reasons.append(f"⚠️ RSI ذروة ({rsi})")
    if rsi_dir > 10:  score += 8;  reasons.append("RSI زخم قوي")
    elif rsi_dir > 5: score += 4;  reasons.append("RSI صاعد")
    elif rsi_dir < -5: score -= 5; reasons.append("RSI نازل")

    # ── MACD ──
    if macd > 0 and macd_hist > 0 and macd > macd_signal and macd_dir > 0:
        score += 25; reasons.append("MACD إشارة شراء قوية 💪")
    elif macd > macd_signal and macd_hist > 0:
        score += 15; reasons.append("MACD تقاطع صاعد")
    elif macd > 0:
        score += 6
    if macd_dir < 0:
        score -= 8; reasons.append("⚠️ MACD زخم ضعيف")

    # ── المتوسطات ──
    if not is_intraday:
        if ma50 > 0 and price > ma50:
            score += 10; reasons.append("فوق MA50 ✅")
        if ma20 > 0 and price > ma20:
            score += 8;  reasons.append("فوق MA20")
        if ma20 > 0 and ma50 > 0 and ma20 > ma50:
            score += 7;  reasons.append("Golden Cross ⭐")
    else:
        if ma20 > 0 and price > ma20:
            score += 10; reasons.append("فوق EMA9 intraday ✅")

    # ── الحجم ──
    if vol_very:
        score += 20; reasons.append(f"حجم استثنائي ×{vol_ratio} 🚀")
    elif vol_high:
        score += 12; reasons.append(f"حجم مرتفع ×{vol_ratio}")
    elif vol_ratio >= 1.2:
        score += 6;  reasons.append(f"حجم فوق المتوسط ×{vol_ratio}")

    # ── TASI ─ مُحسَّن بنسبة الصاعد/الهابط ──
    tasi_breadth = tasi_up / (tasi_down + 1) if tasi_down > 0 else 1.0
    if tasi_change >= 0.5:
        score += 5;  reasons.append("السوق صاعد 📈")
    elif tasi_change < -2.0:
        score -= 20; reasons.append("🚨 السوق هابط بقوة")
    elif tasi_change < -1.0:
        score -= 10; reasons.append("⚠️ السوق ضعيف")
    elif tasi_change < 0:
        score -= 3
    # مزاج السوق (breadth)
    if tasi_breadth < 0.7:
        score -= 8;  reasons.append("🔴 غالبية الأسهم هابطة")
    elif tasi_breadth > 1.3:
        score += 5;  reasons.append("🟢 غالبية الأسهم صاعدة")

    # ── القوة النسبية vs التاسي (test13 جديد) ──
    rs = change_pct - tasi_change
    if rs > 2.0:
        score += 12; reasons.append(f"قوة نسبية ممتازة +{rs:.1f}% 💪")
    elif rs > 1.0:
        score += 7;  reasons.append(f"قوة نسبية جيدة +{rs:.1f}%")
    elif rs > 0.3:
        score += 3;  reasons.append(f"قوة نسبية إيجابية")
    elif rs < -1.5:
        score -= 8;  reasons.append(f"⚠️ ضعف نسبي {rs:.1f}%")
    elif rs < -0.5:
        score -= 4

    # ── Bollinger ──
    if bb_lower > 0 and price <= bb_lower * 1.01:
        score += 8;  reasons.append("عند الحد الأدنى BB 🎯")
    elif bb_upper > 0 and price >= bb_upper * 0.99:
        score -= 8;  reasons.append("⚠️ عند الحد الأعلى BB")

    # ── Stochastic ──
    if stoch_k < 20:
        score += 8;  reasons.append(f"Stoch ذروة بيع ({stoch_k})")
    elif stoch_k > 80:
        score -= 8;  reasons.append(f"⚠️ Stoch ذروة شراء ({stoch_k})")

    # ── Williams %R ──
    if williams_r < -80:
        score += 5;  reasons.append("Williams ذروة بيع")
    elif williams_r > -20:
        score -= 5;  reasons.append("Williams ذروة شراء")

    # ── Momentum ──
    if momentum > 0:
        score += 4;  reasons.append("Momentum إيجابي")
    elif momentum < 0:
        score -= 3

    # ── صافي السيولة من API ──
    if net_liquidity is not None:
        if net_liquidity > 0:
            score += 8;  reasons.append(f"سيولة صافية شراء ✅")
        elif net_liquidity < -50_000_000:
            score -= 12; reasons.append(f"🔴 ضغط بيع قوي (-{abs(net_liquidity/1e6):.0f}M)")
        elif net_liquidity < 0:
            score -= 5;  reasons.append("سيولة صافية بيع")

    # ── توصية المحللين ──
    if analyst_consensus in ("buy", "strong_buy"):
        score += 10; reasons.append(f"محللون: {analyst_consensus} ✅")
    elif analyst_consensus == "sell":
        score -= 8;  reasons.append("محللون: بيع ⚠️")

    # ── هامش الأمان من السعر العادل ──
    if fair_price and fair_price > 0 and price > 0:
        margin = (fair_price - price) / price * 100
        if margin > 15:
            score += 12; reasons.append(f"سعر عادل أعلى +{margin:.0f}% 🎯")
        elif margin > 5:
            score += 6;  reasons.append(f"سعر عادل أعلى +{margin:.0f}%")
        elif margin < -10:
            score -= 10; reasons.append(f"⚠️ يتداول فوق قيمته {abs(margin):.0f}%")

    # ── الأحداث ──
    if event_sentiment == "positive" and event_importance == "important":
        score += 8;  reasons.append("حدث مهم إيجابي 📰")
    elif event_sentiment == "slightly_positive":
        score += 4
    elif event_sentiment in ("negative", "slightly_negative") and event_importance == "important":
        score -= 8;  reasons.append("حدث مهم سلبي ⚠️")

    # ── تغيير اليوم ──
    if change_pct >= 2.0:
        score += 10; reasons.append(f"زخم قوي +{change_pct}%")
    elif change_pct >= 1.0:
        score += 5;  reasons.append(f"زخم إيجابي +{change_pct}%")
    elif change_pct < -1.5:
        score -= 12; reasons.append(f"⚠️ هابط {change_pct}%")
    elif change_pct < -0.5:
        score -= 5

    if is_intraday:
        reasons.append("📡 بيانات intraday حقيقية")

    return min(max(score, 0), 100), reasons

def calc_confidence_v12(score, rsi_dir, macd_dir, vol_high, vol_very,
                         tasi_change, net_liquidity, analyst_consensus, fair_price, price):
    if score <= 0: return 0
    bonus = 0
    if rsi_dir > 10:       bonus += 12
    elif rsi_dir > 5:      bonus += 6
    if macd_dir > 0:       bonus += 10
    if vol_very:           bonus += 8
    elif vol_high:         bonus += 4
    if tasi_change < -1.0: bonus -= 15
    elif tasi_change < -0.5: bonus -= 8
    # مكافآت إضافية
    if net_liquidity and net_liquidity > 0: bonus += 5
    if analyst_consensus in ("buy", "strong_buy"): bonus += 7
    if fair_price and price and fair_price > price * 1.05: bonus += 5
    return min(max(round((score*0.70)+bonus), 0), 100)

def get_signal_v12(score, rsi, confidence, price, ma50, change_pct,
                   liq_score, vol_ratio, atr, is_intraday, net_liquidity,
                   relative_strength=0.0, h60_confirms=True, fair_price_margin=0.0):
    in_downtrend = (not is_intraday) and ma50 > 0 and price < ma50 * 0.95
    atr_pct      = atr/price if price > 0 else 0
    atr_small    = atr_pct < MIN_ATR_PCT
    low_vol      = vol_ratio < MIN_VOL_RATIO
    low_liq      = liq_score < MIN_LIQ
    falling      = change_pct < MAX_CHANGE_NEG
    heavy_sell_pressure = (net_liquidity is not None and net_liquidity < -100_000_000 and score < 75)

    if any([in_downtrend, atr_small, low_vol, low_liq, falling, heavy_sell_pressure]):
        if score < 35 or rsi > 75:
            return "SELL 🔴", "sell"
        return "WAIT 🟡", "wait"

    # ── الشرط الاستثنائي الإلزامي (test13) ──
    # لا BUY بدون شيء واحد غير طبيعي فعلاً
    exceptional = (
        vol_ratio >= 2.5                                    # حجم استثنائي حقيقي
        or rsi < 35                                         # تشبع بيع واضح
        or relative_strength > 1.5                          # أقوى من السوق بوضوح
        or (net_liquidity is not None and net_liquidity > 50_000_000)  # تدفق شراء قوي
        or (not is_intraday and h60_confirms and vol_ratio >= 1.8)     # 60min يؤكد + حجم
    )

    if score >= MIN_SCORE_STR and rsi < 70 and confidence >= MIN_CONF_STR and exceptional:
        return "BUY 🟢", "strong"
    if score >= MIN_SCORE and rsi < 65 and confidence >= MIN_CONFIDENCE and exceptional:
        return "BUY 🟢", "normal"
    if score >= MIN_SCORE and rsi < 65 and confidence >= MIN_CONFIDENCE and not exceptional:
        return "WAIT 🟡", "wait"   # نقاط كافية لكن لا شيء استثنائي
    if score < 35 or rsi > 75:
        return "SELL 🔴", "sell"
    return "WAIT 🟡", "wait"

def calc_stars(score):
    if score >= 80:   return "⭐⭐⭐⭐⭐"
    elif score >= 65: return "⭐⭐⭐⭐"
    elif score >= 50: return "⭐⭐⭐"
    elif score >= 35: return "⭐⭐"
    else:             return "⭐"

def calc_targets_and_sl(entry, atr, confidence=50, beta=1.0):
    risk_mult = ATR_RISK_MULT * max(0.5, min(beta or 1.0, 2.0))
    risk      = round(atr * risk_mult, 3)
    stop      = round(entry - risk, 2)
    t1        = round(entry + risk * ATR_T1_MULT, 2)
    t2        = round(entry + risk * ATR_T2_MULT, 2)
    t1_pct    = round((t1-entry)/entry*100, 2) if entry > 0 else 0
    t2_pct    = round((t2-entry)/entry*100, 2) if entry > 0 else 0
    if confidence >= 80:   label = "توقع قوي 🔥"
    elif confidence >= 60: label = "توقع متوسط 📊"
    else:                  label = "توقع محافظ 🛡️"
    return t1, t2, stop, t1_pct, t2_pct, label

def calc_position_size(entry, stop):
    risk = entry - stop
    if risk <= 0: return 0, 0
    shares = int(min(CAPITAL_DAILY, MAX_TRADE_DAILY) / entry)
    return shares, round(shares*entry, 2)

def calc_consolidation(closes, period=10):
    """تماسك السهم في نطاق ضيق — مؤشر اختراق وشيك"""
    if len(closes) < period: return 0.0
    recent = closes[-period:]
    low_p  = min(recent)
    if low_p <= 0: return 0.0
    rng = (max(recent) - low_p) / low_p * 100
    if rng < 2.0:  return 1.0
    elif rng < 3.5: return 0.7
    elif rng < 5.0: return 0.4
    return 0.0

def calc_intraday_volume_pattern(volumes, times):
    """
    يقسم الجلسة 3 فترات ويحسب نسبة الحجم في كل فترة.
    الأموال الكبيرة تتراكم في الفترة الأخيرة (13:00-15:00).
    يرجع: (نسبة_حجم_الإغلاق, نسبة_حجم_الافتتاح, تراكم_نعم_لا)
    """
    if not volumes or not times or len(volumes) != len(times):
        return 1.0, 1.0, False
    try:
        open_vol, mid_vol, close_vol = 0.0, 0.0, 0.0
        for v, t in zip(volumes, times):
            hour = int(str(t).split(":")[0]) if ":" in str(t) else 0
            if 10 <= hour < 11:      open_vol  += v
            elif 11 <= hour < 13:    mid_vol   += v
            elif 13 <= hour < 15:    close_vol += v
        total = open_vol + mid_vol + close_vol
        if total <= 0: return 1.0, 1.0, False
        close_ratio = close_vol / (total / 3) if total > 0 else 1.0
        open_ratio  = open_vol  / (total / 3) if total > 0 else 1.0
        # تراكم: حجم الإغلاق أعلى من الافتتاح بـ 30%+
        accumulation = close_ratio > 1.3 and close_vol > open_vol * 1.3
        return round(close_ratio, 2), round(open_ratio, 2), accumulation
    except:
        return 1.0, 1.0, False

def get_60min_trend(sym):
    """
    يحسب اتجاه الـ 60min: صاعد / هابط / محايد
    يرجع: (اتجاه_رقمي, RSI_60min, فوق_MA10_60min)
    +1 = صاعد، -1 = هابط، 0 = محايد
    """
    try:
        c60, h60, l60, v60 = get_historical_60min(sym)
        if len(c60) < 10: return 0, 50.0, False
        rsi60   = calc_rsi(c60)
        ma10_60 = calc_ma(c60, 10)
        macd60, msig60, _ = calc_macd(c60)
        price60 = c60[-1]
        above_ma = price60 > ma10_60 if ma10_60 > 0 else False
        if rsi60 > 55 and above_ma and macd60 > msig60:
            return 1, rsi60, above_ma
        elif rsi60 < 45 or (not above_ma and macd60 < msig60):
            return -1, rsi60, above_ma
        return 0, rsi60, above_ma
    except:
        return 0, 50.0, False
    try:
        change_pct   = float(getattr(q,"change_percent",0) or 0)
        today_volume = float(getattr(q,"volume",0) or 0)
        if len(volumes) < 20: return False, 0.0
        if is_intraday:
            avg_vol     = sum(volumes[:-1]) / max(len(volumes)-1, 1)
            intra_ratio = round(volumes[-1]/avg_vol, 1) if avg_vol > 0 else 0.0
        else:
            avg_vol     = sum(volumes[-20:]) / 20
            time_elapsed = max(now_mins - MARKET_OPEN, 1)
            expected_vol = avg_vol * (time_elapsed / 360)
            intra_ratio  = round(today_volume/expected_vol, 1) if expected_vol > 0 else 0.0
        is_bo = (change_pct >= BREAKOUT_CHANGE
                 and intra_ratio >= BREAKOUT_VOL
                 and float(getattr(q,"price",0) or 0) > (closes[-1]*1.003 if closes else 0))
        return is_bo, intra_ratio
    except:
        return False, 0.0

# ============================================================
# 7. قاعدة البيانات
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
                result_24h TEXT DEFAULT '', result_48h TEXT DEFAULT '',
                result_72h TEXT DEFAULT '', profit_loss TEXT DEFAULT '',
                time_to_target TEXT DEFAULT '',
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
             result_24h,result_48h,result_72h,profit_loss,time_to_target,is_breakout,is_intraday)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'','','','','',?,?)
        """, (now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"),
              sym, name, signal_type, price, entry, t1, t2,
              stop, confidence, rsi, macd, vol, slip, liq,
              is_breakout, is_intraday))
        conn.commit()
    st.session_state.signal_log.append({
        "الوقت": now.strftime("%H:%M"), "الرمز": sym, "الاسم": name,
        "الإشارة": signal_type, "السعر": price,
        "هدف1": t1, "هدف2": t2, "Stop": stop, "الثقة": f"{confidence}%",
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

def eval_signals_continuous(quotes_dict):
    today = now_riyadh().strftime("%Y-%m-%d")
    now_t = now_riyadh().strftime("%H:%M:%S")
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
                t1    = float(row.get("target1",  0) or 0)
                t2    = float(row.get("target2",  0) or 0)
                stop  = float(row.get("stop_loss",0) or 0)
                entry = float(row.get("entry_price",0) or 0)
                sig_time = row.get("time","")
                if hi >= t2:
                    result = "✅ وصل الهدف 2"
                    pl = f"+{round((t2-entry)/entry*100,2)}%"
                    ttt = now_t
                elif hi >= t1:
                    result = "🟡 وصل الهدف 1"
                    pl = f"+{round((t1-entry)/entry*100,2)}%"
                    ttt = now_t
                elif lo <= stop:
                    result = "❌ وصل Stop Loss"
                    pl = f"-{round((entry-stop)/entry*100,2)}%"
                    ttt = now_t
                else:
                    chg = round((cur-entry)/entry*100, 2)
                    result = "⏳ لم يصل بعد"
                    pl = f"{chg:+.2f}%"
                    ttt = ""
                conn.execute(
                    "UPDATE signals SET result_24h=?, profit_loss=?, time_to_target=? WHERE signal_id=?",
                    (result, pl, ttt, row["signal_id"])
                )
            conn.commit()
    except: pass

# ============================================================
# 8. قائمة الغد
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
                intraday_rsi REAL, intraday_candles INTEGER,
                analyst_consensus TEXT, fair_price REAL,
                event_sentiment TEXT
            )
        """)
        # إصلاح: إضافة الأعمدة الجديدة إذا لم تكن موجودة (ترقية الجداول القديمة)
        existing = [row[1] for row in conn.execute("PRAGMA table_info(watchlist)").fetchall()]
        for col, coltype in [
            ("analyst_consensus", "TEXT"),
            ("fair_price", "REAL"),
            ("event_sentiment", "TEXT"),
        ]:
            if col not in existing:
                try:
                    conn.execute(f"ALTER TABLE watchlist ADD COLUMN {col} {coltype}")
                except Exception:
                    pass
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

            i_closes, _, _, _, _, i_supported = get_intraday(sym)
            intraday_rsi     = calc_rsi(i_closes) if len(i_closes) >= 14 else rsi
            intraday_candles = len(i_closes)

            # بيانات إضافية
            comp = get_company_info(sym)
            analyst_c = ""
            fair_p    = 0.0
            if comp:
                try: analyst_c = getattr(comp.analysts, "consensus", "") if hasattr(comp, "analysts") else ""
                except: pass
                try: fair_p   = float(getattr(comp.valuation, "fair_price", 0) or 0) if hasattr(comp, "valuation") else 0.0
                except: pass

            ev = get_events(sym)
            ev_sent = ev.get("sentiment","neutral") if ev else "neutral"

            if (close_str >= TONIGHT_CLOSE and vol_ratio >= TONIGHT_VOL
                    and rsi < TONIGHT_RSI_MAX and macd_dir > 0
                    and ma50 > 0 and price > ma50
                    and atr/price >= MIN_ATR_PCT and intraday_rsi < 70):

                score_t = (
                    close_str * 40 +
                    min(vol_ratio/3, 1) * 30 +
                    (1 - rsi/100) * 20 +
                    (1 if macd_dir > 0 else 0) * 10
                )
                if analyst_c in ("buy","strong_buy"): score_t += 8
                if fair_p > price * 1.05: score_t += 5
                if ev_sent == "positive": score_t += 5

                results.append({
                    "date": today, "symbol": sym, "name": name,
                    "close_price": price, "closing_strength": close_str,
                    "vol_ratio": vol_ratio, "rsi": rsi,
                    "macd_dir": macd_dir, "ma50": ma50, "atr": atr,
                    "score": round(score_t, 1),
                    "intraday_rsi": intraday_rsi, "intraday_candles": intraday_candles,
                    "analyst_consensus": analyst_c, "fair_price": fair_p,
                    "event_sentiment": ev_sent
                })
        except: continue

    if results:
        with get_tonight_db() as conn:
            conn.execute("DELETE FROM watchlist WHERE date=?", (today,))
            for r in results:
                conn.execute("""
                    INSERT INTO watchlist
                    (date,symbol,name,close_price,closing_strength,vol_ratio,rsi,
                     macd_dir,ma50,atr,score,intraday_rsi,intraday_candles,
                     analyst_consensus,fair_price,event_sentiment)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (r["date"],r["symbol"],r["name"],r["close_price"],
                      r["closing_strength"],r["vol_ratio"],r["rsi"],
                      r["macd_dir"],r["ma50"],r["atr"],r["score"],
                      r["intraday_rsi"],r["intraday_candles"],
                      r["analyst_consensus"],r["fair_price"],r["event_sentiment"]))
            conn.commit()
    return sorted(results, key=lambda x: x["score"], reverse=True)

def load_tonight_list():
    today = now_riyadh().strftime("%Y-%m-%d")
    with get_tonight_db() as conn:
        rows = conn.execute(
            "SELECT * FROM watchlist WHERE date=? ORDER BY score DESC", (today,)
        ).fetchall()
    return [dict(r) for r in rows]

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
# 9. التحليل الكامل
# ============================================================

def analyze_stocks(stocks_list, quotes_dict, tasi_change, tasi_up, tasi_down, now_mins, tonight_syms):
    data, failed = [], []
    tonight_set  = {x["symbol"] for x in tonight_syms}

    for sym, name in stocks_list:
        try:
            q = quotes_dict.get(sym)
            if not q or not hasattr(q,"price") or not q.price:
                failed.append(sym); continue

            closes, highs, lows, volumes, is_intraday, n_candles = get_best_data(sym, quotes_dict)
            if len(closes) < (INTRADAY_MIN_CANDLES if is_intraday else 30):
                failed.append(sym); continue

            price      = float(q.price)
            change_pct = float(getattr(q,"change_percent",0) or 0)

            # ── المؤشرات ──
            rsi      = calc_rsi(closes)
            rsi_dir  = calc_rsi_direction(closes)
            macd, macd_sig, macd_hist = calc_macd(closes)
            macd_dir = calc_macd_direction(closes)

            if is_intraday:
                ma20 = calc_ma(closes, 9)
                ma50 = 0.0
            else:
                ma20 = calc_ma(closes, 20)
                ma50 = calc_ma(closes, 50)

            bb_up, _, bb_low  = calc_bollinger(closes)
            atr               = calc_atr(highs, lows, closes)
            stoch_k           = calc_stochastic(highs, lows, closes)
            williams_r        = calc_williams_r(highs, lows, closes)
            momentum          = calc_momentum(closes)
            vwap              = calc_vwap(highs, lows, closes, volumes) if is_intraday else 0.0

            vol_high, vol_very, vol_ratio, avg_vol = calc_volume(volumes)
            if is_intraday:
                today_vol = float(getattr(q,"volume",0) or 0)
                avg_hist  = sum(volumes) / max(len(volumes),1)
                vol_ratio = round(today_vol/avg_hist, 1) if avg_hist > 0 else vol_ratio
                vol_high  = vol_ratio >= 1.5
                vol_very  = vol_ratio >= 2.0

            liq_score = calc_liquidity_score(vol_ratio, avg_vol)
            slip_pct, slip_label = calc_slippage(liq_score)

            # ── القوة النسبية ──
            relative_strength = change_pct - tasi_change

            # ── Bid/Ask Spread (test13) ──
            bid_price = float(getattr(q, "bid", 0) or 0)
            ask_price = float(getattr(q, "ask", 0) or 0)
            if ask_price > 0 and bid_price > 0 and price > 0:
                spread_pct = (ask_price - bid_price) / price
                # سعر الدخول = ask + انزلاق (بدل price + انزلاق)
                entry = round(ask_price * (1 + slip_pct * 0.5), 2)
            else:
                spread_pct = 0.0
                entry = round(price * (1 + slip_pct), 2)

            # ── طبقة الـ 60min (test13) ──
            h60_trend, h60_rsi, h60_above_ma = get_60min_trend(sym)
            h60_confirms = (h60_trend >= 0)  # لا يعارض الاتجاه

            # ── نمط الحجم داخل الجلسة (test13) ──
            i_closes_full, i_highs_full, i_lows_full, i_vols_full, i_times_full, _ = get_intraday(sym)
            close_vol_ratio, open_vol_ratio, accumulation = calc_intraday_volume_pattern(
                i_vols_full, i_times_full
            )

            # ── التماسك (test13) ──
            h_closes_raw, _, _, _ = get_historical(sym)
            consol_score = calc_consolidation(h_closes_raw) if h_closes_raw else 0.0

            # ── بيانات Quote السيولة ──
            liq_inflow  = float(getattr(getattr(q,"liquidity",None),"inflow_value",0) or 0) if hasattr(q,"liquidity") else 0
            liq_outflow = float(getattr(getattr(q,"liquidity",None),"outflow_value",0) or 0) if hasattr(q,"liquidity") else 0
            net_liq     = liq_inflow - liq_outflow if (liq_inflow or liq_outflow) else None

            # ── بيانات الشركة ──
            comp = get_company_info(sym)
            analyst_c  = ""
            fair_p     = 0.0
            pe_ratio   = 0.0
            beta_v     = 1.0
            target_p   = 0.0
            if comp:
                try:
                    if hasattr(comp, "analysts"):
                        analyst_c = getattr(comp.analysts, "consensus", "") or ""
                        target_p  = float(getattr(comp.analysts, "target_mean", 0) or 0)
                    if hasattr(comp, "valuation"):
                        fair_p = float(getattr(comp.valuation, "fair_price", 0) or 0)
                    if hasattr(comp, "fundamentals"):
                        pe_ratio = float(getattr(comp.fundamentals, "pe_ratio", 0) or 0)
                        beta_v   = float(getattr(comp.fundamentals, "beta", 1.0) or 1.0)
                except: pass

            # ── الأحداث ──
            ev = get_events(sym)
            ev_sent    = ev.get("sentiment","neutral") if ev else "neutral"
            ev_imp     = ev.get("importance","regular") if ev else "regular"
            ev_type    = ev.get("type","") if ev else ""

            # ── النقاط ──
            score, reasons = get_strength_v12(
                change_pct, rsi, rsi_dir, macd, macd_sig, macd_hist, macd_dir,
                ma20, ma50, price, vol_high, vol_very, vol_ratio,
                tasi_change, tasi_up, tasi_down, bb_low, bb_up, is_intraday,
                stoch_k, williams_r, momentum,
                net_liq, analyst_c, fair_p, ev_sent, ev_imp, beta_v, liq_score
            )
            confidence = calc_confidence_v12(score, rsi_dir, macd_dir, vol_high, vol_very,
                                              tasi_change, net_liq, analyst_c, fair_p, price)
            # test14: نمرر fair_price_margin للشرط الاستثنائي
            _fpm = round((fair_p - price)/price*100, 1) if fair_p > 0 and price > 0 else 0.0
            signal, sig_type = get_signal_v12(
                score, rsi, confidence, price, ma50, change_pct,
                liq_score, vol_ratio, atr, is_intraday, net_liq,
                relative_strength, h60_confirms, _fpm
            )
            stars = calc_stars(score)
            t1, t2, stop, t1_pct, t2_pct, model_label = calc_targets_and_sl(entry, atr, confidence, beta_v)
            shares, amount = calc_position_size(entry, stop)
            is_bo, intra_ratio = check_breakout(sym, q, closes, volumes, now_mins, is_intraday)
            in_tonight = sym in tonight_set

            # هامش الأمان
            safety_margin = round((fair_p - price)/price*100, 1) if fair_p > 0 and price > 0 else None

            # تسجيل تلقائي
            signals_active_now = now_mins >= MARKET_SIGNALS and now_mins < MARKET_CLOSE
            is_workday = now_riyadh().weekday() in [6,0,1,2,3]
            if signals_active_now and is_workday:
                if sig_type in ["strong","normal"] and not signal_already_saved_today(sym):
                    save_signal(sym, name, signal, price, entry, t1, t2, stop,
                                confidence, rsi, macd, vol_ratio, slip_pct, liq_score,
                                0, int(is_intraday))
                elif is_bo and not signal_already_saved_today(sym):
                    save_signal(sym, name, "BREAKOUT 🚨", price, entry, t1, t2, stop,
                                confidence, rsi, macd, vol_ratio, slip_pct, liq_score,
                                1, int(is_intraday))

            data_layer = "📡 Intraday" if is_intraday else "📅 يومي"
            # test14: جودة الوقت داخل الجلسة
            if is_intraday:
                if 615 <= now_mins <= 720:   session_q = "🟢 أفضل وقت (10:15-12:00)"
                elif 780 <= now_mins <= 870: session_q = "🟢 جيد (13:00-14:30)"
                elif 600 <= now_mins <= 615: session_q = "🟡 افتتاح — تحفظ"
                elif 870 <= now_mins <= 900: session_q = "🔴 إغلاق — لا تدخل"
                else:                        session_q = "🟡 متوسط"
            else:
                session_q = "📅 بعد إغلاق"
            rsi_warn   = "🔴 احذر!" if rsi > 70 else ("🟡 قريب" if rsi > 65 else "✅")

            data.append({
                "الرمز": sym, "الاسم": name,
                "السعر": price, "التغيير%": round(change_pct,2),
                "النجوم": stars, "الإشارة": signal,
                "هدف1": t1, "هدف%1": f"+{t1_pct}%",
                "هدف2": t2, "هدف%2": f"+{t2_pct}%",
                "توقع النموذج": model_label,
                "Stop Loss": stop, "سعر الدخول": entry,
                "الثقة%": confidence, "RSI": rsi, "تحذير RSI": rsi_warn,
                "MACD": macd, "MACD زخم": "صاعد ✅" if macd_dir > 0 else "نازل ⚠️",
                "MA50": ma50, "ATR": atr, "Stoch%K": stoch_k,
                "Williams%R": williams_r, "VWAP": vwap if is_intraday else "",
                "حجم×": vol_ratio, "حجم لحظي×": intra_ratio,
                "السيولة": f"{liq_score}/10", "انزلاق": slip_label,
                "صافي السيولة (M)": round(net_liq/1e6,1) if net_liq else "",
                "السعر العادل": fair_p if fair_p > 0 else "",
                "هامش الأمان%": f"+{safety_margin}%" if safety_margin and safety_margin > 0 else (f"{safety_margin}%" if safety_margin else ""),
                "توصية المحللين": analyst_c, "السعر المستهدف": target_p if target_p > 0 else "",
                "P/E": pe_ratio if pe_ratio > 0 else "", "Beta": beta_v,
                "حدث": ev_type, "مشاعر الحدث": ev_sent,
                "الأسهم": shares, "المبلغ": amount,
                "القوة%": score, "طبقة البيانات": data_layer, "عدد الشمعات": n_candles,
                "Breakout": "🚨 نعم" if is_bo else "",
                "في قائمة الغد": "🌙 نعم" if in_tonight else "",
                "قوة نسبية": round(relative_strength, 2),
                "جودة الوقت": session_q,
                "60min": "صاعد ✅" if h60_trend > 0 else ("هابط ⚠️" if h60_trend < 0 else "محايد"),
                "حجم إغلاق×": close_vol_ratio,
                "تراكم": "✅" if accumulation else "",
                "تماسك": "🎯" if consol_score >= 0.7 else "",
                # حقول داخلية
                "_signal_type": sig_type, "_confidence": confidence,
                "_liq_score": liq_score, "_entry": entry,
                "_t1": t1, "_t2": t2, "_stop": stop,
                "_rsi": rsi, "_macd": macd, "_vol": vol_ratio,
                "_sym": sym, "_name": name, "_slip": slip_pct,
                "_is_bo": is_bo, "_is_intraday": is_intraday,
                "_reasons": " | ".join(reasons),
                "_rs": relative_strength, "_h60": h60_trend,
                "_accumulation": accumulation,
            })
        except Exception as e:
            failed.append(f"{sym}({str(e)[:25]})")

    return data, failed

# ============================================================
# 10. CSS
# ============================================================

st.markdown("""
<style>
/* ── الخلفية العامة ── */
.stApp { background:#f0f2f6; }
[data-testid="stAppViewContainer"] { background:#f0f2f6; }

/* ── بطاقة الإشارة ── */
.sc {
    border-radius:16px; padding:0;
    margin-bottom:14px; overflow:hidden;
    border:none; box-shadow:0 1px 4px rgba(0,0,0,0.10);
    background:#fff; font-family:inherit;
}
.sc-header {
    padding:12px 16px 10px;
    display:flex; justify-content:space-between; align-items:center;
    border-bottom:1px solid rgba(0,0,0,0.06);
}
.sc-sym { font-size:15px; font-weight:700; color:#111; }
.sc-name { font-size:12px; color:#666; margin-top:2px; }
.sc-stars { font-size:13px; letter-spacing:1px; }
.sc-badges { padding:8px 16px; display:flex; gap:5px; flex-wrap:wrap; }
.sc-body { padding:0 16px 4px; }
.sc-row {
    display:grid; grid-template-columns:1fr 1fr;
    gap:0; border-bottom:1px solid #f3f4f6;
    padding:7px 0;
}
.sc-row:last-child { border-bottom:none; }
.sc-cell { font-size:12px; color:#444; }
.sc-label { font-size:11px; color:#999; margin-bottom:2px; }
.sc-val { font-size:13px; font-weight:600; color:#111; }
.sc-val-g { color:#1b7a3e; }
.sc-val-r { color:#c0392b; }
.sc-val-b { color:#1565c0; }
.sc-reasons {
    margin:0 16px 12px; padding:8px 12px;
    background:#f8f9fb; border-radius:8px;
    font-size:11px; color:#555; line-height:1.7;
}

/* أنواع البطاقات — شريط لوني في الأعلى */
.sc-strong  .sc-header { border-top:4px solid #1b7a3e; background:#f0faf3; }
.sc-buy     .sc-header { border-top:4px solid #4caf50; background:#f6fdf7; }
.sc-intraday .sc-header { border-top:4px solid #1565c0; background:#f0f6ff; }
.sc-breakout .sc-header { border-top:4px solid #f59e0b; background:#fffbf0; }
.sc-wait    .sc-header { border-top:4px solid #d1d5db; background:#fafafa; }
.sc-sell    .sc-header { border-top:4px solid #e53935; background:#fff8f8; }

/* ── شارات ── */
.badge {
    display:inline-flex; align-items:center; gap:3px;
    padding:3px 9px; border-radius:99px;
    font-size:11px; font-weight:600; white-space:nowrap;
}
.b-green  { background:#e6f4ea; color:#1b7a3e; }
.b-blue   { background:#e3f0fd; color:#1565c0; }
.b-amber  { background:#fff8e1; color:#b45309; }
.b-red    { background:#ffebee; color:#c0392b; }
.b-purple { background:#f0ebff; color:#5b21b6; }
.b-gray   { background:#f3f4f6; color:#555; }

/* ── هيدر الداشبورد ── */
.dash-header {
    background:#fff; border-radius:16px;
    padding:16px 20px; margin-bottom:16px;
    box-shadow:0 1px 4px rgba(0,0,0,0.08);
    display:flex; justify-content:space-between; align-items:center;
    flex-wrap:wrap; gap:10px;
}
.dash-title { font-size:20px; font-weight:700; color:#111; margin:0; }
.dash-sub { font-size:12px; color:#888; margin-top:3px; }
.dash-status {
    display:flex; align-items:center; gap:8px;
    font-size:13px; font-weight:600;
}
.status-dot {
    width:9px; height:9px; border-radius:50%; display:inline-block;
}
.dot-green { background:#22c55e; }
.dot-red   { background:#ef4444; }
.dot-amber { background:#f59e0b; }

/* ── شريط TASI ── */
.tasi-bar {
    background:#fff; border-radius:14px;
    padding:16px 24px; margin-bottom:16px;
    box-shadow:0 1px 4px rgba(0,0,0,0.06);
    display:flex; gap:28px; flex-wrap:wrap; align-items:center;
}
.tasi-item { text-align:center; }
.tasi-label { font-size:12px; color:#888; margin-bottom:4px; font-weight:500; }
.tasi-val { font-size:22px; font-weight:800; color:#111; }
.tasi-sub { font-size:11px; color:#666; }

/* ── شريط التحديث ── */
.upd-bar {
    background:#1e3a5f; color:#e8f0fb;
    border-radius:12px; padding:10px 20px;
    font-size:13px; display:flex;
    align-items:center; gap:10px; flex-wrap:wrap;
    margin-bottom:14px;
}
.upd-dot { width:7px; height:7px; border-radius:50%; background:#22c55e; display:inline-block; }

/* ── تحسينات عامة ── */
.stTabs [data-baseweb="tab"] { font-size:13px; font-weight:600; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 11. الحالة الزمنية والبيانات
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
circuit_break  = False

market, _ = get_market()
tasi_change  = float(getattr(market,"index_change_percent",0) or 0) if market else 0.0
tasi_value   = float(getattr(market,"index_value",0) or 0) if market else 0.0
tasi_up      = int(getattr(market,"advancing",0) or 0) if market else 0
tasi_down    = int(getattr(market,"declining",0) or 0) if market else 0
tasi_mood    = getattr(market,"market_mood","") if market else ""
circuit_break = tasi_change < -3.0

quotes_dict, q_errors = get_all_quotes()

tonight_syms = load_tonight_list()
premarket_list = scan_premarket(tonight_syms, quotes_dict) if pre_open else []

all_data, failed_syms = analyze_stocks(
    UNIQUE_STOCKS, quotes_dict, tasi_change, tasi_up, tasi_down, now_mins, tonight_syms
)

if all_data:
    st.session_state.all_data = all_data
    st.session_state.last_scan_time = now.strftime("%H:%M:%S")
    st.session_state.scan_count += 1

if signals_active or after_close:
    eval_signals_continuous(quotes_dict)
if after_close and all_data:
    scan_tonight(UNIQUE_STOCKS, quotes_dict)

# ============================================================
# 12. الهيدر الرئيسي
# ============================================================


# ── عنوان الداشبورد ──
st.markdown(f"""
<div style='padding:20px 0 8px'>
  <h1 style='margin:0;font-size:28px;font-weight:800;color:#111;line-height:1.2'>
    📊 داشبورد — {GROUP_TITLE}
  </h1>
  <p style='margin:4px 0 0;font-size:13px;color:#888'>
    السوق السعودي — تاسي &nbsp;|&nbsp; {now.strftime("%A %d %B %Y")}
  </p>
</div>
""", unsafe_allow_html=True)

# ── شريط التحديث ──
last_upd  = st.session_state.last_scan_time or "لم يبدأ بعد"
ind_count = sum(1 for d in all_data if d.get("_is_intraday")) if all_data else 0
buy_count = sum(1 for d in all_data if d.get("_signal_type") in ("strong","normal")) if all_data else 0
dot_color = "#22c55e" if market_open else "#ef4444"
st.markdown(f"""
<div class='upd-bar'>
    <span class='upd-dot' style='background:{dot_color}'></span>
    <span><b>آخر تحديث:</b> {now.strftime("%H:%M:%S")}</span>
    <span style='color:#aac'>|</span>
    <span>مسح المؤشرات: {last_upd}</span>
    <span style='color:#aac'>|</span>
    <span>أسهم: <b>{len(all_data)}</b></span>
    <span style='color:#aac'>|</span>
    <span>BUY: <b style='color:#7ee8a2'>{buy_count}</b></span>
    {"<span style='color:#aac'>|</span><span>Intraday: <b style='color:#90c9ff'>" + str(ind_count) + "</b></span>" if ind_count else ""}
</div>
""", unsafe_allow_html=True)

# ── شريط TASI ──
tasi_chg_color = "#22c55e" if tasi_change >= 0 else "#ef4444"
breadth_pct = round(tasi_up/(tasi_up+tasi_down)*100) if (tasi_up+tasi_down)>0 else 50
mood_badge = {"Bullish":"🟢 صاعد","Bearish":"🔴 هابط","Neutral":"🟡 محايد"}.get(tasi_mood, tasi_mood or "—")
st.markdown(f"""
<div class='tasi-bar'>
    <div class='tasi-item'>
        <div class='tasi-label'>مؤشر تاسي</div>
        <div class='tasi-val'>{tasi_value:,.0f}</div>
        <div class='tasi-sub' style='color:{tasi_chg_color};font-weight:600'>{tasi_change:+.2f}%</div>
    </div>
    <div class='tasi-item'>
        <div class='tasi-label'>صاعد</div>
        <div class='tasi-val' style='color:#22c55e'>{tasi_up}</div>
    </div>
    <div class='tasi-item'>
        <div class='tasi-label'>هابط</div>
        <div class='tasi-val' style='color:#ef4444'>{tasi_down}</div>
    </div>
    <div class='tasi-item'>
        <div class='tasi-label'>نبض السوق</div>
        <div class='tasi-val' style='font-size:14px'>{mood_badge}</div>
        <div class='tasi-sub'>{breadth_pct}% صاعد</div>
    </div>
    <div class='tasi-item'>
        <div class='tasi-label'>البيانات</div>
        <div class='tasi-val' style='font-size:14px'>{"📡 Intraday" if st.session_state.intraday_supported else "📅 يومي"}</div>
    </div>
    <div class='tasi-item'>
        <div class='tasi-label'>وقت السوق</div>
        <div class='tasi-val' style='font-size:14px'>{"🟢 مفتوح" if market_open else "🌅 قريب" if pre_open else "🔴 مغلق"}</div>
        <div class='tasi-sub'>{now.strftime("%H:%M")}</div>
    </div>
</div>
""", unsafe_allow_html=True)

if circuit_break:
    st.error("🚨 تنبيه Circuit Breaker — السوق في هبوط حاد. لا تتداول.")





def render_top_card(r):
    sig_type = r.get("_signal_type","wait")
    is_bo    = r.get("_is_bo", False)
    is_intra = r.get("_is_intraday", False)
    sc_type  = ("sc-strong" if sig_type=="strong" else
                "sc-intraday" if is_intra else
                "sc-breakout" if is_bo else
                "sc-buy" if sig_type=="normal" else "sc-wait")
    liq_s = r.get("_liq_score",0)
    liq_b = "b-green" if liq_s>=7 else "b-amber" if liq_s>=4 else "b-red"

    chg = r.get("التغيير%",0)
    chg_col = "sc-val-g" if chg>=0 else "sc-val-r"

    analyst = str(r.get("توصية المحللين",""))
    margin  = str(r.get("هامش الأمان%",""))
    analyst_ok = analyst and analyst not in ("","0","nan","None")
    margin_ok  = margin  and margin  not in ("","0","nan","None")

    reasons = r.get("_reasons","").replace("|","•")

    html = f"""
<div class='sc {sc_type}'>
  <div class='sc-header'>
    <div>
      <div class='sc-sym'>{r['الرمز']} &nbsp;<span style='font-weight:400;font-size:13px;color:#444'>{r['الاسم']}</span></div>
    </div>
    <div class='sc-stars'>{r.get('النجوم','')}</div>
  </div>
  <div class='sc-badges'>
    <span class='badge b-green'>{r['الإشارة']}</span>
    <span class='badge b-blue'>ثقة {r['الثقة%']}%</span>
    <span class='badge {liq_b}'>سيولة {r['السيولة']}</span>
    {"<span class='badge b-purple'>Intraday</span>" if is_intra else "<span class='badge b-gray'>يومي</span>"}
    {"<span class='badge b-amber'>Breakout</span>" if is_bo else ""}
    {("<span class='badge b-blue'>" + analyst + "</span>") if analyst_ok else ""}
    {("<span class='badge b-green'>هامش " + margin + "</span>") if margin_ok else ""}
  </div>
  <div class='sc-body'>
    <div class='sc-row'>
      <div class='sc-cell'><div class='sc-label'>السعر الحالي</div><div class='sc-val'>{r['السعر']}</div></div>
      <div class='sc-cell'><div class='sc-label'>سعر الدخول</div><div class='sc-val sc-val-b'>{r['سعر الدخول']}</div></div>
    </div>
    <div class='sc-row'>
      <div class='sc-cell'><div class='sc-label'>هدف 1</div><div class='sc-val sc-val-g'>{r['هدف1']} &nbsp;<small>{r['هدف%1']}</small></div></div>
      <div class='sc-cell'><div class='sc-label'>هدف 2</div><div class='sc-val sc-val-g'>{r['هدف2']} &nbsp;<small>{r['هدف%2']}</small></div></div>
    </div>
    <div class='sc-row'>
      <div class='sc-cell'><div class='sc-label'>وقف الخسارة</div><div class='sc-val sc-val-r'>{r['Stop Loss']}</div></div>
      <div class='sc-cell'><div class='sc-label'>التغيير اليوم</div><div class='sc-val {chg_col}'>{chg:+.2f}%</div></div>
    </div>
    <div class='sc-row'>
      <div class='sc-cell'><div class='sc-label'>RSI</div><div class='sc-val'>{r['RSI']} {r.get('تحذير RSI','')}</div></div>
      <div class='sc-cell'><div class='sc-label'>قوة الإشارة</div><div class='sc-val'>{r['القوة%']}%</div></div>
    </div>
  </div>
  <div class='sc-reasons'>{reasons}</div>
</div>"""
    st.markdown(html, unsafe_allow_html=True)


# ────────────────────────────────────────────────────────────
# أفضل الفرص — دائمًا في الأعلى
# ────────────────────────────────────────────────────────────
if all_data:
    df_all_top = pd.DataFrame(all_data)
    df_buy_top = df_all_top[df_all_top["الإشارة"]=="BUY 🟢"].sort_values("الثقة%", ascending=False)
    if not df_buy_top.empty:
        st.divider()
        buy_time = st.session_state.last_scan_time or "—"
        st.markdown(f"### ⚡ أفضل الفرص — BUY &nbsp;&nbsp; <small style='font-size:13px;color:#555;font-weight:normal'>الإشارات: {buy_time}</small>", unsafe_allow_html=True)
        top3 = df_buy_top.head(3)
        cols = st.columns(min(3, len(top3)))
        for i, (_, row) in enumerate(top3.iterrows()):
            with cols[i]:
                render_top_card(row.to_dict())
        st.divider()

# ============================================================
# 13. التابات
# ============================================================

tab_buy, tab_bo, tab_tomorrow, tab_log, tab_reports, tab_backtest = st.tabs([
    "⚡ كل إشارات BUY",
    "🚨 Breakout",
    "🌙 قائمة الغد",
    "📋 سجل اليوم",
    "📊 التقارير",
    "🧪 اختبار الاستراتيجية",
])

# ─── كل إشارات BUY ───
with tab_buy:
    st.subheader("⚡ كل إشارات BUY — المسح الشامل")
    if not signals_active:
        st.info("⏳ الإشارات تبدأ الساعة 10:15 — تعرض الآن أفضل الفرص من آخر مسح")
    if all_data:
        df_b = pd.DataFrame(all_data)
        df_buy = df_b[df_b["الإشارة"]=="BUY 🟢"].sort_values("الثقة%", ascending=False)
        st.caption(f"إجمالي الأسهم الممسوحة: {len(df_b)} | BUY: {len(df_buy)} | فشل: {len(failed_syms)}")

        show_c = ["الرمز","الاسم","السعر","التغيير%","النجوم","الإشارة",
                  "هدف1","هدف2","Stop Loss","الثقة%","RSI","تحذير RSI",
                  "MACD زخم","Stoch%K","حجم×","صافي السيولة (M)",
                  "توصية المحللين","هامش الأمان%","السعر العادل",
                  "مشاعر الحدث","القوة%","طبقة البيانات","Breakout","في قائمة الغد"]
        show_c = [c for c in show_c if c in df_buy.columns]

        f1,f2,f3,f4 = st.columns(4)
        with f1: only_strong = st.checkbox("⭐ Strong فقط")
        with f2: only_intra  = st.checkbox("📡 Intraday فقط")
        with f3: hide_overbought = st.checkbox("إخفاء ذروة RSI")
        with f4: sort_by = st.selectbox("ترتيب:", ["الثقة%","القوة%","RSI","حجم×"])

        df_show = df_buy.copy()
        if only_strong:  df_show = df_show[df_show["_signal_type"]=="strong"]
        if only_intra:   df_show = df_show[df_show["طبقة البيانات"]=="📡 Intraday"]
        if hide_overbought and "تحذير RSI" in df_show.columns:
            df_show = df_show[~df_show["تحذير RSI"].str.contains("🔴",na=False)]
        df_show = df_show.sort_values(sort_by, ascending=(sort_by=="RSI"))

        st.dataframe(df_show[show_c], use_container_width=True, height=500,
            column_config={
                "القوة%": st.column_config.ProgressColumn("القوة%", min_value=0, max_value=100),
                "الثقة%": st.column_config.ProgressColumn("الثقة%", min_value=0, max_value=100),
            })
        csv_b = df_show[show_c].to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("⬇️ تحميل إشارات BUY", csv_b, f"buy_{now.strftime('%Y_%m_%d')}.csv", "text/csv")
    else:
        st.warning("لا توجد بيانات — جاري المسح...")

# ─── Breakout ───
with tab_bo:
    st.subheader("🚨 Breakout اللحظي")
    if first_15: st.warning("⏰ أول 15 دقيقة — الوقت الأفضل للـ Breakout")
    if all_data:
        df_bo = pd.DataFrame(all_data)
        df_bo = df_bo[df_bo["Breakout"]=="🚨 نعم"].sort_values("حجم لحظي×", ascending=False)
        if not df_bo.empty:
            st.success(f"🚨 {len(df_bo)} إشارة Breakout الآن")
            show_bo = ["الرمز","الاسم","السعر","التغيير%","الإشارة","الثقة%",
                       "RSI","حجم×","حجم لحظي×","هدف1","هدف2","Stop Loss","القوة%"]
            show_bo = [c for c in show_bo if c in df_bo.columns]
            st.dataframe(df_bo[show_bo], use_container_width=True)
        else:
            st.info("لا توجد Breakout الآن — ستظهر فور اكتشافها")

# ─── قائمة الغد ───
with tab_tomorrow:
    st.subheader("🌙 مرشحو الغد")
    if pre_open and premarket_list:
        st.success(f"🌅 Pre-market — {len(premarket_list)} سهم Gap Up")
        st.dataframe(pd.DataFrame(premarket_list)[["symbol","name","close_price","gap_up","vol_ratio","rsi"]],
                     use_container_width=True)
        st.divider()
    tonight_data = load_tonight_list()
    if tonight_data:
        df_tn = pd.DataFrame(tonight_data)
        st.success(f"📋 {len(tonight_data)} سهم في قائمة الغد")
        show_tn = ["symbol","name","close_price","closing_strength","vol_ratio","rsi",
                   "intraday_rsi","score","analyst_consensus","fair_price","event_sentiment"]
        show_tn = [c for c in show_tn if c in df_tn.columns]
        st.dataframe(df_tn[show_tn], use_container_width=True,
            column_config={"score": st.column_config.ProgressColumn("score", min_value=0, max_value=100)})
        csv_tn = df_tn[show_tn].to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("⬇️ قائمة الغد", csv_tn, f"tomorrow_{now.strftime('%Y_%m_%d')}.csv","text/csv")
    else:
        msg = "القائمة تُبنى بعد 15:15" if not after_close else "⏳ جاري البناء..."
        st.info(msg)

# ─── سجل اليوم ───
with tab_log:
    st.subheader("📋 سجل اليوم")
    today_sigs = load_today_signals()
    if today_sigs:
        df_log = pd.DataFrame(today_sigs)
        total  = len(today_sigs)
        buy_n  = len([s for s in today_sigs if "BUY" in str(s.get("signal_type",""))])
        bo_n   = len([s for s in today_sigs if s.get("is_breakout",0)==1])
        won    = len([s for s in today_sigs if str(s.get("result_24h","")).startswith("✅")])
        c1,c2,c3,c4 = st.columns(4)
        c1.metric("إجمالي الإشارات", total)
        c2.metric("BUY", buy_n)
        c3.metric("Breakout", bo_n)
        c4.metric("✅ وصل هدف", won)

        show_log = ["date","time","symbol","name","signal_type","price","entry_price",
                    "target1","target2","stop_loss","confidence","rsi","result_24h",
                    "profit_loss","time_to_target","is_breakout","is_intraday"]
        show_log = [c for c in show_log if c in df_log.columns]
        st.dataframe(df_log[show_log], use_container_width=True)
        csv_log = df_log.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("⬇️ تحميل", csv_log, f"signals_{now.strftime('%Y_%m_%d')}.csv","text/csv")
    else:
        st.info("لا توجد سجلات اليوم")

# ─── التقارير ───
with tab_reports:
    st.subheader("📊 التقارير")

    def build_excel_report(df_signals, report_type="daily"):
        """يبني تقرير Excel شامل"""
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            # ورقة الملخص
            completed = df_signals[df_signals["result_24h"] != ""] if "result_24h" in df_signals.columns else pd.DataFrame()
            won_s  = len(completed[completed["result_24h"].str.startswith("✅",na=False)]) if not completed.empty else 0
            t1_s   = len(completed[completed["result_24h"].str.contains("هدف 1",na=False)]) if not completed.empty else 0
            t2_s   = len(completed[completed["result_24h"].str.contains("هدف 2",na=False)]) if not completed.empty else 0
            stop_s = len(completed[completed["result_24h"].str.startswith("❌",na=False)]) if not completed.empty else 0
            pend_s = len(completed[completed["result_24h"].str.startswith("⏳",na=False)]) if not completed.empty else 0
            total_s = len(df_signals)
            rate_s  = round(won_s/len(completed)*100,1) if len(completed) > 0 else 0

            summary_data = {
                "المقياس": ["إجمالي الإشارات","مكتملة","✅ ناجحة","هدف 2","هدف 1","❌ Stop","⏳ لم يصل","نسبة النجاح%"],
                "القيمة":  [total_s, len(completed), won_s, t2_s, t1_s, stop_s, pend_s, f"{rate_s}%"]
            }
            pd.DataFrame(summary_data).to_excel(writer, sheet_name="الملخص", index=False)

            # ورقة كل الإشارات
            df_signals.to_excel(writer, sheet_name="الإشارات الكاملة", index=False)

            # ورقة الناجحة
            if not completed.empty:
                won_df = completed[completed["result_24h"].str.startswith("✅",na=False)]
                if not won_df.empty:
                    won_df.to_excel(writer, sheet_name="الناجحة", index=False)

            # ورقة الخاسرة
            if not completed.empty:
                lost_df = completed[completed["result_24h"].str.startswith("❌",na=False)]
                if not lost_df.empty:
                    lost_df.to_excel(writer, sheet_name="الخاسرة", index=False)

            # ورقة أداء كل سهم
            if "symbol" in df_signals.columns and "result_24h" in df_signals.columns:
                def is_win(r): return str(r).startswith("✅") or "هدف" in str(r)
                df_signals["ناجحة"] = df_signals["result_24h"].apply(is_win).astype(int)
                perf = df_signals.groupby(["symbol","name"]).agg(
                    إشارات=("result_24h","count"),
                    ناجحة=("ناجحة","sum")
                ).reset_index()
                perf["نسبة%"] = (perf["ناجحة"]/perf["إشارات"]*100).round(1)
                perf.sort_values("نسبة%", ascending=False).to_excel(writer, sheet_name="أداء الأسهم", index=False)

        output.seek(0)
        return output.getvalue()

    r1, r2, r3 = st.tabs(["📅 يومي","📆 أسبوعي","📈 الأداء الكلي"])

    with r1:
        today_str = now.strftime("%Y-%m-%d")
        with get_db_conn() as conn:
            df_today = pd.read_sql_query(f"SELECT * FROM signals WHERE date='{today_str}'", conn)
        if not df_today.empty:
            won_t  = len(df_today[df_today["result_24h"].str.startswith("✅",na=False)])
            stop_t = len(df_today[df_today["result_24h"].str.startswith("❌",na=False)])
            pend_t = len(df_today[df_today["result_24h"].str.startswith("⏳",na=False)])
            comp_t = won_t + stop_t
            rate_t = round(won_t/comp_t*100,1) if comp_t > 0 else 0

            c1,c2,c3,c4,c5 = st.columns(5)
            c1.metric("إجمالي", len(df_today))
            c2.metric("✅ ناجحة", won_t)
            c3.metric("❌ Stop", stop_t)
            c4.metric("⏳ جارٍ", pend_t)
            c5.metric("نسبة النجاح", f"{rate_t}%")

            if rate_t >= 65: st.success(f"🎯 النموذج ممتاز اليوم — {rate_t}%")
            elif rate_t >= 55: st.warning(f"📊 النموذج جيد — {rate_t}%")
            elif comp_t > 0: st.error(f"⚠️ {rate_t}% — راجع الفلاتر")

            st.dataframe(df_today, use_container_width=True)

            # تصدير Excel يومي
            excel_daily = build_excel_report(df_today, "daily")
            st.download_button(
                "⬇️ تحميل تقرير Excel اليومي",
                excel_daily,
                f"تقرير_يومي_{today_str}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("لا توجد إشارات اليوم")

    with r2:
        week_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
        with get_db_conn() as conn:
            df_week = pd.read_sql_query(
                f"SELECT * FROM signals WHERE date >= '{week_start}' ORDER BY date, signal_id", conn
            )
        if not df_week.empty:
            won_w  = len(df_week[df_week["result_24h"].str.startswith("✅",na=False)])
            stop_w = len(df_week[df_week["result_24h"].str.startswith("❌",na=False)])
            pend_w = len(df_week[df_week["result_24h"].str.startswith("⏳",na=False)])
            comp_w = won_w + stop_w
            rate_w = round(won_w/comp_w*100,1) if comp_w > 0 else 0

            c1,c2,c3,c4,c5 = st.columns(5)
            c1.metric("إجمالي الأسبوع", len(df_week))
            c2.metric("✅ ناجحة", won_w)
            c3.metric("❌ Stop", stop_w)
            c4.metric("⏳ جارٍ", pend_w)
            c5.metric("نسبة الأسبوع", f"{rate_w}%")

            # أداء يومي
            if "date" in df_week.columns:
                def daily_rate(grp):
                    c = grp[grp["result_24h"].str.startswith("✅",na=False)]
                    tot = len(grp[grp["result_24h"].isin(grp["result_24h"].unique()) & grp["result_24h"].str.len()>0])
                    return round(len(c)/tot*100,1) if tot > 0 else 0
                daily_perf = df_week.groupby("date").apply(lambda g: pd.Series({
                    "إشارات": len(g),
                    "ناجحة": len(g[g["result_24h"].str.startswith("✅",na=False)]),
                    "Stop": len(g[g["result_24h"].str.startswith("❌",na=False)])
                })).reset_index()
                st.dataframe(daily_perf, use_container_width=True)

            # تصدير Excel أسبوعي
            excel_week = build_excel_report(df_week, "weekly")
            st.download_button(
                "⬇️ تحميل تقرير Excel الأسبوعي",
                excel_week,
                f"تقرير_أسبوعي_{week_start}.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.info("لا توجد إشارات هذا الأسبوع")

    with r3:
        try:
            with get_db_conn() as conn:
                df_all_s = pd.read_sql_query("SELECT * FROM signals ORDER BY signal_id DESC", conn)
            if not df_all_s.empty:
                total_all = len(df_all_s)
                completed_all = df_all_s[df_all_s["result_24h"] != ""]
                success_all   = len(completed_all[completed_all["result_24h"].str.startswith("✅",na=False)])
                t2_all  = len(completed_all[completed_all["result_24h"].str.contains("هدف 2",na=False)])
                t1_all  = len(completed_all[completed_all["result_24h"].str.contains("هدف 1",na=False)])
                stop_all= len(completed_all[completed_all["result_24h"].str.startswith("❌",na=False)])

                c1,c2,c3,c4 = st.columns(4)
                c1.metric("إجمالي الكل", total_all)
                c2.metric("مكتملة", len(completed_all))
                c3.metric("✅ هدف 2", t2_all)
                c4.metric("❌ Stop", stop_all)

                if len(completed_all) > 0:
                    rate_all = round(success_all/len(completed_all)*100,1)
                    avg_rr = round(t2_all/(stop_all+1), 2)
                    c1b,c2b = st.columns(2)
                    c1b.metric("نسبة النجاح الكلية", f"{rate_all}%")
                    c2b.metric("نسبة R/R الفعلية", f"{avg_rr}:1")
                    if rate_all >= 65: st.success(f"🎯 النموذج ممتاز — {rate_all}% على كل التاريخ")
                    elif rate_all >= 55: st.warning(f"📊 النموذج جيد — {rate_all}%")
                    else: st.error(f"⚠️ {rate_all}% — يحتاج مراجعة")

                st.dataframe(df_all_s.head(100), use_container_width=True)

                # تصدير كل السجل
                excel_all = build_excel_report(df_all_s, "all")
                st.download_button(
                    "⬇️ تحميل كل السجل Excel",
                    excel_all,
                    f"سجل_كامل_{now.strftime('%Y_%m_%d')}.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        except Exception as e:
            st.info(f"ستظهر البيانات بعد أول إشارة — {e}")

    # حفظ تقرير يومي CSV بعد الإغلاق
    if after_close and all_data:
        df_save = pd.DataFrame(all_data)
        path = os.path.join(DAILY_DIR, f"{now.strftime('%Y_%m_%d')}.csv")
        save_c = ["الرمز","الاسم","السعر","التغيير%","الإشارة","الثقة%",
                  "RSI","MACD زخم","توصية المحللين","هامش الأمان%",
                  "صافي السيولة (M)","القوة%","طبقة البيانات","Breakout"]
        save_c = [c for c in save_c if c in df_save.columns]
        df_save[save_c].to_csv(path, index=False, encoding="utf-8-sig")

# ─── اختبار الاستراتيجية (Backtest) ───
with tab_backtest:
    st.subheader("🧪 اختبار الاستراتيجية — تحليل الأهداف والتوقيت")
    st.markdown("""
    **كيف يعمل:**
    - يأخذ البيانات التاريخية لكل سهم (يومية)
    - لكل يوم: يحسب الإشارة بناءً على ما قبله فقط (لا يرى المستقبل)
    - يقيس: هل وصل الهدف؟ متى وصل؟ هل ضرب الـ Stop؟
    - يحلل: متوسط وقت تحقيق كل هدف، نسبة النجاح، R/R الفعلي
    """)

    def backtest_one_stock_v12(sym, name, n_days=20, skip_down=False):
        try:
            closes, highs, lows, volumes = get_historical(sym)
            if len(closes) < n_days + 50:
                return []
            results = []
            start_idx = len(closes) - n_days
            last_signal_day = -10  # cooldown 5 أيام — يمنع تكرار نفس السهم (test13)
            for i in range(start_idx, len(closes) - 1):
                c = closes[:i]; h = highs[:i]; l = lows[:i]; v = volumes[:i]
                if len(c) < 30: continue

                # Cooldown: تجاهل إذا أعطينا إشارة على هذا السهم في آخر 5 أيام
                if (i - last_signal_day) < 5:
                    continue

                price      = closes[i-1]
                change_pct = (closes[i-1] - closes[i-2]) / closes[i-2] * 100 if i > 1 else 0

                # فلتر: تجاهل لو السهم هابط في آخر 3 أيام (بديل عن TASI التاريخي)
                if skip_down and i >= 4:
                    avg_3day_chg = (closes[i-1] - closes[i-4]) / closes[i-4] * 100
                    if avg_3day_chg < -2.0:
                        continue

                rsi      = calc_rsi(c)
                rsi_dir  = calc_rsi_direction(c)
                macd, macd_sig, macd_hist = calc_macd(c)
                macd_dir = calc_macd_direction(c)
                ma20     = calc_ma(c, 20)
                ma50     = calc_ma(c, 50)
                bb_up, _, bb_low = calc_bollinger(c)
                atr      = calc_atr(h, l, c)
                stoch_k  = calc_stochastic(h, l, c)
                williams_r_v = calc_williams_r(h, l, c)
                mom      = calc_momentum(c)
                vol_high, vol_very, vol_ratio, avg_vol = calc_volume(v)
                liq_score = calc_liquidity_score(vol_ratio, avg_vol)
                slip_pct, _ = calc_slippage(liq_score)
                entry = round(price * (1 + slip_pct), 2)

                # test14: حساب relative_strength تاريخياً
                # نقارن أداء السهم بمتوسط أداء الأسهم الأخرى في نفس الفترة
                # تقدير بسيط: change_pct vs متوسط السوق المقدّر
                hist_tasi_est = (closes[i-1] - closes[max(0,i-6)]) / closes[max(0,i-6)] * 100 / 5 if i > 5 else 0
                bt_rs = change_pct - hist_tasi_est

                # fair price margin من البيانات التاريخية (0 لأنه غير متاح)
                bt_fpm = 0.0

                score, reasons = get_strength_v12(
                    change_pct, rsi, rsi_dir, macd, macd_sig, macd_hist, macd_dir,
                    ma20, ma50, price, vol_high, vol_very, vol_ratio,
                    hist_tasi_est, 0, 0, bb_low, bb_up, False,
                    stoch_k, williams_r_v, mom, None, "", 0.0, "neutral", "regular", 1.0, liq_score
                )
                confidence = calc_confidence_v12(score, rsi_dir, macd_dir, vol_high, vol_very,
                                                  hist_tasi_est, None, "", 0.0, price)
                # test14: فلتر الأحد — بعد حساب score
                bt_day_of_week = i % 5
                if bt_day_of_week == 0 and score < 72:
                    continue

                signal, sig_type = get_signal_v12(
                    score, rsi, confidence, price, ma50,
                    change_pct, liq_score, vol_ratio, atr or 0, False, None,
                    bt_rs, True, bt_fpm
                )
                if not atr or atr == 0: continue
                t1, t2, stop, t1_pct, t2_pct, _ = calc_targets_and_sl(entry, atr, confidence)

                # النتيجة خلال 3 أيام (بدل يوم واحد فقط)
                # نبحث في أقرب 3 أيام بعد الإشارة
                fwd_days = min(3, len(closes) - i - 1)
                next_high  = max(highs[i:i+fwd_days+1]) if fwd_days > 0 else highs[i]
                next_low   = min(lows[i:i+fwd_days+1])  if fwd_days > 0 else lows[i]
                next_close = closes[i+fwd_days]          if fwd_days > 0 else closes[i]
                actual_chg = round((next_close - price) / price * 100, 2)

                hit_t2   = next_high >= t2
                hit_t1   = next_high >= t1
                hit_stop = next_low  <= stop

                # وقت التحقيق (بالأيام)
                days_to_target = None
                if hit_t2 or hit_t1:
                    # نحدد في أي يوم من الـ 3 أيام تحقق الهدف
                    for fwd in range(0, fwd_days+1):
                        if i + fwd < len(highs):
                            if hit_t2 and highs[i+fwd] >= t2:
                                days_to_target = fwd + 1; break
                            elif hit_t1 and highs[i+fwd] >= t1:
                                days_to_target = fwd + 1; break

                if hit_t2:
                    outcome = "✅ هدف 2"; pnl_pct = t2_pct
                elif hit_t1 and not hit_stop:
                    outcome = "🟡 هدف 1"; pnl_pct = t1_pct
                elif hit_stop and not hit_t1:
                    outcome = "❌ Stop Loss"
                    pnl_pct = round((stop - entry) / entry * 100, 2)
                elif hit_t1 and hit_stop:
                    outcome = "🟡 هدف 1 ثم Stop"; pnl_pct = t1_pct / 2
                else:
                    outcome = "⏳ لم يصل"; pnl_pct = actual_chg

                results.append({
                    "الرمز": sym, "الاسم": name,
                    "يوم": i - start_idx + 1,
                    "السعر": price, "الإشارة": signal,
                    "نوع الإشارة": sig_type,
                    "القوة%": score, "الثقة%": confidence, "RSI": rsi,
                    "هدف1%": t1_pct, "هدف2%": t2_pct,
                    "تغيير_فعلي%": actual_chg,
                    "النتيجة": outcome, "ربح/خسارة%": pnl_pct,
                    "أيام_للهدف": days_to_target,
                    "ناجحة": 1 if ("✅" in outcome or "🟡" in outcome) else 0,
                })
                last_signal_day = i  # cooldown — لا إشارة جديدة لـ 5 أيام
            return results
        except:
            return []

    def run_backtest_v12(stocks_list, n_days=20, skip_down=False):
        all_results = []
        prog = st.progress(0)
        stat = st.empty()
        total = len(stocks_list)
        for i, (sym, name) in enumerate(stocks_list):
            stat.text(f"اختبار {i+1}/{total}: {sym} — {name}")
            results = backtest_one_stock_v12(sym, name, n_days, skip_down)
            all_results.extend(results)
            prog.progress((i+1)/total)
        prog.empty(); stat.empty()
        return all_results

    col_bt1, col_bt2, col_bt3, col_bt4 = st.columns(4)
    with col_bt1:
        bt_days = st.slider("عدد أيام الاختبار:", 5, 20, 20)
    with col_bt2:
        bt_scope = st.selectbox("النطاق:", ["أسهم سريعة (50 سهم)", "كل الأسهم (~214)"])
    with col_bt3:
        bt_filter = st.selectbox("فلتر:", ["BUY فقط", "كل الإشارات"])
    with col_bt4:
        bt_skip_down = st.checkbox("تجاهل أيام السهم هابط", value=True,
            help="يتجاهل الإشارات في الأيام اللي كان فيها السهم نفسه هابط خلال 3 أيام سابقة")

    run_bt = st.button("🚀 ابدأ اختبار الاستراتيجية", type="primary")

    if run_bt:
        import random
        if bt_scope == "أسهم سريعة (50 سهم)":
            stocks_to_test = random.sample(UNIQUE_STOCKS, min(50, len(UNIQUE_STOCKS)))
        else:
            stocks_to_test = UNIQUE_STOCKS

        with st.spinner(f"جاري اختبار {len(stocks_to_test)} سهم على آخر {bt_days} يوم..."):
            bt_results = run_backtest_v12(stocks_to_test, bt_days, bt_skip_down)

        if not bt_results:
            st.error("❌ لم تُنتج أي نتائج — تحقق من البيانات")
        else:
            df_bt = pd.DataFrame(bt_results)
            if bt_filter == "BUY فقط":
                df_show_bt = df_bt[df_bt["نوع الإشارة"].isin(["strong","normal"])].copy()
            else:
                df_show_bt = df_bt.copy()

            total_sig  = len(df_show_bt)
            buy_sig    = len(df_show_bt[df_show_bt["نوع الإشارة"].isin(["strong","normal"])])
            won_bt     = df_show_bt["ناجحة"].sum()
            # نسبة النجاح على المكتملة فقط (هدف أو Stop) — "لم يصل" محايدة
            completed_bt = df_show_bt[df_show_bt["النتيجة"] != "⏳ لم يصل"]
            pending_bt   = len(df_show_bt) - len(completed_bt)
            succ_rate  = round(won_bt/len(completed_bt)*100, 1) if len(completed_bt) > 0 else 0
            hit_t2_bt = len(df_show_bt[df_show_bt["النتيجة"]=="✅ هدف 2"])
            hit_t1_bt = len(df_show_bt[df_show_bt["النتيجة"].str.contains("هدف 1",na=False)])
            hit_stop_bt = len(df_show_bt[df_show_bt["النتيجة"]=="❌ Stop Loss"])
            avg_win_bt  = df_show_bt[df_show_bt["ناجحة"]==1]["ربح/خسارة%"].mean()
            avg_loss_bt = df_show_bt[df_show_bt["ناجحة"]==0]["ربح/خسارة%"].mean()

            # ── وقت تحقيق الأهداف ──
            target_rows = df_show_bt[df_show_bt["أيام_للهدف"].notna()]
            avg_days_t1 = target_rows[target_rows["النتيجة"].str.contains("هدف 1",na=False)]["أيام_للهدف"].mean()
            avg_days_t2 = target_rows[target_rows["النتيجة"]=="✅ هدف 2"]["أيام_للهدف"].mean()

            st.divider()
            st.markdown("### 📊 نتائج اختبار الاستراتيجية")
            if bt_skip_down:
                st.info("🔍 الفلتر مفعّل: تم تجاهل الإشارات في أيام كان السهم هابطاً أكثر من 2% خلال 3 أيام سابقة")
            else:
                st.warning("⚠️ الفلتر مُعطَّل: النتائج تشمل أيام السوق الهابط — فعّل 'تجاهل أيام السهم هابط' للحصول على نتيجة أدق")
            m1,m2,m3,m4 = st.columns(4)
            m1.metric("إجمالي الإشارات", total_sig)
            m2.metric("ناجحة", int(won_bt))
            m3.metric("نسبة النجاح*", f"{succ_rate}%", delta=f"+{succ_rate-50:.1f}% عن العشوائي")
            m4.metric("⏳ معلقة (لم تصل)", pending_bt)
            st.caption(f"*النسبة محسوبة على {len(completed_bt)} إشارة مكتملة فقط (وصلت هدف أو Stop) — المعلقة تحتاج أكثر من يوم واحد")

            m5,m6,m7,m8 = st.columns(4)
            m5.metric("✅ وصل هدف 2", hit_t2_bt)
            m6.metric("🟡 وصل هدف 1", hit_t1_bt)
            m7.metric("❌ ضرب Stop", hit_stop_bt)
            m8.metric("R/R الفعلي", f"{round(hit_t2_bt/(hit_stop_bt+1),2)}:1")

            st.divider()
            st.markdown("### ⏱️ تحليل وقت تحقيق الأهداف")
            ta1,ta2,ta3,ta4 = st.columns(4)
            ta1.metric("متوسط أيام لهدف 1", f"{avg_days_t1:.1f}" if avg_days_t1 == avg_days_t1 else "—")
            ta2.metric("متوسط أيام لهدف 2", f"{avg_days_t2:.1f}" if avg_days_t2 == avg_days_t2 else "—")
            ta3.metric("متوسط ربح الناجحة", f"{avg_win_bt:.2f}%" if avg_win_bt == avg_win_bt else "—")
            ta4.metric("متوسط خسارة الفاشلة", f"{avg_loss_bt:.2f}%" if avg_loss_bt == avg_loss_bt else "—")

            st.divider()
            # حكم على النموذج
            if succ_rate >= 65:
                st.success(f"🎯 **الاستراتيجية ممتازة** — نسبة نجاح {succ_rate}%")
            elif succ_rate >= 55:
                st.warning(f"📊 **الاستراتيجية جيدة** — {succ_rate}% مع R/R 1:2")
            elif succ_rate >= 45:
                st.warning(f"⚠️ **متوسطة** — {succ_rate}% — تحتاج تحسين")
            else:
                st.error(f"❌ **ضعيفة** — {succ_rate}% — راجع الفلاتر")

            # ── تفاصيل ──
            bt_tab1, bt_tab2, bt_tab3, bt_tab4, bt_tab5 = st.tabs([
                "📋 كل الإشارات","✅ الناجحة","❌ الخاسرة",
                "📈 أداء كل سهم","⏱️ توزيع وقت الأهداف"
            ])

            show_cols_bt = ["الرمز","الاسم","الإشارة","القوة%","الثقة%",
                            "RSI","هدف1%","هدف2%","تغيير_فعلي%",
                            "النتيجة","ربح/خسارة%","أيام_للهدف"]
            show_cols_bt = [c for c in show_cols_bt if c in df_show_bt.columns]

            with bt_tab1:
                st.dataframe(df_show_bt[show_cols_bt].sort_values("ربح/خسارة%",ascending=False),
                             use_container_width=True, height=500,
                             column_config={
                                 "القوة%": st.column_config.ProgressColumn("القوة%",min_value=0,max_value=100),
                                 "الثقة%": st.column_config.ProgressColumn("الثقة%",min_value=0,max_value=100),
                             })
                csv_bt = df_show_bt[show_cols_bt].to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
                st.download_button("⬇️ تحميل CSV", csv_bt, f"backtest_{bt_days}days.csv","text/csv")

                # تصدير Excel كامل للـ Backtest
                bt_excel_out = io.BytesIO()
                with pd.ExcelWriter(bt_excel_out, engine="openpyxl") as bw:
                    df_show_bt.to_excel(bw, sheet_name="كل الإشارات", index=False)
                    df_show_bt[df_show_bt["ناجحة"]==1].to_excel(bw, sheet_name="الناجحة", index=False)
                    df_show_bt[df_show_bt["ناجحة"]==0].to_excel(bw, sheet_name="الخاسرة", index=False)
                    # ملخص
                    pd.DataFrame({
                        "المقياس": ["إجمالي","ناجحة","نسبة%","هدف2","هدف1","Stop","أيام_هدف1","أيام_هدف2"],
                        "القيمة":  [total_sig, int(won_bt), succ_rate, hit_t2_bt, hit_t1_bt, hit_stop_bt,
                                    round(avg_days_t1,1) if avg_days_t1==avg_days_t1 else 0,
                                    round(avg_days_t2,1) if avg_days_t2==avg_days_t2 else 0]
                    }).to_excel(bw, sheet_name="الملخص", index=False)
                bt_excel_out.seek(0)
                st.download_button(
                    "⬇️ تحميل Excel كامل للاختبار",
                    bt_excel_out.getvalue(),
                    f"backtest_excel_{bt_days}days.xlsx",
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

            with bt_tab2:
                df_won_bt = df_show_bt[df_show_bt["ناجحة"]==1].sort_values("ربح/خسارة%",ascending=False)
                if not df_won_bt.empty:
                    st.success(f"{len(df_won_bt)} إشارة ناجحة | متوسط: {df_won_bt['ربح/خسارة%'].mean():.2f}%")
                    st.dataframe(df_won_bt[show_cols_bt], use_container_width=True)
                else:
                    st.info("لا توجد إشارات ناجحة")

            with bt_tab3:
                df_lost_bt = df_show_bt[df_show_bt["ناجحة"]==0].sort_values("ربح/خسارة%")
                if not df_lost_bt.empty:
                    st.error(f"{len(df_lost_bt)} إشارة خاسرة | متوسط: {df_lost_bt['ربح/خسارة%'].mean():.2f}%")
                    st.dataframe(df_lost_bt[show_cols_bt], use_container_width=True)
                else:
                    st.success("لا توجد إشارات خاسرة! ✅")

            with bt_tab4:
                if "الرمز" in df_show_bt.columns:
                    stock_p = df_show_bt.groupby(["الرمز","الاسم"]).agg(
                        إشارات=("الإشارة","count"),
                        ناجحة=("ناجحة","sum"),
                        متوسط_الربح=("ربح/خسارة%","mean"),
                        أفضل=("ربح/خسارة%","max"),
                        أسوأ=("ربح/خسارة%","min"),
                        متوسط_أيام=("أيام_للهدف","mean")
                    ).reset_index()
                    stock_p["نسبة%"] = (stock_p["ناجحة"]/stock_p["إشارات"]*100).round(1)
                    stock_p = stock_p.sort_values("نسبة%", ascending=False)
                    st.dataframe(stock_p, use_container_width=True, height=500,
                        column_config={"نسبة%": st.column_config.ProgressColumn("نسبة%",min_value=0,max_value=100)})

            with bt_tab5:
                days_dist = df_show_bt[df_show_bt["أيام_للهدف"].notna()].groupby("أيام_للهدف").size().reset_index(name="عدد")
                if not days_dist.empty:
                    st.markdown("**توزيع عدد الأيام لتحقيق الهدف:**")
                    st.dataframe(days_dist, use_container_width=True)
                    outcome_dist = df_show_bt.groupby("النتيجة").size().reset_index(name="عدد")
                    st.markdown("**توزيع النتائج:**")
                    st.dataframe(outcome_dist, use_container_width=True)
                else:
                    st.info("لا توجد بيانات كافية لتحليل التوقيت")

st.divider()
st.caption(f"⚠️ test12 — مرجع تقني | آخر مسح: {st.session_state.last_scan_time or '—'} | للمعلومات فقط، ليست توصية استثمارية")
