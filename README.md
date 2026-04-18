# 🤖 JARVIS AI — ALEXA SKILL ON VERCEL
## "Alexa, Bhaiya, Sahiba gana chalado"
## Free Forever | No Card | No Expiry | Always On

---

## WHY VERCEL?
- ✅ No credit card needed
- ✅ Free forever (not 6 months)
- ✅ HTTPS included automatically
- ✅ Always on — no PC needed
- ✅ Deploy in 5 minutes with GitHub

---

## FILE STRUCTURE
```
jarvis-vercel/
├── api/
│   └── index.py              ← Main Alexa Flask handler
├── chatbot.py                ← Groq AI chatbot
├── realtime_search.py        ← Google + Groq real-time search
├── model.py                  ← Cohere decision model
├── automation.py             ← Voice automations
├── music_player.py           ← yt-dlp ad-free YouTube streaming
├── interactionModels/
│   └── custom/
│       └── en-US.json        ← Alexa voice model
├── skill.json                ← Alexa skill manifest
├── vercel.json               ← Vercel config
├── requirements.txt          ← Python dependencies
└── README.md
```

---

## COMPLETE SETUP GUIDE

---

### PART 1 — DEPLOY ON VERCEL (5 minutes)

#### Step 1 — Create GitHub Account
Go to https://github.com and sign up (free, no card)

#### Step 2 — Create New GitHub Repository
1. Click **+** (top right) → **New repository**
2. Name: `jarvis-bhaiya`
3. Set to **Private**
4. Click **Create repository**

#### Step 3 — Upload Your Files to GitHub
1. Click **uploading an existing file**
2. Drag and drop ALL files from this folder:
   - `vercel.json`
   - `requirements.txt`
   - `skill.json`
   - `chatbot.py`
   - `realtime_search.py`
   - `model.py`
   - `automation.py`
   - `music_player.py`
3. Also upload the `api/` folder (upload `api/index.py`)
4. Also upload `interactionModels/custom/en-US.json`
5. Click **Commit changes**

#### Step 4 — Create Vercel Account
1. Go to https://vercel.com
2. Click **Sign Up**
3. Choose **Continue with GitHub** (no card needed!)
4. Authorize Vercel

#### Step 5 — Deploy on Vercel
1. Click **Add New** → **Project**
2. Find your `jarvis-bhaiya` repo → click **Import**
3. Click **Deploy** (leave all settings as default)
4. Wait ~2 minutes for deployment
5. You'll see: **"Congratulations! Your project is deployed"**
6. Copy your URL — it looks like: `https://jarvis-bhaiya.vercel.app`

#### Step 6 — Add Environment Variables on Vercel
1. In Vercel dashboard → your project → **Settings** → **Environment Variables**
2. Add these one by one:

| Name | Value |
|---|---|
| `GroqAPIKey` | your-groq-api-key |
| `CohereApiKey` | your-cohere-api-key |
| `Username` | Sir |
| `AssistantName` | Jarvis |

3. Click **Save** for each
4. Go to **Deployments** → click the 3 dots → **Redeploy**

#### Step 7 — Verify It's Working
Open your browser and go to:
```
https://jarvis-bhaiya.vercel.app/
```
You should see:
```
✅ Jarvis AI skill is running on Vercel! Endpoint: /alexa
```

Your Alexa endpoint URL is:
```
https://jarvis-bhaiya.vercel.app/alexa
```
**Save this URL — you need it for Alexa setup.**

---

### PART 2 — CREATE ALEXA SKILL (10 minutes)

#### Step 8 — Create Amazon Developer Account
1. Go to https://developer.amazon.com
2. Sign in with your **same Amazon account** linked to your Echo device
3. No payment needed for developer account

#### Step 9 — Create New Skill
1. Go to https://developer.amazon.com/alexa/console/ask
2. Click **Create Skill**
3. Fill in:
   - Skill name: `Bhaiya`
   - Primary locale: **English (US)**
   - Model: **Custom**
   - Backend: **Provision your own**
4. Click **Create skill**
5. Choose **Start from scratch** → **Continue with template**

#### Step 10 — Set Invocation Name
1. Left sidebar → **Invocations** → **Skill Invocation Name**
2. Type: `bhaiya`
3. Click **Save Model**

#### Step 11 — Import Voice Model
1. Left sidebar → **JSON Editor**
2. Select ALL text and DELETE it
3. Open `interactionModels/custom/en-US.json` from this folder
4. Copy ALL its contents and paste into the JSON Editor
5. Click **Save Model**
6. Click **Build Model** (takes ~2 minutes)

#### Step 12 — Enable Audio Player (REQUIRED for music!)
1. Left sidebar → **Interfaces**
2. Find **Audio Player** → toggle it **ON**
3. Click **Save Interfaces**
4. Click **Build Model** again

#### Step 13 — Set Your Vercel Endpoint
1. Left sidebar → **Endpoint**
2. Select **HTTPS**
3. In the **Default Region** box, paste:
   ```
   https://jarvis-bhaiya.vercel.app/alexa
   ```
   (replace with your actual Vercel URL)
4. Under **SSL certificate type** select:
   **"My development endpoint has a certificate from a trusted certificate authority"**
   (Vercel's SSL is trusted ✅)
5. Click **Save Endpoints**

#### Step 14 — Test in Developer Console
1. Click **Test** tab
2. Change dropdown from **Off** to **Development**
3. In the text box type: `open bhaiya`
4. You should hear Matthew's voice respond in Hindi!
5. Type: `Sahiba gana chalado`
6. Music should start playing!

#### Step 15 — Enable on Your Echo Device
1. Open **Alexa app** on your phone
2. Go to: **More** → **Skills & Games** → **Your Skills** → **Dev** tab
3. You'll see **Bhaiya** skill — tap **Enable**
4. Now say on your Echo:

```
"Alexa, Bhaiya, Sahiba gana chalado"
```

🎶 **Sahiba plays instantly, completely ad-free!**

---

## ALL VOICE COMMANDS

| You say | What happens |
|---|---|
| `Alexa, Bhaiya` | Opens skill, Matthew greets in Hindi |
| `Alexa, Bhaiya, Sahiba gana chalado` | Streams Sahiba ad-free |
| `Alexa, Bhaiya, Tum Hi Ho bajao` | Streams Tum Hi Ho |
| `Alexa, Bhaiya, play Shape of You` | Streams Shape of You |
| `Alexa, Bhaiya, aaj ka news kya hai` | Real-time news |
| `Alexa, Bhaiya, who is Virat Kohli` | AI answer |
| `Alexa, Bhaiya, search Google for best phones` | Reads results |
| `Alexa, Bhaiya, write an email to my boss` | Writes email |
| `Alexa, pause` | Pauses music |
| `Alexa, resume` | Resumes music |
| `Alexa, stop` | Stops everything |

---

## API KEYS (Free — No Card)

| Service | Get Key At | Cost |
|---|---|---|
| Groq (AI) | https://console.groq.com | Free forever |
| Cohere (decisions) | https://dashboard.cohere.com | Free forever |
| Vercel (hosting) | https://vercel.com | Free forever |
| Amazon Developer | https://developer.amazon.com | Free forever |

---

## TROUBLESHOOTING

| Problem | Solution |
|---|---|
| Health check shows error | Check Vercel logs → Project → Functions tab |
| "There was a problem" on Echo | Check env variables are set in Vercel |
| Music not playing | Make sure AudioPlayer interface is enabled + model rebuilt |
| Skill not on Echo | Re-enable in Alexa app → More → Skills → Dev tab |
| API errors | Check GroqAPIKey and CohereApiKey in Vercel env vars |

**View Vercel logs:**
Vercel Dashboard → Your Project → **Functions** tab → click `/api/index` → see real-time logs

---

## COST = ₹0 / $0 FOREVER

| Service | Free Limit | Your Usage |
|---|---|---|
| Vercel | 100GB bandwidth/month | ~0.1GB |
| Groq | 14,400 requests/day | ~10-50/day |
| Cohere | 1000 requests/month | ~10-50/day on trial |
| yt-dlp | Unlimited | Free, open source |
