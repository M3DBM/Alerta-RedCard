import requests, time, os, threading
from flask import Flask

TOKEN = os.environ.get("TOKEN") or os.environ.get("BOT_TOKEN")
CANAL = os.environ.get("CANAL")
enviados = set()
app = Flask(__name__)

@app.route('/')
def home(): return "Bot RedCard Online - TODAS AS LIGAS!"

def enviar(msg):
    requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", data={"chat_id": CANAL, "text": msg}, timeout=10)

def vigiar():
    print("Bot iniciado - TODAS AS LIGAS", flush=True)
    while True:
        try:
            # 1 REQUISIÇÃO PEGA TUDO
            url = "https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard"
            r = requests.get(url, timeout=15).json()
            for jogo in r.get('events',[]):
                if jogo['status']['type']['state']!= 'in': continue

                # DETECÇÃO DUPLA: hasRedCard + texto do details
                tem_vermelho = jogo.get('hasRedCard', False)
                details = jogo['competitions'][0].get('details',[])
                for d in details:
                    if 'red card' in d.get('type',{}).get('text','').lower() or 'vermelho' in str(d).lower():
                        tem_vermelho = True

                if tem_vermelho:
                    # Evita mandar 2x o mesmo jogo
                    uid = jogo['id']
                    if uid not in enviados:
                        liga = jogo['competitions'][0].get('notes', [{}])[0].get('headline','Futebol')
                        msg = f"🔴 CARTÃO VERMELHO!\n\n🏆 {liga}\n⚽ {jogo.get('name')}\n⏱️ {jogo['status'].get('displayClock','AO VIVO')}\n\n#RedCard"
                        enviar(msg)
                        enviados.add(uid)
            time.sleep(30)
        except Exception as e:
            print(f"Erro: {e}")
            time.sleep(30)

threading.Thread(target=vigiar, daemon=True).start()
if __name__ == "__main__": app.run(host='0.0.0.0', port=10000)
