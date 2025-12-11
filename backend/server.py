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
CHAVES = [k for k in CHAVES if k] # Remove vazias para não dar erro

# 1000 tokens é muito mais que suficiente para 2 parágrafos (sobra muito espaço)
generation_config = {
    "temperature": 1.0,
    "max_output_tokens": 1000, 
}

MODELOS_PARA_TENTAR = [
    'gemini-flash-latest',       
    'gemini-2.0-flash-lite',     
    'gemini-2.0-flash',          
    'gemini-pro-latest'          
]

historico_por_ip = {} 

# --- PROMPT REFINADO (SEGURANÇA CONTRA TEXTÃO) ---
ESTRUTURA_NARRATIVA = """
DIRETRIZES DE MESTRE (RPG DE TEXTO MOBILE):
1. **TAMANHO:** Responda SEMPRE em no máximo 2 parágrafos. Seja denso e atmosférico, mas breve. O jogador está no celular.
2. **PAUSA:** NUNCA avance a história além da consequência imediata. Pare e espere a reação.
3. **REGRA DE OURO:** NUNCA descreva as ações ou falas do personagem do jogador. Você controla o mundo, ele controla o herói.
4. **FINALIZAÇÃO:** Termine o texto deixando claro que é a vez do jogador (ex: "O que você faz?", "A criatura avança, qual sua reação?").
5. **ATOS:** O jogo deve ser lento. Não resolva o mistério no começo. Faça o jogador sofrer e lutar.
"""

PROMPT_MESTRE_BASE = f"""
{ESTRUTURA_NARRATIVA}
PERSONALIDADE: Narrativo, Sombrio, Imersivo (Dark Fantasy/Sci-Fi).
REGRAS TÉCNICAS:
- Use **Negrito** para itens, nomes e perigos.
- Use *Itálico* para sons e sussurros.
"""

TEMAS = {
    "medieval": f"{PROMPT_MESTRE_BASE} CENÁRIO: Dark Fantasy (Estilo Dark Souls). PROTAGONISTA: Guerreiro.",
    "cyberpunk": f"{PROMPT_MESTRE_BASE} CENÁRIO: Cyberpunk Distópico. PROTAGONISTA: Mercenário.",
    "terror": f"{PROMPT_MESTRE_BASE} CENÁRIO: Terror Lovecraftiano Anos 20. PROTAGONISTA: Investigador.",
    "espacial": f"{PROMPT_MESTRE_BASE} CENÁRIO: Horror Espacial (Estilo Dead Space). PROTAGONISTA: Engenheiro."
}

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

def gerar_resposta_blindada(prompt_usuario, historico):
    # Adiciona a mensagem do usuário na memória temporária antes de enviar
    historico.append({"role": "user", "parts": [prompt_usuario]})

    for nome_modelo in MODELOS_PARA_TENTAR:
        try:
            # Sorteia uma chave se houver lista, senão tenta pegar a única que tiver
            chave_escolhida = random.choice(CHAVES) if CHAVES else os.getenv("GEMINI_API_KEY")
            
            # Se não tiver nenhuma chave configurada, vai dar erro aqui
            if not chave_escolhida: raise Exception("Nenhuma chave de API encontrada!")

            genai.configure(api_key=chave_escolhida)
            
            print(f"--> Jogando no {nome_modelo}...") # Log para você ver no Render
            model = genai.GenerativeModel(nome_modelo, generation_config=generation_config)
            
            response = model.generate_content(historico)
            texto_resposta = response.text
            
            # Se deu certo, salva a resposta na memória e retorna
            historico.append({"role": "model", "parts": [texto_resposta]})
            return texto_resposta, 200
            
        except Exception as e:
            print(f"❌ Erro no {nome_modelo}: {e}")
            time.sleep(0.5) # Espera um pouquinho antes de tentar o próximo
            continue

    # Se saiu do loop, tudo falhou
    return "⚠️ **O Mestre precisa de um descanso.**<br>Muitos jogadores ao mesmo tempo. Aguarde 10 segundos e tente de novo.", 429

@app.route('/api/chat', methods=['POST'])
def chat():
    user_ip = request.remote_addr 
    if user_ip not in historico_por_ip: historico_por_ip[user_ip] = []
    
    dados = request.json
    # O sufixo força a IA a lembrar que deve parar de falar
    msg_usuario = f"{dados.get('message')} [Responda em 2 parágrafos e PARE]"
    
    texto, status = gerar_resposta_blindada(msg_usuario, historico_por_ip[user_ip])
    return jsonify({"reply": texto}), status

@app.route('/api/reset', methods=['POST'])
def reset_game():
    user_ip = request.remote_addr
    historico_por_ip[user_ip] = [] 
    
    tema = request.json.get('theme', 'medieval')
    prompt_completo = TEMAS.get(tema, TEMAS['medieval'])
    
    # Prompt inicial ultra-específico para não começar narrando a vida toda
    comando_inicial = f"""
    SISTEMA: {prompt_completo}
    AÇÃO IMEDIATA: Introduza APENAS a cena inicial.
    Descreva onde o personagem acorda/está e qual o perigo ou mistério visível.
    NÃO faça o personagem andar nem falar nada.
    Termine perguntando o que ele faz.
    """
    
    texto, status = gerar_resposta_blindada(comando_inicial, historico_por_ip[user_ip])
    return jsonify({"reply": texto}), status

@app.route('/api/continue', methods=['POST'])
def continue_game():
    user_ip = request.remote_addr
    hist = historico_por_ip.get(user_ip, [])
    
    resumo, status = gerar_resposta_blindada("Resuma os feitos do personagem em 1 parágrafo para a próxima aventura.", hist)
    if status != 200: return jsonify({"reply": resumo}), status
    
    historico_por_ip[user_ip] = [] 
    prompt_novo = f"{PROMPT_MESTRE_BASE} \n NOVA TEMPORADA INICIADA. VETERANO: {resumo} \n AÇÃO: Comece uma nova situação de perigo. Seja breve."
    
    texto, status = gerar_resposta_blindada(prompt_novo, historico_por_ip[user_ip])
    return jsonify({"reply": texto}), status

if __name__ == '__main__':
    app.run(debug=True, port=5000)