import requests, time, os, threading
from flask import Flask

TOKEN = os.environ.get("TOKEN") or os.environ.get("BOT_TOKEN")
CANAL = os.environ.get("CANAL")

LIGAS = ["bra.1","eng.1","esp.1","ita.1","ger.1","fra.1","uefa.champions","conmebol.libertadores"]
enviados = set()

app = Flask(__name__)
@app.route('/')
def home():
    return "Bot RedCard Online - Vigiando..."

def enviar_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        data = {"chat_id": CANAL, "text": msg}
        requests.post(url, data=data, timeout=10)
        print(f"Enviado: {msg[:50]}")
    except Exception as e:
        print(f"Erro telegram: {e}")

def vigiar_jogos():
    print("Bot iniciado - vigiando cartoes vermelhos...", flush=True)
    while True:
        try:
            for liga in LIGAS:
                try:
                    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{liga}/scoreboard"
                    r = requests.get(url, timeout=10).json()
                    for jogo in r.get('events',[]):
                        if jogo['status']['type']['state']!= 'in':
                            continue
                        details = jogo['competitions'][0].get('details',[])
                        for d in details:
                            tipo = d.get('type',{}).get('text','').lower()
                            if 'red card' in tipo or 'cartão vermelho' in tipo:
                                uid = d.get('id') or f"{jogo['id']}_{d.get('clock',{}).get('displayValue','')}"
                                if uid not in enviados:
                                    msg = f"🔴 CARTÃO VERMELHO!\n\n🏆 {liga.upper()}\n⚽ {jogo.get('name')}\n⏱️ {jogo['status'].get('displayClock','AO VIVO')}\n\n#RedCard"
                                    enviar_telegram(msg)
                                    enviados.add(uid)
                except Exception as e:
                    print(f"Erro liga {liga}: {e}")
                    continue
            time.sleep(60)
        except Exception as e:
            print(f"Erro geral: {e}")
            time.sleep(60)

threading.Thread(target=vigiar_jogos, daemon=True).start()

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
