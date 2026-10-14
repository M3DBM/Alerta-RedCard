import requests
import time
from flask import Flask
import threading
import os

BOT_TOKEN = os.getenv("BOT_TOKEN", "SEU_TOKEN_AQUI")
CHAT_ID = os.getenv("CHAT_ID", "SEU_CHAT_ID")
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

app = Flask(__name__)
jogos_avisados = set()

def gerar_oportunidades(time_casa, time_fora, placar_casa, placar_fora, time_com_vermelho):
    adversario = time_fora if time_com_vermelho == time_casa else time_casa
    return [
        f"{adversario} empata ou vitória",
        "Over 1.5 Gols",
        f"{adversario} marca o próximo"
    ]

def enviar_telegram(time_casa, time_fora, placar, minuto, time_com_cartao, tipo_cartao):
    if tipo_cartao == "VERMELHO":
        icone = "🔴 RED CARD!"
        msg_complemento = f"{time_com_cartao} ficou com 10 jogadores!"
    else:
        icone = "🟨 TESTE - AMARELO!"
        msg_complemento = f"Teste OK! Sistema funcionando! Cartão para {time_com_cartao}"

    try:
        pc, pf = map(int, placar.split("x"))
    except:
        pc, pf = 0,0

    dicas = gerar_oportunidades(time_casa, time_fora, pc, pf, time_com_cartao)

    mensagem = f"""{icone} {time_casa} {placar} {time_fora} ({minuto}')
{msg_complemento}

💰 OPORTUNIDADES AO VIVO:
• {dicas[0]}
• {dicas[1]}
• {dicas[2]}"""

    payload = {"chat_id": CHAT_ID, "text": mensagem}
    try:
        requests.post(TELEGRAM_URL, data=payload, timeout=10)
        print(f"ENVIADO: {mensagem}")
    except Exception as e:
        print(f"Erro: {e}")

def verificar_jogos():
    url = "https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard"
    while True:
        try:
            r = requests.get(url, timeout=15)
            data = r.json()
            events = data.get("events", [])

            for event in events:
                if event.get("status", {}).get("type", {}).get("state")!= "in":
                    continue

                comp = event.get("competitions", [{}])[0]
                competitors = comp.get("competitors", [])
                if len(competitors) < 2: continue

                time_casa = competitors[0].get("team", {}).get("displayName", "Casa")
                time_fora = competitors[1].get("team", {}).get("displayName", "Fora")
                placar = f"{competitors[0].get('score','0')}x{competitors[1].get('score','0')}"
                minuto = event.get("status", {}).get("displayClock", "0'")

                for ct in competitors:
                    team_name = ct.get("team", {}).get("displayName", "")

                    # PEGA OS DADOS DE CARTÃO
                    has_red = ct.get("hasRedCard", False)
                    red_cards = int(ct.get("redCards", 0) or 0)
                    yellow_cards = int(ct.get("yellowCards", 0) or ct.get("yellowCard", 0) or 0)

                    # ESPN as vezes manda dentro de statistics
                    # vamos tentar pegar de todo jeito
                    if yellow_cards == 0:
                        # tenta outro campo
                        stats = ct.get("statistics", [])
                        for s in stats:
                            if "yellow" in s.get("name","").lower():
                                yellow_cards = int(s.get("value",0))

                    tipo = None
                    if has_red or red_cards > 0:
                        tipo = "VERMELHO"
                    elif yellow_cards > 0:
                        tipo = "AMARELO"

                    if tipo:
                        # ID único pra não repetir o mesmo cartão
                        game_id = f"{event.get('id')}_{team_name}_{tipo}_{yellow_cards}_{red_cards}"
                        if game_id not in jogos_avisados:
                            enviar_telegram(time_casa, time_fora, placar, minuto, team_name, tipo)
                            jogos_avisados.add(game_id)
                            # No modo teste, avisa só o primeiro amarelo de cada time
                            # pra não floodar
                            if tipo == "AMARELO":
                                # bloqueia mais amarelos desse time nesse jogo
                                for i in range(1,10):
                                    jogos_avisados.add(f"{event.get('id')}_{team_name}_AMARELO_{i}_0")

            print("Verificado... aguardando 20s")
            time.sleep(20)
        except Exception as e:
            print(f"Erro loop: {e}")
            time.sleep(20)

@app.route("/")
def home():
    return "Bot MODO TESTE AMARELO - ON - Checando a cada 20s"

if __name__ == "__main__":
    t = threading.Thread(target=verificar_jogos, daemon=True)
    t.start()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
