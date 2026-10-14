import requests, time, os, traceback
from flask import Flask
import threading

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

app = Flask(__name__)
jogos_avisados = set()

def enviar_telegram(time_casa, time_fora, placar, minuto, time_cartao, tipo, liga_nome):
    tag = f"[{liga_nome}]" if liga_nome else ""
    icone = "🔴 RED CARD!" if tipo == "VERMELHO" else "🟨 AMARELO!"
    texto = f"{icone} {tag} {time_casa} {placar} {time_fora} ({minuto}')\n{time_cartao} - {tipo}"
    try:
        requests.post(TELEGRAM_URL, data={"chat_id": CHAT_ID, "text": texto}, timeout=10)
        print(f"ENVIADO: {texto}", flush=True)
    except Exception as e:
        print(f"Erro telegram: {e}", flush=True)

def verificar_jogos():
    print(">>> BOT INICIADO - VERIFICANDO JOGOS <<<", flush=True)
    url = "https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard"
    while True:
        try:
            print("Tentando buscar na ESPN...", flush=True)
            r = requests.get(url, timeout=20)
            print(f"ESPN status: {r.status_code}", flush=True)
            data = r.json()
            events = data.get("events", [])
            print(f"Encontrados {len(events)} eventos totais", flush=True)

            achou_ao_vivo = 0
            for event in events:
                state = event.get("status", {}).get("type", {}).get("state")
                if state!= "in":
                    continue
                achou_ao_vivo += 1
                comp_data = event.get("competitions", [{}])[0]
                liga_nome = comp_data.get("type", {}).get("name") or "ALL"
                comps = comp_data.get("competitors", [])
                if len(comps) < 2: continue
                time_casa = comps[0].get("team", {}).get("displayName", "Casa")
                time_fora = comps[1].get("team", {}).get("displayName", "Fora")
                print(f"AO VIVO: {liga_nome} - {time_casa} x {time_fora}", flush=True)

            print(f"Total ao vivo agora: {achou_ao_vivo} | Aguardando 15s...", flush=True)
            time.sleep(15)
        except Exception as e:
            print(f"ERRO CRITICO NO LOOP: {e}", flush=True)
            traceback.print_exc()
            time.sleep(20)

threading.Thread(target=verificar_jogos, daemon=True).start()

@app.route("/")
def home():
    return "Bot ON - Debug"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
