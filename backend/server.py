from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, NotFound, ServiceUnavailable, InternalServerError
import os
from dotenv import load_dotenv
import time
import random

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# Configuração de criatividade
generation_config = {
    "temperature": 1.0,
    "max_output_tokens": 4000, 
}

# --- LISTA DE "SALVA-VIDAS" (RODÍZIO DE MODELOS) ---
# O sistema tentará um por um. Misturamos modelos novos (limitados) e velhos (robustos).
MODELOS_PARA_TENTAR = [
    'gemini-2.0-flash-lite',     # O mais rápido e moderno da lista
    'gemini-flash-latest',       # O "apelido" para o 1.5 Flash estável
    'gemini-2.0-flash',          # Versão padrão potente
    'gemini-2.0-flash-001',      # Variação estável
    'gemini-pro-latest'          # Backup do Pro
]

resumo_campanha_anterior = ""
historico_atual = [] 

# --- PROMPTS E ESTRUTURA ---
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

# --- FUNÇÃO ROBUSTA DE GERAÇÃO ---
def gerar_resposta_robusta(prompt_usuario):
    global historico_atual
    
    # Adiciona msg do usuário
    historico_atual.append({"role": "user", "parts": [prompt_usuario]})

    # Tenta cada modelo da lista
    for nome_modelo in MODELOS_PARA_TENTAR:
        try:
            print(f"--> Tentando conectar com: {nome_modelo}...")
            model = genai.GenerativeModel(nome_modelo, generation_config=generation_config)
            
            response = model.generate_content(historico_atual)
            
            texto_resposta = response.text
            print(f"--> SUCESSO com {nome_modelo}!")
            
            historico_atual.append({"role": "model", "parts": [texto_resposta]})
            return texto_resposta, 200
            
        except ResourceExhausted:
            print(f"⚠️ Cota excedida no {nome_modelo}. Tentando próximo em 1s...")
            time.sleep(1) # Pequena pausa para não floodar
            continue
        except NotFound:
            print(f"❌ Modelo {nome_modelo} não existe na sua conta. Pulando...")
            continue
        except Exception as e:
            print(f"❌ Erro genérico no {nome_modelo}: {e}")
            time.sleep(1)
            continue

    # Se chegou aqui, TODOS falharam
    print("CRÍTICO: Todos os modelos falharam.")
    return "⚠️ **O Mestre perdeu a conexão espiritual.**<br>Todos os modelos estão ocupados ou sem cota no momento.<br>Por favor, aguarde 2 minutos e tente novamente.", 429

# --- ROTAS ---
@app.route('/api/chat', methods=['POST'])
def chat():
    dados = request.json
    texto, status = gerar_resposta_robusta(dados.get('message'))
    return jsonify({"reply": texto}), status

@app.route('/api/reset', methods=['POST'])
def reset_game():
    global historico_atual, resumo_campanha_anterior
    resumo_campanha_anterior = ""
    historico_atual = [] # Limpa histórico
    
    tema = request.json.get('theme', 'medieval')
    prompt_completo = TEMAS.get(tema, TEMAS['medieval'])
    
    comando_inicial = f"""
    COMANDO SISTEMA: {prompt_completo}
    OBJETIVO IMEDIATO:
    1. Ignore introduções. O sistema já fez isso.
    2. Inicie DIRETAMENTE a narração do ATO 1.
    3. Descreva o cenário inicial e o perigo.
    4. Pergunte a ação do jogador.
    """
    
    texto, status = gerar_resposta_robusta(comando_inicial)
    return jsonify({"reply": texto}), status

@app.route('/api/continue', methods=['POST'])
def continue_game():
    global historico_atual, resumo_campanha_anterior
    
    resumo, status = gerar_resposta_robusta("SISTEMA: Resuma o personagem veterano (Nome, Itens, Feitos).")
    if status != 200: return jsonify({"reply": resumo}), status
    
    resumo_campanha_anterior = resumo
    historico_atual = [] 

    prompt_novo = f"{PROMPT_MESTRE_BASE} \n NOVA TEMPORADA. VETERANO: {resumo_campanha_anterior} \n AÇÃO: Inicie o ATO 1."
    
    texto, status = gerar_resposta_robusta(prompt_novo)
    return jsonify({"reply": texto}), status

if __name__ == '__main__':
    app.run(debug=True, port=5000)