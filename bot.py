import requests, time, os, asyncio, threading
from telegram import Bot
from flask import Flask

TOKEN = os.environ.get("TOKEN")
CANAL = os.environ.get("CANAL")

LIGAS = ["bra.1","eng.1","esp.1","ita.1","ger.1","fra.1","uefa.champions","conmebol.libertadores"]
bot = Bot(token=TOKEN)
enviados = set()

# site fake pra Render não reclamar da porta
app = Flask(__name__)
@app.route('/')
def home():
    return "Bot RedCard Online - Vigiando..."

def vigiar_jogos():
    print("Bot iniciado - vigiando cartoes vermelhos...")
    while True:
        try:
            for liga in LIGAS:
                try:
                    url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/{liga}/scoreboard"
                    r = requests.get(url, timeout=10).json()
                    for jogo in r.get('events',[]):
                        if jogo['status']['type']['state']!= 'in': continue
                        for d in jogo['competitions'][0].get('details',[]):
                            tipo = d.get('type',{}).get('text','').lower()
                            if 'red card' in tipo:
                                if d['id'] not in enviados:
                                    msg = f"🔴 CARTÃO VERMELHO!\n\n🏆 {liga.upper()}\n⚽ {jogo.get('name')}\n⏱️ {jogo['status'].get('displayClock','AO VIVO')}"
                                    asyncio.run(bot.send_message(chat_id=CANAL, text=msg))
                                    enviados.add(d['id'])
                                    print(f"Alerta: {jogo.get('name')}")
                except: pass
            time.sleep(60)
        except Exception as e:
            print(f"Erro: {e}")
            time.sleep(60)

# roda o vigia em segundo plano
threading.Thread(target=vigiar_jogos, daemon=True).start()

# abre a porta que o Render exige
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=10000)
