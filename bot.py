import requests, time, os
from flask import Flask
import threading

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

app = Flask(__name__)
jogos_avisados = set()

def enviar_telegram(time_casa, time_fora, placar, minuto, time_cartao, tipo, liga_nome):
    # Tag da liga pra diferenciar [CHAMPIONS] vs [U19]
    tag = f"[{liga_nome}]" if liga_nome else ""

    if tipo == "VERMELHO":
        icone = "🔴 RED CARD!"
        msg = f"{time_cartao} ficou com 10 jogadores!"
    else:
        icone = "🟨 AMARELO!"
        msg = f"Teste OK! Sistema funcionando! Cartão para {time_cartao}"

    texto = f"""{icone} {tag} {time_casa} {placar} {time_fora} ({minuto}')
{msg}

💰 OPORTUNIDADES AO VIVO:
- Time adversário empata ou vence
- Over 1.5 Gols
- Próximo gol adversário"""

    try:
        requests.post(TELEGRAM_URL, data={"chat_id": CHAT_ID, "text": texto}, timeout=10)
        print(f"Enviado: {texto}")
    except Exception as e:
        print(f"Erro telegram: {e}")

def verificar_jogos():
    url = "https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard"

    while True:
        try:
            r = requests.get(url, timeout=15).json()
            events = r.get("events", [])

            for event in events:
                # Só jogos ao vivo
                if event.get("status", {}).get("type", {}).get("state")!= "in":
                    continue

                # === AQUI QUE SEPARA JOGOS COM NOME IGUAL ===
                try:
                    comp = event.get("competitions", [{}])[0]
                    liga_nome = comp.get("notes", [{}])[0].get("league", {}).get("name") or \
                                comp.get("type", {}).get("abbreviation") or \
                                r.get("leagues", [{}])[0].get("name") or "ALL"
                    # ID único = LIGA + ID do evento
                    event_id = f"{liga_nome}_{event.get('id')}"
                except:
                    liga_nome = "ALL"
                    event_id = event.get("id")

                comps = event.get("competitions", [{}])[0].get("competitors", [])
                if len(comps) < 2:
                    continue

                time_casa = comps[0].get("team", {}).get("displayName", "Casa")
                time_fora = comps[1].get("team", {}).get("displayName", "Fora")
                placar = f"{comps[0].get('score','0')}x{comps[1].get('score','0')}"
                minuto = event.get("status", {}).get("displayClock", "0'")

                for ct in comps:
                    team_name = ct.get("team", {}).get("displayName", "")
                    yellow = int(ct.get("yellowCards", 0) or 0)
                    red = int(ct.get("redCards", 0) or 0)
                    has_red = ct.get("hasRedCard", False)

                    tipo = None
                    if has_red or red > 0:
                        tipo = "VERMELHO"
                    elif yellow > 0:
                        tipo = "AMARELO" # MODO TESTE - depois tiramos

                    if tipo:
                        # ID único pra não repetir o mesmo cartão
                        game_key = f"{event_id}_{team_name}_{tipo}_{yellow}_{red}"

                        if game_key not in jogos_avisados:
                            print(f"Cartão: {liga_nome} - {team_name} {tipo}")
                            enviar_telegram(time_casa, time_fora, placar, minuto, team_name, tipo, liga_nome)
                            jogos_avisados.add(game_key)

                            # No teste, bloqueia flood de amarelo do mesmo time
                            if tipo == "AMARELO":
                                for i in range(1, 10):
                                    jogos_avisados.add(f"{event_id}_{team_name}_AMARELO_{i}_0")

            print("Verificado TODAS as ligas... 15s")
            time.sleep(15)

        except Exception as e:
            print(f"Erro geral: {e}")
            time.sleep(20)

@app.route("/")
def home():
    return "Bot ON - TODAS as ligas + separa jogos iguais (Champions vs U19)"

if __name__ == "__main__":
    threading.Thread(target=verificar_jogos, daemon=True).start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
if __name__ == "__main__":
    t = threading.Thread(target=verificar_jogos, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
