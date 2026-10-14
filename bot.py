import requests, time, os, traceback
from flask import Flask
import threading

BOT_TOKEN = os.getenv("BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
TELEGRAM_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

app = Flask(__name__)
jogos_avisados = set()

def enviar_telegram(time_casa, time_fora, placar, minuto, time_cartao, tipo, liga_nome):
    tag = f"[{liga_nome}]"
    icone = "🔴 RED CARD!" if tipo=="VERMELHO" else "🟨 AMARELO!"
    msg_topo = f"{time_cartao} ficou com 10!" if tipo=="VERMELHO" else f"Cartão para {time_cartao}"

    try:
        gc, gf = map(int, placar.lower().replace('x','-').split('-'))
        total = gc+gf
    except: total=0
    time_com_11 = time_fora if time_casa==time_cartao else time_casa

    if total==0: ops=[f"- {time_com_11} vence (1 a mais)","- Over 0.5 Gols","- Over 1.5 Gols"]
    elif total==1: ops=[f"- Over 1.5 Gols",f"- Próximo gol: {time_com_11}",f"- {time_com_11} vence"]
    elif total==2: ops=[f"- Over 2.5 Gols","- Ambos marcam? SIM",f"- Próximo gol: {time_com_11}"]
    else: ops=[f"- Over {total+0.5} Gols",f"- Próximo gol: {time_com_11}","- Over escanteios"]

    texto = f"""{icone} {tag} {time_casa} {placar} {time_fora} ({minuto}')
{msg_topo}

💰 OPORTUNIDADES AO VIVO:
{chr(10).join(ops)}"""
    try:
        requests.post(TELEGRAM_URL, data={"chat_id": CHAT_ID, "text": texto}, timeout=10)
        print(f"ENVIADO: {texto}", flush=True)
    except Exception as e: print(f"Erro TG: {e}", flush=True)

def pega_cartoes_detalhado(event_id):
    # Busca o SUMMARY que tem cartão ao vivo
    try:
        url = f"https://site.api.espn.com/apis/site/v2/sports/soccer/all/summary?event={event_id}"
        data = requests.get(url, timeout=10, headers={"User-Agent":"Mozilla/5.0"}).json()
        comps = data.get("header",{}).get("competitions",[{}])[0].get("competitors",[])
        if not comps:
            comps = data.get("boxscore",{}).get("competitors",[])
        res = {}
        for c in comps:
            team = c.get("team",{}).get("displayName","")
            # pega de statistics ou direto
            y = int(c.get("yellowCards",0) or 0)
            r = int(c.get("redCards",0) or 0)
            has_red = c.get("hasRedCard", False)
            for st in c.get("statistics",[]):
                if "yellow" in st.get("name","").lower() or st.get("abbreviation")=="YC":
                    y = int(str(st.get("displayValue","0")).split("-")[0])
                if "red" in st.get("name","").lower() or st.get("abbreviation")=="RC":
                    r = int(str(st.get("displayValue","0")).split("-")[0])
                    if r>0: has_red=True
            res[team] = (y,r,has_red)
        return res
    except Exception as e:
        print(f"Erro summary {event_id}: {e}", flush=True)
        return {}

def verificar_jogos():
    print(">>> BOT COM SUMMARY - CARTÃO AO VIVO <<<", flush=True)
    url = "https://site.api.espn.com/apis/site/v2/sports/soccer/all/scoreboard"
    headers = {"User-Agent":"Mozilla/5.0"}
    while True:
        try:
            data = requests.get(url, timeout=20, headers=headers).json()
            events = data.get("events",[])
            print(f"Encontrados {len(events)} eventos", flush=True)
            ao_vivo=0
            for event in events:
                if event.get("status",{}).get("type",{}).get("state")!="in": continue
                ao_vivo+=1
                comp_data = event.get("competitions",[{}])[0]
                liga_nome = comp_data.get("type",{}).get("abbreviation") or "ALL"
                event_id = event.get('id')
                comps = comp_data.get("competitors",[])
                if len(comps)<2: continue
                time_casa = comps[0].get("team",{}).get("displayName","Casa")
                time_fora = comps[1].get("team",{}).get("displayName","Fora")
                placar = f"{comps[0].get('score','0')}x{comps[1].get('score','0')}"
                minuto = event.get("status",{}).get("displayClock","")

                # AQUI PEGA CARTÃO REAL
                detalhes = pega_cartoes_detalhado(event_id)
                # Se summary não trouxe, usa do scoreboard
                if not detalhes:
                    detalhes = {c.get("team",{}).get("displayName",""): (0,0,False) for c in comps}

                total_ama=0
                total_verm=0
                for y,r,_ in detalhes.values():
                    total_ama+=y
                    total_verm+=r

                print(f"AO VIVO: {liga_nome} - {time_casa} {placar} {time_fora} ({minuto}) | AMA: {total_ama} VERM: {total_verm}", flush=True)
                for team,(y,r,hr) in detalhes.items():
                    print(f" -> {team}: amarelo={y} vermelho={r} has_red={hr}", flush=True)

                for team,(y,r,hr) in detalhes.items():
                    tipo=None
                    if hr or r>0: tipo="VERMELHO"
                    elif y>0: tipo="AMARELO"
                    if tipo:
                        key=f"{liga_nome}_{event_id}_{team}_{tipo}_{y}_{r}"
                        if key not in jogos_avisados:
                            enviar_telegram(time_casa, time_fora, placar, minuto, team, tipo, liga_nome)
                            jogos_avisados.add(key)
                            if tipo=="AMARELO":
                                # evita spam de mesmo jogo
                                for i in range(y+1, y+5):
                                    jogos_avisados.add(f"{liga_nome}_{event_id}_{team}_AMARELO_{i}_0")

            print(f"Total: {ao_vivo} jogos ao vivo/intervalo | 15s", flush=True)
            time.sleep(15)
        except Exception as e:
            print(f"ERRO: {e}", flush=True)
            traceback.print_exc()
            time.sleep(20)

threading.Thread(target=verificar_jogos, daemon=True).start()

@app.route("/")
def home(): return "Bot ON - Summary ao vivo + apostas"

if __name__=="__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
