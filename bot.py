import requests, time, os, traceback
from flask import Flask
import threading

BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

app = Flask(__name__)
jogos_avisados = set()

def enviar_telegram(time_casa, time_fora, placar, minuto, time_cartao, tipo, liga_nome):
    tag = f"[{liga_nome}]" if liga_nome else ""
    if tipo == "VERMELHO":
        icone = "🔴 RED CARD!"
        msg_topo = f"{time_cartao} ficou com 10 jogadores!"
    else:
        icone = "🟨 AMARELO!"
        msg_topo = f"Cartão para {time_cartao}"

    try:
        gols_casa, gols_fora = map(int, placar.lower().replace('x','-').split('-'))
        total_gols = gols_casa + gols_fora
    except:
        total_gols = 0

    time_com_10 = time_cartao
    time_com_11 = time_fora if time_casa == time_com_10 else time_casa

    if total_gols == 0:
        oportunidades = [f"- {time_com_11} vence (tem 1 a mais)", "- Over 0.5 Gols", "- Over 1.5 Gols"]
    elif total_gols == 1:
        oportunidades = [f"- Over 1.5 Gols", f"- Próximo gol: {time_com_11}", f"- {time_com_11} vence"]
    elif total_gols == 2:
        oportunidades = [f"- Over 2.5 Gols", f"- Ambos marcam? SIM", f"- Próximo gol: {time_com_11}"]
    else:
        oportunidades = [f"- Over {total_gols + 0.5} Gols", f"- Próximo gol: {time_com_11}", f"- Over escanteios"]

    lista_oportunidades = "\n".join(oportunidades)
    texto = f"""{icone} {tag} {time_casa} {placar} {time_fora} ({minuto}')
{msg_topo}

💰 OPORTUNIDADES AO VIVO:
{lista_oportunidades}"""

    try:
        requests.post(TELEGRAM_URL, data={"chat_id": CHAT_ID, "text": texto}, timeout=10)
        print(f"ENVIADO: {texto}", flush=True)
    except Exception as e:
        print(f"Erro telegram: {e}", flush=True)

def pega_cartoes(competitor):
    amarelo = 0
    vermelho = 0
    has_red = False
    # Método novo da ESPN
    for stat in competitor.get("statistics", []):
        name = stat.get("name","").lower()
        abbr = stat.get("abbreviation","")
        val = stat.get("displayValue","0")
        try: v = int(str(val).split("-")[0])
        except: v = 0
        if "yellow" in name or abbr == "YC":
            amarelo = v
        if "red" in name or abbr == "RC":
            vermelho = v
            if v > 0: has_red = True
    # Método antigo (se vier direto)
    if amarelo==0: amarelo = int(competitor.get("yellowCards",0) or 0)
    if vermelho==0: vermelho = int(competitor.get("redCards",0) or 0)
    if competitor.get("hasRedCard"): has_red = True
    return amarelo, vermelho, has_red

def verificar_jogos():
    print(">>> BOT INICIADO - VERIFICANDO JOGOS <<<", flush=True)
    url = "https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard"
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    while True:
        try:
            print("Buscando ESPN...", flush=True)
            data = requests.get(url, timeout=20, headers=headers).json()
            events = data.get("events", [])
            print(f"Encontrados {len(events)} eventos", flush=True)
            ao_vivo = 0
            for event in events:
                state = event.get("status", {}).get("type", {}).get("state")
                if state not in ["in"]: # só ao vivo mesmo
                    continue

                ao_vivo += 1
                comp_data = event.get("competitions", [{}])[0]
                liga_nome = comp_data.get("type", {}).get("name") or comp_data.get("type", {}).get("abbreviation") or "ALL"
                event_id = event.get('id')
                comps = comp_data.get("competitors", [])
                if len(comps) < 2: continue

                time_casa = comps[0].get("team", {}).get("displayName", "Casa")
                time_fora = comps[1].get("team", {}).get("displayName", "Fora")
                placar = f"{comps[0].get('score','0')}x{comps[1].get('score','0')}"
                minuto = event.get("status", {}).get("displayClock", "0'")
                t1_ama, t1_verm, _ = pega_cartoes(comps[0])
                t2_ama, t2_verm, _ = pega_cartoes(comps[1])

                # LOG QUE TU QUERIA COM CARTÃO
                print(f"AO VIVO: {liga_nome} - {time_casa} {placar} {time_fora} ({minuto}) | AMA: {t1_ama+t2_ama} VERM: {t1_verm+t2_verm}", flush=True)
                print(f" -> {time_casa}: amarelo={t1_ama} vermelho={t1_verm} | {time_fora}: amarelo={t2_ama} vermelho={t2_verm}", flush=True)

                for ct in comps:
                    team = ct.get("team", {}).get("displayName", "")
                    yellow, red, has_red = pega_cartoes(ct)

                    tipo = None
                    if has_red or red > 0: tipo = "VERMELHO"
                    elif yellow > 0: tipo = "AMARELO"

                    if tipo:
                        key = f"{liga_nome}_{event_id}_{team}_{tipo}_{yellow}_{red}"
                        if key not in jogos_avisados:
                            enviar_telegram(time_casa, time_fora, placar, minuto, team, tipo, liga_nome)
                            jogos_avisados.add(key)
                            if tipo == "AMARELO":
                                for i in range(1, 10):
                                    jogos_avisados.add(f"{liga_nome}_{event_id}_{team}_AMARELO_{i}_0")

            print(f"Total: {ao_vivo} jogos ao vivo/intervalo | 15s", flush=True)
            time.sleep(15)
        except Exception as e:
            print(f"ERRO: {e}", flush=True)
            traceback.print_exc()
            time.sleep(20)

threading.Thread(target=verificar_jogos, daemon=True).start()

@app.route("/")
def home():
    return "Bot ON - Todas as ligas + id fix + apostas"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
