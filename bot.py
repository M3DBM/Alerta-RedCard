import requests
import time
import os
import asyncio
from telegram import Bot

TOKEN = os.environ.get("TOKEN")
CANAL = os.environ.get("CANAL")

LIGAS = ["bra.1","eng.1","esp.1","ita.1","ger.1","fra.1","uefa.champions","conmebol.libertadores"]

bot = Bot(token=TOKEN)
enviados = set()

print("Bot iniciado - vigiando cartões vermelhos...")

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
                        if 'red card' in tipo or 'cartao vermelho' in tipo:
                            if d['id'] not in enviados:
                                time_jogo = jogo['status'].get('displayClock','AO VIVO')
                                nome = jogo.get('name','Jogo')
                                msg = f"🔴 CARTÃO VERMELHO!\n\n🏆 {liga.upper()}\n⚽ {nome}\n⏱️ {time_jogo}\n\n#RedCard #AoVivo"
                                asyncio.run(bot.send_message(chat_id=CANAL, text=msg))
                                enviados.add(d['id'])
                                print(f"Alerta enviado: {nome}")
            except Exception as e:
                print(f"Erro na liga {liga}: {e}")
                continue
        time.sleep(60)
    except Exception as e:
        print(f"Erro geral: {e}")
        time.sleep(60)
