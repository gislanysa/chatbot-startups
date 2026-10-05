import json
import os
import threading
import unicodedata
import urllib.error
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# -- Configurações --
PASTA = os.path.dirname(os.path.abspath(__file__))
ARQUIVO_JSON = os.path.join(PASTA, "base_conhecimento.json")
API_KEY = os.environ.get("GEMINI_API_KEY", "")
MODELO = "gemini-2.5-flash"
URL_API = "https://generativelanguage.googleapis.com/v1beta/models/" + MODELO + ":generateContent"
PORTA = 5055

# -- Base de conhecimento (JSON) --
def carregar_base():
    with open(ARQUIVO_JSON, encoding="utf-8") as f:
        return json.load(f)

BASE = carregar_base()

def remover_acentos(texto):
    return "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")

def base_como_texto():
    linhas = ["Tema: " + BASE["tema"], ""]
    for item in BASE["faq"]:
        linhas.append("P: " + item["pergunta"])
        linhas.append("R: " + item["resposta"])
        linhas.append("")
    return "\n".join(linhas)


# -- Modo offline (palavras-chave) --
def resposta_offline(pergunta):
    palavras = remover_acentos(pergunta.lower()).split()
    melhor, melhor_pontos = None, 0
    for item in BASE["faq"]:
        pontos = 0
        for p in palavras:
            for k in item["palavras_chave"]:
                if k in p:
                    pontos += 1
        if pontos > melhor_pontos:
            melhor, melhor_pontos = item, pontos
    if melhor:
        return melhor["resposta"]
    return "Não encontrei essa informação. Tente perguntar sobre cadastro, CNPJ, busca de startups ou matchmaking."

# -- LLM (Gemini) --
def resposta_llm(pergunta):
    instrucoes = (
        "Você é o assistente virtual de uma plataforma de matchmaking entre startups e empresas. "
        "Responda em português, de forma curta e simpática, usando APENAS as informações da base abaixo. "
        "Se a resposta não estiver na base, diga que não tem essa informação e sugira os temas disponíveis. "
        "Não invente dados.\n\n=== BASE DE CONHECIMENTO ===\n" + base_como_texto()
    )
    corpo = {
        "system_instruction": {"parts": [{"text": instrucoes}]},
        "contents": [{"role": "user", "parts": [{"text": pergunta}]}],
    }
    req = urllib.request.Request(
        URL_API,
        data=json.dumps(corpo).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": API_KEY},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        dados = json.loads(r.read().decode("utf-8"))
    return dados["candidates"][0]["content"]["parts"][0]["text"].strip()

def responder(pergunta):
    if not API_KEY:
        return resposta_offline(pergunta) + "\n(modo offline: chave não definida)"
    try:
        return resposta_llm(pergunta)
    except urllib.error.HTTPError as e:
        return resposta_offline(pergunta) + "\n(modo offline: erro HTTP " + str(e.code) + ")"
    except Exception as e:
        return resposta_offline(pergunta) + "\n(modo offline: " + type(e).__name__ + ")"

# -- Interface (página web) --
PAGINA = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Chatbot - Plataforma de Startups</title>
<style>
  * { box-sizing: border-box; }
  body { margin: 0; font-family: -apple-system, "Segoe UI", Roboto, sans-serif; background: #eef1f8;
         height: 100vh; display: flex; justify-content: center; align-items: center; }
  .app { width: 100%; max-width: 560px; height: 92vh; background: #fff; border-radius: 16px;
         box-shadow: 0 8px 30px rgba(0,0,0,.12); display: flex; flex-direction: column; overflow: hidden; }
  header { background: #1a56db; color: #fff; padding: 16px 20px; }
  header h1 { margin: 0; font-size: 18px; }
  header p { margin: 4px 0 0; font-size: 13px; opacity: .85; }
  #chat { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 10px; background: #f8f9fc; }
  .msg { max-width: 82%; padding: 10px 14px; border-radius: 14px; line-height: 1.4; font-size: 15px; white-space: pre-wrap; }
  .bot { background: #fff; border: 1px solid #e3e7f1; align-self: flex-start; }
  .user { background: #1a56db; color: #fff; align-self: flex-end; }
  .sugestoes { display: flex; flex-wrap: wrap; gap: 8px; padding: 0 16px 10px; background: #f8f9fc; }
  .sugestoes button { border: 1px solid #1a56db; background: #fff; color: #1a56db; border-radius: 16px;
                      padding: 6px 12px; font-size: 13px; cursor: pointer; }
  form { display: flex; gap: 8px; padding: 12px; border-top: 1px solid #e3e7f1; }
  input { flex: 1; padding: 12px 14px; border: 1px solid #cfd6e6; border-radius: 22px; font-size: 15px; outline: none; }
  .enviar { background: #1a56db; color: #fff; border: 0; border-radius: 22px; padding: 0 20px; font-size: 15px; cursor: pointer; }
  .enviar:disabled { opacity: .5; }
</style>
</head>
<body>
<div class="app">
  <header>
    <h1>Assistente da Plataforma de Startups</h1>
    <p>Tire dúvidas sobre cadastro, CNPJ, busca e matchmaking</p>
  </header>
  <div id="chat"></div>
  <div class="sugestoes">
    <button type="button">Preciso de CNPJ?</button>
    <button type="button">O cadastro é pago?</button>
    <button type="button">Como funciona o matchmaking?</button>
  </div>
  <form id="form">
    <input id="entrada" placeholder="Digite sua pergunta..." autocomplete="off">
    <button class="enviar" id="botao" type="submit">Enviar</button>
  </form>
</div>
<script>
  var chat = document.getElementById("chat");
  var entrada = document.getElementById("entrada");
  var botao = document.getElementById("botao");

  function adicionar(texto, classe) {
    var div = document.createElement("div");
    div.className = "msg " + classe;
    div.textContent = texto;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
    return div;
  }

  function perguntar(texto) {
    adicionar(texto, "user");
    var aguarde = adicionar("Digitando...", "bot");
    botao.disabled = true;
    fetch("/perguntar", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ pergunta: texto })
    })
    .then(function (r) { return r.json(); })
    .then(function (d) { aguarde.textContent = d.resposta; })
    .catch(function () { aguarde.textContent = "Não consegui falar com o servidor."; })
    .then(function () { botao.disabled = false; entrada.focus(); });
  }

  document.getElementById("form").addEventListener("submit", function (e) {
    e.preventDefault();
    var texto = entrada.value.trim();
    if (!texto) return;
    entrada.value = "";
    perguntar(texto);
  });

  var botoes = document.querySelectorAll(".sugestoes button");
  for (var i = 0; i < botoes.length; i++) {
    botoes[i].addEventListener("click", function () { perguntar(this.textContent); });
  }

  adicionar("Olá! Como posso ajudar você hoje?", "bot");
</script>
</body>
</html>
"""

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        dados = PAGINA.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_POST(self):
        tamanho = int(self.headers.get("Content-Length", 0))
        corpo = json.loads(self.rfile.read(tamanho) or b"{}")
        resposta = responder(corpo.get("pergunta", ""))
        dados = json.dumps({"resposta": resposta}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def log_message(self, *args):
        pass

if __name__ == "__main__":
    servidor = ThreadingHTTPServer(("127.0.0.1", PORTA), Handler)
    url = "http://localhost:" + str(PORTA)
    print("Chatbot rodando em " + url + "  (Ctrl+C para encerrar)")
    if not API_KEY:
        print("Aviso: GEMINI_API_KEY não definida. Rodando em modo offline.")
    threading.Timer(1, lambda: webbrowser.open(url)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nEncerrado.")