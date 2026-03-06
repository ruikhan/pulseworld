import sqlite3, os, json, random
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'pulseworld-dev-2026')
DB = 'pulseworld.db'

# ════════════════════════════════════════════════════════
# DATABASE
# ════════════════════════════════════════════════════════
def get_db():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db

def rows_to_dicts(rows):
    return [dict(r) for r in rows]

def init_db():
    db = get_db()
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            avatar_color TEXT DEFAULT '#6366f1',
            watchlist TEXT DEFAULT '[]',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS watchlist (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            asset_type TEXT DEFAULT 'stock',
            added_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT,
            tag TEXT DEFAULT 'general',
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            symbol TEXT NOT NULL,
            alert_type TEXT,
            target_price REAL,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    ''')
    db.commit()
    db.close()

# ════════════════════════════════════════════════════════
# STATIC DATA — Institutions, Power Index, Countries
# ════════════════════════════════════════════════════════
INSTITUTIONS = [
    {'name':'Federal Reserve','abbr':'FED','type':'Central Bank','country':'USA','flag':'🇺🇸',
     'founded':1913,'assets':'$8.9T','influence':98,'desc':'The central banking system of the United States. Controls USD monetary policy, sets interest rates, and acts as lender of last resort.',
     'latest_action':'Held rates at 5.25-5.50% — monitoring inflation trajectory','color':'#1d4ed8'},
    {'name':'International Monetary Fund','abbr':'IMF','type':'International','country':'Global','flag':'🌐',
     'founded':1944,'assets':'$1.1T SDR','influence':96,'desc':'189-country organization ensuring global monetary cooperation, financial stability, and providing loans to countries in crisis.',
     'latest_action':'Revised global growth forecast to 3.1% for 2025','color':'#0891b2'},
    {'name':'World Bank','abbr':'WB','type':'Development Bank','country':'Global','flag':'🌐',
     'founded':1944,'assets':'$700B+','influence':94,'desc':'Provides financial and technical assistance to developing countries for development programs that reduce poverty.',
     'latest_action':'Committed $100B climate finance package through 2030','color':'#059669'},
    {'name':'Bank for International Settlements','abbr':'BIS','type':'Central Bank Hub','country':'Switzerland','flag':'🇨🇭',
     'founded':1930,'assets':'$700B','influence':95,'desc':'The bank for central banks. Coordinates global monetary policy, sets Basel banking standards, and serves 63 central banks.',
     'latest_action':'Published Basel IV implementation guidelines for 2025','color':'#7c3aed'},
    {'name':'European Central Bank','abbr':'ECB','type':'Central Bank','country':'Eurozone','flag':'🇪🇺',
     'founded':1998,'assets':'€7.0T','influence':93,'desc':'Central bank for 20 EU countries using the Euro. Controls eurozone monetary policy and financial stability.',
     'latest_action':'Cut rates to 3.75% — first cut since 2019','color':'#2563eb'},
    {'name':'World Trade Organization','abbr':'WTO','type':'Trade Body','country':'Global','flag':'🌐',
     'founded':1995,'assets':'N/A','influence':88,'desc':'Regulates international trade between nations, resolves trade disputes, and negotiates trade agreements.',
     'latest_action':'Launched new AI trade framework negotiations','color':'#d97706'},
    {'name':'BlackRock','abbr':'BLK','type':'Asset Manager','country':'USA','flag':'🇺🇸',
     'founded':1988,'assets':'$10.5T AUM','influence':92,'desc':'World\'s largest asset manager. Controls more assets than any country\'s GDP except USA and China.',
     'latest_action':'Launched tokenized fund on Ethereum blockchain','color':'#1f2937'},
    {'name':'JPMorgan Chase','abbr':'JPM','type':'Investment Bank','country':'USA','flag':'🇺🇸',
     'founded':1799,'assets':'$3.9T','influence':91,'desc':'Largest US bank by assets. Dominant in investment banking, commercial banking, financial services and asset management.',
     'latest_action':'Q1 2025 profit surged 6% to $14.6B','color':'#1d4ed8'},
    {'name':'Goldman Sachs','abbr':'GS','type':'Investment Bank','country':'USA','flag':'🇺🇸',
     'founded':1869,'assets':'$1.6T','influence':90,'desc':'Premier global investment banking, securities and investment management firm. Known as "The Vampire Squid" for market influence.',
     'latest_action':'Raised S&P 500 year-end target to 5,600','color':'#374151'},
    {'name':'Vanguard Group','abbr':'VG','type':'Asset Manager','country':'USA','flag':'🇺🇸',
     'founded':1975,'assets':'$8.6T AUM','influence':89,'desc':'Second largest asset manager globally. Pioneered index fund investing. Owns significant shares in virtually every major corporation.',
     'latest_action':'Surpassed $8.6T in assets under management','color':'#dc2626'},
]

BIG_TECH = [
    {'name':'Apple','symbol':'AAPL','sector':'Consumer Tech','country':'USA','flag':'🇺🇸','market_cap':'$3.5T','employees':'164K','influence':97,'color':'#1f2937','desc':'World\'s most valuable company. Controls iPhone ecosystem, App Store, and expanding services empire.'},
    {'name':'Microsoft','symbol':'MSFT','sector':'Cloud/AI','country':'USA','flag':'🇺🇸','market_cap':'$3.2T','employees':'221K','influence':96,'color':'#0ea5e9','desc':'Dominates enterprise software, Azure cloud, and made the defining AI bet with OpenAI partnership.'},
    {'name':'NVIDIA','symbol':'NVDA','sector':'AI/Semiconductors','country':'USA','flag':'🇺🇸','market_cap':'$2.9T','employees':'29K','influence':95,'color':'#16a34a','desc':'The indispensable AI infrastructure company. Makes GPUs that power every major AI model.'},
    {'name':'Alphabet','symbol':'GOOGL','sector':'Advertising/AI','country':'USA','flag':'🇺🇸','market_cap':'$2.1T','employees':'182K','influence':94,'color':'#ea4335','desc':'Controls global search (92% share), YouTube, Android, and Google Cloud. Owns your attention.'},
    {'name':'Amazon','symbol':'AMZN','sector':'Cloud/Commerce','country':'USA','flag':'🇺🇸','market_cap':'$1.9T','employees':'1.5M','influence':93,'color':'#f97316','desc':'Dominates e-commerce and cloud (AWS powers ~33% of the internet). Expanding into healthcare and logistics.'},
    {'name':'Meta','symbol':'META','sector':'Social Media/AI','country':'USA','flag':'🇺🇸','market_cap':'$1.4T','employees':'67K','influence':91,'color':'#2563eb','desc':'Controls Facebook, Instagram, WhatsApp — 3.2B daily users. Betting the company on AI and the Metaverse.'},
    {'name':'Tesla','symbol':'TSLA','sector':'EV/Energy/AI','country':'USA','flag':'🇺🇸','market_cap':'$780B','employees':'140K','influence':88,'color':'#dc2626','desc':'Pioneered EVs and leads in autonomous driving. Elon Musk\'s proximity to power adds geopolitical weight.'},
    {'name':'TSMC','symbol':'TSM','sector':'Semiconductors','country':'Taiwan','flag':'🇹🇼','market_cap':'$840B','employees':'73K','influence':92,'color':'#7c3aed','desc':'Makes 90% of world\'s advanced chips. The single most strategically critical company on Earth.'},
    {'name':'Samsung','symbol':'005930.KS','sector':'Electronics','country':'South Korea','flag':'🇰🇷','market_cap':'$380B','employees':'270K','influence':87,'color':'#1d4ed8','desc':'World\'s largest smartphone maker and memory chip producer. Controls critical supply chains.'},
    {'name':'Alibaba','symbol':'BABA','sector':'Commerce/Cloud','country':'China','flag':'🇨🇳','market_cap':'$210B','employees':'225K','influence':85,'color':'#f59e0b','desc':'China\'s dominant e-commerce and cloud empire. Subject to Beijing regulatory control — a reminder of who holds ultimate power.'},
]

GEOPOLITICAL = [
    {'country':'United States','code':'US','flag':'🇺🇸','power_score':99,'gdp':'$27.4T','military':'$886B','currency':'USD','stability':'High','risk':'Low','desc':'Sole hyperpower. Controls reserve currency, leads NATO, dominates global finance and technology.'},
    {'country':'China','code':'CN','flag':'🇨🇳','power_score':94,'gdp':'$17.7T','military':'$224B','currency':'CNY','stability':'Medium','risk':'Medium','desc':'Rising superpower challenging US hegemony. Belt & Road Initiative spans 140+ countries.'},
    {'country':'European Union','code':'EU','flag':'🇪🇺','power_score':88,'gdp':'$18.4T','military':'$350B+','currency':'EUR','stability':'High','risk':'Low','desc':'World\'s largest single market. Regulatory superpower — EU rules shape global corporate behavior.'},
    {'country':'Russia','code':'RU','flag':'🇷🇺','power_score':78,'gdp':'$2.2T','military':'$109B','currency':'RUB','stability':'Low','risk':'High','desc':'Nuclear superpower with vast resources. Under severe sanctions since 2022 Ukraine invasion.'},
    {'country':'Japan','code':'JP','flag':'🇯🇵','power_score':82,'gdp':'$4.2T','military':'$51B','currency':'JPY','stability':'High','risk':'Low','desc':'Third largest economy. Major US ally, holds largest foreign reserves. Aging demographic challenge.'},
    {'country':'India','code':'IN','flag':'🇮🇳','power_score':80,'gdp':'$3.7T','military':'$83B','currency':'INR','stability':'Medium','risk':'Low-Medium','desc':'Fastest growing major economy. Largest democracy, world\'s most populous nation. Rising tech power.'},
    {'country':'Saudi Arabia','code':'SA','flag':'🇸🇦','power_score':76,'gdp':'$1.1T','military':'$80B','currency':'SAR','stability':'Medium','risk':'Medium','desc':'Controls 17% of global oil reserves. OPEC leader. Vision 2030 transformation underway.'},
    {'country':'United Kingdom','code':'GB','flag':'🇬🇧','power_score':79,'gdp':'$3.1T','military':'$68B','currency':'GBP','stability':'High','risk':'Low','desc':'Post-Brexit global Britain. Permanent UN Security Council member. London remains global finance hub.'},
]

AVATAR_COLORS = ['#6366f1','#10b981','#f59e0b','#ec4899','#3b82f6','#ef4444','#8b5cf6','#14b8a6']

# ════════════════════════════════════════════════════════
# AUTH
# ════════════════════════════════════════════════════════
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

@app.route('/')
def index():
    return redirect(url_for('dashboard') if 'user_id' in session else url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    error = None
    if request.method == 'POST':
        email = request.form.get('email','').strip()
        password = request.form.get('password','')
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
        db.close()
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            session['avatar_color'] = user['avatar_color']
            return redirect(url_for('dashboard'))
        error = 'Invalid email or password.'
    return render_template('login.html', error=error)

@app.route('/register', methods=['GET','POST'])
def register():
    error = None
    if request.method == 'POST':
        name = request.form.get('name','').strip()
        email = request.form.get('email','').strip()
        password = request.form.get('password','')
        if not name or not email or not password:
            error = 'All fields are required.'
        else:
            color = random.choice(AVATAR_COLORS)
            try:
                db = get_db()
                db.execute('INSERT INTO users (name,email,password,avatar_color) VALUES (?,?,?,?)',
                           (name, email, generate_password_hash(password), color))
                db.commit()
                user = db.execute('SELECT * FROM users WHERE email=?',(email,)).fetchone()
                db.close()
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                session['avatar_color'] = color
                return redirect(url_for('dashboard'))
            except sqlite3.IntegrityError:
                error = 'Email already registered.'
    return render_template('register.html', error=error)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# ════════════════════════════════════════════════════════
# MAIN ROUTES
# ════════════════════════════════════════════════════════
@app.route('/dashboard')
@login_required
def dashboard():
    uid = session['user_id']
    db = get_db()
    watchlist = rows_to_dicts(db.execute('SELECT * FROM watchlist WHERE user_id=? ORDER BY added_at DESC', (uid,)).fetchall())
    recent_notes = rows_to_dicts(db.execute('SELECT * FROM notes WHERE user_id=? ORDER BY created_at DESC LIMIT 3', (uid,)).fetchall())
    db.close()
    return render_template('dashboard.html', watchlist=watchlist, recent_notes=recent_notes)

@app.route('/markets')
@login_required
def markets():
    return render_template('markets.html')

@app.route('/institutions')
@login_required
def institutions():
    return render_template('institutions.html', institutions=INSTITUTIONS)

@app.route('/bigtech')
@login_required
def bigtech():
    return render_template('bigtech.html', companies=BIG_TECH)

@app.route('/geopolitical')
@login_required
def geopolitical():
    return render_template('geopolitical.html', countries=GEOPOLITICAL)

@app.route('/watchlist', methods=['GET','POST'])
@login_required
def watchlist():
    uid = session['user_id']
    db = get_db()
    if request.method == 'POST':
        symbol = request.form.get('symbol','').upper().strip()
        asset_type = request.form.get('asset_type','stock')
        if symbol:
            existing = db.execute('SELECT id FROM watchlist WHERE user_id=? AND symbol=?',(uid,symbol)).fetchone()
            if not existing:
                db.execute('INSERT INTO watchlist (user_id,symbol,asset_type) VALUES (?,?,?)',(uid,symbol,asset_type))
                db.commit()
        db.close()
        return redirect(url_for('watchlist'))
    items = rows_to_dicts(db.execute('SELECT * FROM watchlist WHERE user_id=? ORDER BY added_at DESC',(uid,)).fetchall())
    db.close()
    return render_template('watchlist.html', items=items)

@app.route('/watchlist/remove/<int:wid>', methods=['POST'])
@login_required
def remove_watchlist(wid):
    db = get_db()
    db.execute('DELETE FROM watchlist WHERE id=? AND user_id=?',(wid, session['user_id']))
    db.commit()
    db.close()
    return redirect(url_for('watchlist'))

@app.route('/notes', methods=['GET','POST'])
@login_required
def notes():
    uid = session['user_id']
    db = get_db()
    if request.method == 'POST':
        db.execute('INSERT INTO notes (user_id,title,content,tag) VALUES (?,?,?,?)',
                   (uid, request.form.get('title',''), request.form.get('content',''), request.form.get('tag','general')))
        db.commit()
        db.close()
        return redirect(url_for('notes'))
    all_notes = rows_to_dicts(db.execute('SELECT * FROM notes WHERE user_id=? ORDER BY created_at DESC',(uid,)).fetchall())
    db.close()
    return render_template('notes.html', notes=all_notes)

@app.route('/notes/delete/<int:nid>', methods=['POST'])
@login_required
def delete_note(nid):
    db = get_db()
    db.execute('DELETE FROM notes WHERE id=? AND user_id=?',(nid, session['user_id']))
    db.commit()
    db.close()
    return redirect(url_for('notes'))

# ════════════════════════════════════════════════════════
init_db()
if __name__ == '__main__':
    app.run(debug=True)
