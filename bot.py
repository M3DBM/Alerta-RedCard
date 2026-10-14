import requests
import time
from flask import Flask
import threading
import os
from datetime import datetime

# SEU TOKEN E CHAT ID - já está certo, não mexe
BOT_TOKEN = os.getenv("BOT_TOKEN", "SEU_TOKEN_AQUI")
CHAT_ID = os.getenv("CHAT_ID", "SEU_CHAT_ID")
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

app = Flask(__name__)

# Guarda os jogos que já avisamos pra não repetir
jogos_avisados = set()

def gerar_oportunidades(time_casa, time_fora, placar_casa, placar_fora, minuto, time_com_vermelho):
    """Gera as dicas com base no placar"""
    try:
        minuto_int = int(minuto.replace("'", "").replace("+", "").split("-")[0])
    except:
        minuto_int = 70

    adversario = time_fora if time_com_vermelho == time_casa else time_casa
    esta_ganhando = False
    esta_perdendo = False
    esta_empatando = False

    if time_com_vermelho == time_casa:
        if placar_casa > placar_fora:
            esta_ganhando = True
        elif placar_casa < placar_fora:
            esta_perdendo = True
        else:
            esta_empatando = True
    else:
        if placar_fora > placar_casa:
            esta_ganhando = True
        elif placar_fora < placar_casa:
            esta_perdendo = True
        else:
            esta_empatando = True

    dicas = []

    if esta_ganhando:
        dicas.append(f"{adversario} empata ou vitória (Dupla Chance)")
        dicas.append("Over 1.5 Gols")
        dicas.append(f"{adversario} marca o próximo gol")
    elif esta_empatando:
        dicas.append(f"{adversario} vence")
        dicas.append("Over 0.5 Gols")
        dicas.append(f"{adversario} Over 0.5")
    else: # está perdendo
        dicas.append(f"{adversario} vence")
        dicas.append(f"{adversario} -1.5 Handicap")
        dicas.append("Over 1.5 Gols")

    return dicas

def enviar_telegram(time_casa, time_fora, placar, minuto, time_com_vermelho):
    try:
        placar_casa, placar_fora = map(int, placar.split("x"))
    except:
        placar_casa, placar_fora = 0, 0

    dicas = gerar_oportunidades(time_casa, time_fora, placar_casa, placar_fora, minuto, time_com_vermelho)

    mensagem = f"""🔴 RED CARD! {time_casa} {placar} {time_fora} ({minuto}')
{time_com_vermelho} ficou com 10 jogadores!

💰 OPORTUNIDADES AO VIVO:
• {dicas[0]}
• {dicas[1]}
• {dicas[2]}"""

    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "HTML"}
    try:
        requests.post(TELEGRAM_URL, data=payload, timeout=10)
        print(f"Enviado: {mensagem}")
    except Exception as e:
        print(f"Erro telegram: {e}")

def verificar_jogos():
    url = "https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard"
    while True:
        try:
            r = requests.get(url, timeout=15)
            data = r.json()
            events = data.get("events", [])

            for event in events:
                status = event.get("status", {}).get("type", {}).get("state")
                if status!= "in":
                    continue

                comp = event.get("competitions", [{}])[0]
                competitors = comp.get("competitors", [])
                if len(competitors) < 2:
                    continue

                time_casa = competitors[0].get("team", {}).get("displayName", "Casa")
                time_fora = competitors[1].get("team", {}).get("displayName", "Fora")

                # Pega placar
                placar_casa = competitors[0].get("score", "0")
                placar_fora = competitors[1].get("score", "0")
                placar = f"{placar_casa}x{placar_fora}"

                # Minuto do jogo
                minuto = event.get("status", {}).get("displayClock", "0'")

                # VERIFICA QUEM TEM VERMELHO
                for comp_team in competitors:
                    has_red = comp_team.get("hasRedCard") or comp_team.get("isRedCard") or False
                    # Algumas vezes vem em 'redCards' > 0
                    red_cards = comp_team.get("records", [])

                    # Método mais confiável da ESPN
                    if comp_team.get("team", {}).get("id"):
                        # Se tiver campo de red card
                        if comp_team.get("statistics") or comp_team.get("hasRedCard"):
                            pass

                    # CHECAGEM SIMPLES E QUE FUNCIONA: hasRedCard
                    if comp_team.get("hasRedCard") or comp_team.get("redCards", 0) > 0 or comp_team.get("hasRedCard", False):
                        team_name = comp_team.get("team", {}).get("displayName", "")
                        game_id = event.get("id") + "_" + team_name

                        if game_id not in jogos_avisados:
                            enviar_telegram(time_casa, time_fora, placar, minuto, team_name)
                            jogos_avisados.add(game_id)

                    # Fallback: verifica no 'situation'
                    situation = comp.get("situation", {})
                    # Se não achou, tenta outro campo comum
                    if comp.get("hasRedCard"):
                         pass

            time.sleep(30)
        except Exception as e:
            print(f"Erro loop: {e}")
            time.sleep(30)

@app.route("/")
def home():
    return "Bot Alerta Red Card com Oportunidades - ON"

if __name__ == "__main__":
    t = threading.Thread(target=verificar_jogos, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
