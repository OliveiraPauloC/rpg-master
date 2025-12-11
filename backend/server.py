from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, NotFound, ServiceUnavailable, InternalServerError
import os
from dotenv import load_dotenv
import time
import random

load_dotenv()

# --- CARREGA AS 3 CHAVES ---
# Se não encontrar a 2 ou 3, usa a principal repetida para não quebrar
CHAVES = [
    os.getenv("GEMINI_API_KEY"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3")
]
# Remove chaves vazias (caso você não tenha colocado as 3 ainda)
CHAVES = [k for k in CHAVES if k]

# Configuração de criatividade
generation_config = {
    "temperature": 1.0,
    "max_output_tokens": 4000, 
}

# --- LISTA DE MODELOS OTIMIZADA ---
# Priorizamos o 1.5 Flash (Estável) pois tem maior cota que o 2.0 (Preview)
MODELOS_PARA_TENTAR = [
    'gemini-1.5-flash',          # O mais robusto para produção
    'gemini-1.5-flash-latest',   # Alternativa
    'gemini-2.0-flash-lite',     # Rápido, mas cota menor
    'gemini-pro',                # Antigo mas confiável
]

historico_por_ip = {} # Memória simples (O ideal seria banco de dados)

ESTRUTURA_NARRATIVA = """
DIRETRIZES (4 ATOS):
ATO 1: A APRESENTAÇÃO.
ATO 2: A ESCALADA.
ATO 3: O CLÍMAX.
ATO 4: O DESFECHO.
Escreva [FIM] apenas no final absoluto.
"""

PROMPT_MESTRE_BASE = f"""
{ESTRUTURA_NARRATIVA}
PERSONALIDADE: Mestre de RPG Narrativo, Sombrio e Imersivo.
REGRAS TÉCNICAS:
1. JAMAIS role dados pelo jogador.
2. Use Markdown Rico (Negrito, Títulos).
3. Seja sensorial (cheiros, sons).
4. Respostas diretas e impactantes.
"""

TEMAS = {
    "medieval": f"{PROMPT_MESTRE_BASE} CENÁRIO: Dark Fantasy. PROTAGONISTA: Guerreiro Humano.",
    "cyberpunk": f"{PROMPT_MESTRE_BASE} CENÁRIO: Cyberpunk 2099. PROTAGONISTA: Mercenário.",
    "terror": f"{PROMPT_MESTRE_BASE} CENÁRIO: Terror Lovecraft. PROTAGONISTA: Investigador.",
    "espacial": f"{PROMPT_MESTRE_BASE} CENÁRIO: Sci-Fi Horror. PROTAGONISTA: Engenheiro."
}

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

# --- FUNÇÃO DE ROTAÇÃO DE CHAVES E MODELOS ---
def gerar_resposta_blindada(prompt_usuario, historico):
    # Adiciona msg do usuário
    historico.append({"role": "user", "parts": [prompt_usuario]})

    # Tenta cada modelo da lista
    for nome_modelo in MODELOS_PARA_TENTAR:
        try:
            # --- ROTAÇÃO DE CHAVES AQUI ---
            chave_escolhida = random.choice(CHAVES)
            genai.configure(api_key=chave_escolhida)
            # ------------------------------
            
            print(f"--> Tentando {nome_modelo} com chave final {chave_escolhida[-4:]}...")
            model = genai.GenerativeModel(nome_modelo, generation_config=generation_config)
            
            response = model.generate_content(historico)
            texto_resposta = response.text
            
            historico.append({"role": "model", "parts": [texto_resposta]})
            return texto_resposta, 200
            
        except ResourceExhausted:
            print(f"⚠️ Cota cheia na chave {chave_escolhida[-4:]} / modelo {nome_modelo}. Trocando...")
            time.sleep(0.5) 
            continue # Tenta o próximo modelo/chave no loop
        except Exception as e:
            print(f"❌ Erro: {e}")
            time.sleep(0.5)
            continue

    return "⚠️ **O Mestre está meditando. **Muitos aventureiros ao mesmo tempo. Tente novamente em 10 segundos.", 429

# --- ROTAS ---
@app.route('/api/chat', methods=['POST'])
def chat():
    user_ip = request.remote_addr # Identifica usuário pelo IP (básico)
    if user_ip not in historico_por_ip: historico_por_ip[user_ip] = []
    
    dados = request.json
    texto, status = gerar_resposta_blindada(dados.get('message'), historico_por_ip[user_ip])
    return jsonify({"reply": texto}), status

@app.route('/api/reset', methods=['POST'])
def reset_game():
    user_ip = request.remote_addr
    historico_por_ip[user_ip] = [] # Limpa histórico DO USUÁRIO
    
    tema = request.json.get('theme', 'medieval')
    prompt_completo = TEMAS.get(tema, TEMAS['medieval'])
    
    comando_inicial = f"COMANDO DE SISTEMA: {prompt_completo}. AÇÃO: Inicie o jogo imediatamente."
    
    texto, status = gerar_resposta_blindada(comando_inicial, historico_por_ip[user_ip])
    return jsonify({"reply": texto}), status

@app.route('/api/continue', methods=['POST'])
def continue_game():
    user_ip = request.remote_addr
    hist = historico_por_ip.get(user_ip, [])
    
    resumo, status = gerar_resposta_blindada("SISTEMA: Resuma o personagem para a próxima temporada.", hist)
    if status != 200: return jsonify({"reply": resumo}), status
    
    historico_por_ip[user_ip] = [] # Limpa velho
    novo_hist = historico_por_ip[user_ip]

    prompt_novo = f"{PROMPT_MESTRE_BASE} \n NOVA TEMPORADA. VETERANO: {resumo} \n AÇÃO: Inicie o ATO 1."
    texto, status = gerar_resposta_blindada(prompt_novo, novo_hist)
    return jsonify({"reply": texto}), status

if __name__ == '__main__':
    app.run(debug=True, port=5000)