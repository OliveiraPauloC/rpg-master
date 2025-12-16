from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
from google.api_core.exceptions import ResourceExhausted, InternalServerError
import os
from dotenv import load_dotenv
import time
import random

load_dotenv()

CHAVES = [
    os.getenv("GEMINI_API_KEY"),
    os.getenv("GEMINI_API_KEY_2"),
    os.getenv("GEMINI_API_KEY_3")
]
CHAVES = [k for k in CHAVES if k] 

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

# --- PROMPT DO MESTRE (MANTÉM AS REGRAS DE DADO E INTENÇÃO) ---
ESTRUTURA_NARRATIVA = """
DIRETRIZES DE MESTRE DE RPG (SISTEMA D20 RÍGIDO):

VOCÊ É O MESTRE, NÃO O ESCRITOR.
O JOGADOR DIZ A INTENÇÃO ("EU ATIRO"). O DADO DIZ O RESULTADO ("ACERTOU").

REGRAS DE COMBATE E DADOS:
1. **INTENÇÃO vs RESULTADO:** Se o jogador disser "Eu ataco" ou "Tento abrir", NUNCA narre o sucesso imediato.
   - RESPOSTA CORRETA: "A porta parece trancada. Role um teste de Força (CD 15) para arrombar." ou "O guarda saca a espada. Role Iniciativa (d20)."
2. **AGUARDE O DADO:** Só narre o resultado final (se matou, se abriu, se caiu) DEPOIS que o jogador enviar o valor do dado (ex: "Rolei 15").
3. **NARRATIVA DINÂMICA:** Se o jogador rolar Sucesso, narre uma cena heroica. Se rolar Falha, narre uma complicação ou dano.

CONSISTÊNCIA DE TEMA:
- Respeite as leis da física e magia do tema escolhido. Sem pistolas laser na Idade Média.

DIRETRIZES DE MESTRE DE RPG (SISTEMA D20 + INVENTÁRIO REAL):

VOCÊ É O MESTRE. O JOGADOR É O HERÓI.
O DADO DEFINE O SUCESSO. O INVENTÁRIO É REAL.

REGRAS DE OURO:
1. **DADOS:** Se houver risco, PEÇA UM TESTE (ex: "Role Força CD 12"). Só narre o sucesso após o jogador rolar.
2. **INVENTÁRIO AUTOMÁTICO (IMPORTANTE):** - Se o jogador GANHAR um item, escreva no final: `[ADD: Nome do Item]`
   - Se o jogador GASTAR/PERDER um item, escreva: `[REMOVE: Nome Exato do Item]`
   - O código do jogo vai ler essas tags e atualizar a mochila do jogador. Não fale sobre "atualizar inventário" no texto, apenas use as tags.

ESTRUTURA:
- 4 Atos (10-15 turnos cada). Não escreva "Ato X" no texto.

FORMATO:
- Máximo 2 parágrafos.
- Termine SEMPRE com "O que você faz?" ou pedindo rolagem.
"""

PROMPT_MESTRE_BASE = f"""
{ESTRUTURA_NARRATIVA}
TÉCNICA:
- Use **Negrito** para inimigos e CDs (ex: **CD 15**).
- Use *Itálico* para sons.
"""

TEMAS = {
    "medieval": f"{PROMPT_MESTRE_BASE} CENÁRIO: Alta Fantasia (D&D). Espadas, Magia, Dragões, Masmorras.",
    "cyberpunk": f"{PROMPT_MESTRE_BASE} CENÁRIO: Cyberpunk Distópico. Neon, Implantes, Hackers, Megacorporações.",
    "terror": f"{PROMPT_MESTRE_BASE} CENÁRIO: Terror Lovecraftiano (Anos 1920). Investigação, Loucura, Cultos, Horror Cósmico.",
    "espacial": f"{PROMPT_MESTRE_BASE} CENÁRIO: Sci-Fi Horror (Dead Space/Alien). Naves abandonadas, Criossono, Engenharia, Vazio."
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
            
            response = model.generate_content(historico_formatado)
            texto_resposta = response.text
            
            return texto_resposta, 200
            
        except Exception as e:
            print(f"Erro no {nome_modelo}: {e}")
            time.sleep(0.5) 
            continue

    return "⚠️ O Mestre está rolando dados atrás do escudo. Tente novamente.", 429

@app.route('/api/chat', methods=['POST'])
def chat():
    dados = request.json
    msg_original = dados.get('message')
    ficha = dados.get('charData', {}) # <--- AQUI: Recebe a ficha do Frontend
    
    # 1. INJETA O INVENTÁRIO NO CONTEXTO (Para a IA saber o que você tem)
    info_personagem = ""
    if ficha:
        itens = ", ".join(ficha.get('itens', []))
        stats = ficha.get('atributos', {})
        info_personagem = f"[CONTEXTO ATUAL: Itens na Mochila: {itens} | Atributos: FOR {stats.get('FOR')}, DES {stats.get('DES')}, INT {stats.get('INT')}]"

    # 2. INSTRUÇÃO EXTRA (Dados + Gestão de Itens)
    if "🎲" in msg_original or "Rolei" in msg_original:
        instrucao = "[Mestre: O jogador rolou. Narre o resultado. Se ele gastou itens (poção, flecha), use as tags [REMOVE]/[ADD] para atualizar a mochila.]"
    else:
        instrucao = "[Mestre: O jogador declarou intenção. Peça teste se necessário. Se ele achar itens, use [ADD: Item].]"

    msg_final = f"{info_personagem} \n JOGADOR: {msg_original} \n {instrucao}"
    
    historico_bruto = dados.get('history', []) 
    historico_gemini = converter_historico_para_gemini(historico_bruto)
    
    texto, status = gerar_resposta_blindada(msg_final, historico_gemini)
    return jsonify({"reply": texto}), status

@app.route('/api/reset', methods=['POST'])
def reset_game():
    tema = request.json.get('theme', 'medieval')

    ficha_inicial = request.json.get('charData', {})

    itens_str = ", ".join(ficha_inicial.get('itens', [])) if ficha_inicial else "Equipamento Básico"
    atributos_str = str(ficha_inicial.get('atributos', {})) if ficha_inicial else ""

    prompt_completo = TEMAS.get(tema, TEMAS['medieval'])
    
    # --- AQUI ESTÁ A MÁGICA DOS INÍCIOS PERSONALIZADOS ---
    INICIOS_TEMATICOS = {
        "medieval": """
        INÍCIO (ESTILO MISSÃO D&D):
        1. O jogador é um aventureiro experiente com uma MISSÃO CLARA (ex: recuperar um item, salvar alguém).
        2. Ele já está no local do objetivo (entrada da masmorra, castelo, caverna).
        3. Descreva o equipamento dele e o obstáculo imediato (porta, guarda, enigma).
        4. O jogador SABE o que tem que fazer.
        """,
        
        "cyberpunk": """
        INÍCIO (ESTILO GIG/TRABALHO):
        1. O jogador é um Mercenário no meio de um 'Gig' (trabalho arriscado).
        2. A situação já está tensa (invadindo um sistema, negociação falhando, fuga de corporação).
        3. A tecnologia é onipresente. O objetivo é cumprir o contrato e receber o pagamento.
        """,
        
        "terror": """
        INÍCIO (ESTILO AMNÉSIA/MISTÉRIO):
        1. O jogador acorda desorientado, sem saber como chegou ali.
        2. O ambiente é opressor, escuro e desconhecido.
        3. Sensação de vulnerabilidade total. O objetivo inicial é apenas entender onde está e sobreviver.
        """,
        
        "espacial": """
        INÍCIO (ESTILO ISOLAMENTO/FALHA):
        1. O jogador acorda de criossono ou chega em uma estação que não responde.
        2. Alarmes soando, luzes de emergência, silêncio no rádio.
        3. A tecnologia falhou. O jogador está isolado no vácuo. Objetivo: Descobrir o que aconteceu com a tripulação.
        """
    }
    
    estilo_inicio = INICIOS_TEMATICOS.get(tema, INICIOS_TEMATICOS['medieval'])
    
    comando_inicial = f"""
    SISTEMA: {prompt_completo}
    {estilo_inicio}
    
    AÇÃO DE INÍCIO:
    1. Narre o cenário inicial com imersão.
    2. Liste narrativamente o que o jogador carrega ({itens_str}) e seus pontos fortes ({atributos_str}).
    3. **OBRIGATÓRIO:** Diga exatamente: "Você pode conferir seu equipamento clicando no ícone da Mochila 🎒 acima."
    4. Termine perguntando "O que você faz?".
    """
    
    texto, status = gerar_resposta_blindada(comando_inicial, [])
    return jsonify({"reply": texto}), status

@app.route('/api/continue', methods=['POST'])
def continue_game():
    return jsonify({"reply": "A saga continua..."}), 200

if __name__ == '__main__':
    app.run(debug=True, port=5000)