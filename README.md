# 🤖 TraderBot — AI-Powered WhatsApp Business Assistant for Nigerian Traders

TraderBot is a fully automated, AI-powered WhatsApp chatbot built specifically for Nigerian market traders and small business owners. It understands natural Nigerian language — English, Pidgin, and mixed speech — and helps traders record sales, track stock, manage debts, and get business insights, all through WhatsApp without downloading any app.

## 🔗 Live Demo
The bot runs 24/7 at: **https://trader-bot-wavz.onrender.com**

---

## 🚀 What It Does

### 📦 Sales Recording
Record single or multiple sales in one message. The bot understands natural language:
```
I sell 3 bags rice 45k, 5 tins tomato 2k. I buy rice 38k, tomato 1.5k
```
It automatically calculates profit, deducts from stock, and saves everything.

### 🏪 Stock Management
Add new or old stock and track quantities in real time:
```
I buy 10 bags rice 20000 each, 20 tins tomato 500 each
show my stock
```
The bot shows ⚠️ LOW warnings when stock drops to 2 units or less.

### 📝 Debt Tracking
Record credit sales and track payments:
```
Amaka take 3 tins tomato 1000 each, go pay Friday
Amaka don pay 2000
who owe me money
how much Amaka owe me
```

### 📊 Business Summaries
Get summaries for any time period on demand:
```
my profit today
yesterday sales
this week summary
this month summary
last 5 days summary
weekend sales
sales from 2026-01-01 to 2026-01-31
```

### 🏆 Product & Customer Analysis
```
show top products       → revenue, profit, ROI per product
show top customers      → best customers by total purchases
sales chart             → visual revenue and profit chart
```

### 🏷️ Multiple Business Sections
Manage food, drinks, clothes, or any category separately:
```
switch to food
switch to drinks
food summary
drinks summary
show all sections
show food stock
```

### 🔄 Archive & Reset
```
I don finish the goods, start fresh
```
Archives all old records and starts a clean slate.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11 |
| Web Framework | Flask |
| AI / NLP | Groq API (LLaMA 3.3 70B) |
| WhatsApp | Twilio WhatsApp Sandbox |
| Database | Supabase (PostgreSQL) |
| Charts | Matplotlib |
| Hosting | Render.com (Free tier) |
| Version Control | Git & GitHub |

---

## 📁 Project Structure

```
trader-bot/
├── app.py                      # Flask webhook server
├── bot/
│   ├── __init__.py
│   ├── ai_engine.py            # Groq AI message understanding
│   ├── message_handler.py      # Business logic & reply generation
│   ├── db.py                   # Supabase database operations
│   └── charts.py               # Matplotlib chart generation
├── .env                        # Environment variables (not committed)
├── .gitignore
├── Procfile                    # Render deployment config
├── requirements.txt
└── README.md
```

---

## ⚙️ Setup & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/SamuelOyedokun/Trader-Bot.git
cd Trader-Bot
```

### 2. Create Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables
Create a `.env` file in the root directory:
```
GROQ_API_KEY=your_groq_api_key
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_WHATSAPP_NUMBER=+14155238886
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
VERIFY_TOKEN=traderbot123
```

### 5. Set Up Supabase Database
Run these SQL commands in your Supabase SQL Editor:

```sql
CREATE TABLE sales (
  id bigserial PRIMARY KEY,
  phone text,
  item text,
  quantity float4,
  selling_price float4,
  cost_price float4,
  profit float4,
  customer_name text,
  section text DEFAULT 'general',
  archived boolean DEFAULT false,
  archived_at timestamptz,
  created_at timestamptz default now()
);

CREATE TABLE stock (
  id bigserial PRIMARY KEY,
  phone text,
  item text,
  quantity float4,
  cost_price float4,
  section text DEFAULT 'general',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

CREATE TABLE debts (
  id bigserial PRIMARY KEY,
  phone text,
  customer_name text,
  item text,
  quantity float4,
  amount float4,
  amount_paid float4 DEFAULT 0,
  balance float4,
  due_date text,
  status text DEFAULT 'unpaid',
  section text DEFAULT 'general',
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

CREATE TABLE customers (
  id bigserial PRIMARY KEY,
  phone text,
  customer_name text,
  total_purchases float4 DEFAULT 0,
  total_orders int DEFAULT 0,
  created_at timestamptz default now(),
  updated_at timestamptz default now()
);

CREATE TABLE user_sections (
  id bigserial PRIMARY KEY,
  phone text UNIQUE,
  current_section text DEFAULT 'general',
  updated_at timestamptz default now()
);

ALTER TABLE sales DISABLE ROW LEVEL SECURITY;
ALTER TABLE stock DISABLE ROW LEVEL SECURITY;
ALTER TABLE debts DISABLE ROW LEVEL SECURITY;
ALTER TABLE customers DISABLE ROW LEVEL SECURITY;
ALTER TABLE user_sections DISABLE ROW LEVEL SECURITY;
```

### 6. Set Up Twilio WhatsApp Sandbox
- Go to [console.twilio.com](https://console.twilio.com)
- Navigate to **Messaging → Try it out → Send a WhatsApp message**
- Note your sandbox number and join code
- Set webhook URL to: `https://your-app-url.onrender.com/webhook`

### 7. Run Locally
```bash
# Terminal 1 - Start Flask
python app.py

# Terminal 2 - Expose with ngrok
cd ngrok-folder
.\ngrok.exe http 5000
```

---

## 🌐 Deployment (Render.com)

1. Push code to GitHub
2. Go to [render.com](https://render.com) and create a new **Web Service**
3. Connect your GitHub repository
4. Set **Start Command** to: `python app.py`
5. Add all environment variables from your `.env` file
6. Select **Free** tier and deploy

---

## 💬 Example Conversations

```
User: hello
Bot:  👋 Hello! I'm your business assistant.
      📍 Current section: GENERAL
      Here's what I can do: Record sales & stock,
      Daily/weekly/monthly summaries, Top products + ROI,
      Top customers, Sales charts, Debt tracking,
      Stock management, Multiple business sections

User: I sell 5 bags rice 45000 each, I buy am 38000
Bot:  ✅ Sales recorded! [GENERAL]
      📦 rice × 5
         Sell: ₦45,000 | Cost: ₦38,000 | Profit: ₦35,000
      💰 Total Profit: ₦35,000

User: Biodun take 2 bags rice 45000, go pay next week
Bot:  📝 Debt recorded! [GENERAL]
      👤 Biodun
      📦 rice × 2
      💰 Owes: ₦90,000
      📅 Due: next week

User: show top products
Bot:  🏆 Top Products
      1. rice
         💰 Revenue: ₦225,000
         📈 Profit: ₦35,000
         📊 ROI: 18.4%
         📦 Units sold: 5

User: switch to drinks
Bot:  ✅ Switched to DRINKS section!
      All sales, stock and summaries will now be
      recorded under drinks.
```

---

## 🔒 Security

- All credentials stored in `.env` file — never committed to GitHub
- `.gitignore` excludes `.env`, `venv/`, and `__pycache__/`
- Supabase handles secure cloud data storage

---

## 🗺️ Roadmap

- [ ] Voice note support (Whisper API transcription)
- [ ] Automated weekly Sunday summary to all users
- [ ] Debt reminder messages to customers
- [ ] Multi-language support (Yoruba, Hausa, Igbo)
- [ ] Payment integration (Paystack/Flutterwave)
- [ ] Admin dashboard for bot owner
- [ ] Subscription billing system

---

## 👤 Author

**Samuel Oyedokun**  
[GitHub](https://github.com/SamuelOyedokun)

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

> Built with ₦0 startup cost. Designed for the 40 million+ informal traders across Nigeria. 🇳🇬
