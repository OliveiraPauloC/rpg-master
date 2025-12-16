from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, InternalServerError
import os
from dotenv import load_dotenv
import time
import random

load_dotenv()

# --- CARREGA AS CHAVES ---
CHAVES = [
    os.getenv("GEMINI_API_KEY"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3")
]
CHAVES = [k for k in CHAVES if k] 

# AUMENTADO PARA 4000 (EVITA CORTES)
generation_config = {
    "temperature": 1.0,
    "max_output_tokens": 4000, 
}

MODELOS_PARA_TENTAR = [
    'gemini-flash-latest',       
    'gemini-2.0-flash-lite',     
    'gemini-2.0-flash',          
    'gemini-pro-latest'          
]

# --- PROMPT MESTRE (VERSÃO NARRATIVA FLUÍDA) ---
ESTRUTURA_NARRATIVA = """
DIRETRIZES DE MESTRE DE RPG (SISTEMA D20):

OBJETIVO: Mestrar uma campanha de 4 ATOS (10-15 turnos cada).
FOCO: Ação, risco e testes de perícia.

REGRAS DE OURO:
1. PEÇA ROLAGENS: Se o jogador tentar algo arriscado, PEÇA UM TESTE (ex: "Faça um teste de Força CD 12").
2. PÓS-DADO (IMPORTANTE): Ao receber um resultado de dado, NÃO diga apenas "Sucesso". Descreva a cena heroica ou o desastre trágico. Dê vida ao resultado!
3. CONTINUIDADE: Após narrar o resultado do dado, a cena DEVE continuar. O inimigo recua? A porta abre? O que acontece depois?
4. FINALIZAÇÃO OBRIGATÓRIA: NUNCA termine uma resposta sem perguntar "O que você faz?" ou dar opções. O jogo não pode parar.

ESTRUTURA (ATOS):
- Use a estrutura de 4 Atos para guiar a dificuldade, mas NÃO escreva "ATO 1" ou "ATO 2" no texto.

FORMATO DA RESPOSTA:
- Use parágrafos descritivos (2 a 3).
- Se o jogador rolar 20 (Crítico), narre algo épico.
- Se rolar 1 (Falha Crítica), narre um desastre divertido.
"""

PROMPT_MESTRE_BASE = f"""
{ESTRUTURA_NARRATIVA}
TÉCNICA:
- Use **Negrito** para inimigos e itens.
- Use *Itálico* para atmosfera.
"""

TEMAS = {
    "medieval": f"{PROMPT_MESTRE_BASE} CENÁRIO: Alta Fantasia Épica (D&D/LOTR). Magia, dragões e heróis.",
    "cyberpunk": f"{PROMPT_MESTRE_BASE} CENÁRIO: Cyberpunk Distópico. Neon, hackers e corporações.",
    "terror": f"{PROMPT_MESTRE_BASE} CENÁRIO: Terror Lovecraftiano. Sanidade e horror cósmico.",
    "espacial": f"{PROMPT_MESTRE_BASE} CENÁRIO: Horror Espacial (Dead Space). Naves e alienígenas."
}

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

def converter_historico_para_gemini(historico_site):
    historico_gemini = []
    for msg in historico_site:
        role = 'user'
        if msg['tipo'] == 'bot':
            role = 'model'
        elif msg['tipo'] == 'system': 
            role = 'user'
            
        if "Criando" in msg['text'] or "Erro" in msg['text'] or "..." in msg['text']:
            continue
            
        historico_gemini.append({
            "role": role,
            "parts": [msg['text']]
        })
    return historico_gemini

def gerar_resposta_blindada(prompt_usuario, historico_formatado):
    historico_formatado.append({"role": "user", "parts": [prompt_usuario]})

    for nome_modelo in MODELOS_PARA_TENTAR:
        try:
            chave_escolhida = random.choice(CHAVES) if CHAVES else os.getenv("GEMINI_API_KEY")
            if not chave_escolhida: raise Exception("Sem chaves!")

            genai.configure(api_key=chave_escolhida)
            print(f"--> Jogando no {nome_modelo}...") 
            
            model = genai.GenerativeModel(nome_modelo, generation_config=generation_config)
            
            # REMOVIDO O SPLIT QUE CORTAVA O TEXTO
            response = model.generate_content(historico_formatado)
            texto_resposta = response.text
            
            return texto_resposta, 200
            
        except Exception as e:
            print(f"Erro no {nome_modelo}: {e}")
            time.sleep(0.5) 
            continue

    return "⚠️ O Mestre está rolando dados. Tente novamente em 10s.", 429

@app.route('/api/chat', methods=['POST'])
def chat():
    dados = request.json
    # Prompt reforçado na mensagem do usuário
    msg_usuario = f"{dados.get('message')} [Mestre: Narre o resultado com detalhes. E termine perguntando: O que você faz?]"
    
    historico_bruto = dados.get('history', []) 
    historico_gemini = converter_historico_para_gemini(historico_bruto)
    
    texto, status = gerar_resposta_blindada(msg_usuario, historico_gemini)
    return jsonify({"reply": texto}), status

@app.route('/api/reset', methods=['POST'])
def reset_game():
    tema = request.json.get('theme', 'medieval')
    prompt_completo = TEMAS.get(tema, TEMAS['medieval'])
    
    comando_inicial = f"""
    SISTEMA: {prompt_completo}
    INÍCIO: O jogador começa a aventura.
    DESCREVA: Onde ele está e um PERIGO IMEDIATO.
    AÇÃO: Peça uma reação.
    """
    
    texto, status = gerar_resposta_blindada(comando_inicial, [])
    return jsonify({"reply": texto}), status

@app.route('/api/continue', methods=['POST'])
def continue_game():
    return jsonify({"reply": "A saga continua..."}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)