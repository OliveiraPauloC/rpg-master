import ReactMarkdown from 'react-markdown'
import { useState, useEffect, useRef } from 'react'
import { Mic, MicOff, Send, Volume2, Loader2, RotateCcw, Sword, Zap, Ghost, Rocket, Dices, FastForward, Square, Settings, X, Music, Backpack, Info, Github, Keyboard, ChevronDown } from 'lucide-react'
import axios from 'axios'
import './App.css'

// --- IMPORTS DOS SONS ---
import somDados from './assets/dados.mp3'
import musMedieval from './assets/medieval.mp3'
import musCyberpunk from './assets/cyberpunk.mp3'
import musTerror from './assets/terror.mp3'
import musEspacial from './assets/espacial.mp3'

const API_URL = "https://rpg-master-32ct.onrender.com"; 

function App() {
  const [texto, setTexto] = useState('')
  const [mensagens, setMensagens] = useState([])
  const [ouvindo, setOuvindo] = useState(false)
  const [loading, setLoading] = useState(false)
  const [falando, setFalando] = useState(false)
  const [rolandoDado, setRolandoDado] = useState(false)
  const [jogoIniciado, setJogoIniciado] = useState(false)
  const [podeContinuar, setPodeContinuar] = useState(false)
  
  // Configs
  const [mostrarConfig, setMostrarConfig] = useState(false)
  const [vozFixa, setVozFixa] = useState(null);
  const [tom, setTom] = useState(0.8);
  const [velocidade, setVelocidade] = useState(1.1); 

  // Música
  const [musicaAtual, setMusicaAtual] = useState(null);
  const [musicaLigada, setMusicaLigada] = useState(true);
  const [volMusica, setVolMusica] = useState(0.1);

  // --- ESTADOS DO INVENTÁRIO ---
  const [invAberto, setInvAberto] = useState(false);
  const [ficha, setFicha] = useState({
    classe: '',
    atributos: { FOR: 0, DES: 0, INT: 0 },
    itens: []
  });

  const [mostrarCreditos, setMostrarCreditos] = useState(false);
  const [digitando, setDigitando] = useState(false);

  const MUSICAS = {
    medieval: musMedieval,
    cyberpunk: musCyberpunk,
    terror: musTerror,
    espacial: musEspacial
  };

  const INTRODUCOES = {
    medieval: "⚔️ **Saudações, bravo guerreiro.** Eu serei seu guia através das brumas do destino. Prepare sua lâmina, pois o mundo não perdoa os fracos.",
    cyberpunk: "🔌 **Link Neural Estabelecido.** Bem-vindo a Neo-Veneza, mercenário. Eu sou a Voz da Rede. Verifique seus implantes. O contrato começa agora.",
    terror: "🕯️ **Você não deveria ter vindo...** Mas agora que está aqui, eu serei a voz na sua cabeça. Mantenha a sanidade, investigador. As sombras estão famintas.",
    espacial: "🚀 **Sistemas de Suporte: Críticos.** Acorde, engenheiro. Eu sou a I.A. da nave USG Ishimura. Estamos à deriva e não estamos sozinhos..."
  };

  // --- LOADOUTS INICIAIS ---
  const LOADOUTS = {
    medieval: {
      classe: "Guerreiro",
      itens: ["Espada Longa", "Poção de Cura (x2)", "Mapa Antigo", "Pederneira"],
      atributos: { FOR: 16, DES: 12, INT: 10 }
    },
    cyberpunk: {
      classe: "Mercenário",
      itens: ["Pistola Smart", "Chip de Créditos", "Inalador de Adrenalina", "Deck de Hack"],
      atributos: { FOR: 12, DES: 16, INT: 14 }
    },
    terror: {
      classe: "Investigador",
      itens: ["Lanterna Velha", "Caderno de Notas", "Revólver .38", "Amuleto Estranho"],
      atributos: { FOR: 10, DES: 12, INT: 16 }
    },
    espacial: {
      classe: "Engenheiro",
      itens: ["Cortador de Plasma", "Tanque de O2", "Cartão de Acesso Nível 1", "Medkit"],
      atributos: { FOR: 12, DES: 10, INT: 18 }
    }
  };

  useEffect(() => {
    const carregarVozGoogle = () => {
      const lista = window.speechSynthesis.getVoices();
      const google = lista.find(v => v.name.includes('Google') && v.lang.includes('pt-BR'));
      if (google) setVozFixa(google);
      else if (lista.length > 0) setVozFixa(lista[0]);
    };
    window.speechSynthesis.onvoiceschanged = carregarVozGoogle;
    carregarVozGoogle();
  }, []);

  const messagesEndRef = useRef(null)

  const limparTextoParaFala = (textoBruto) => {
    return textoBruto.replace(/[#*]/g, '').replace(/\[.*?\]/g, '').replace(/\(.*?\)/g, '').replace(/[\u{1F600}-\u{1F6FF}\u{1F300}-\u{1F5FF}\u{1F680}-\u{1F6FF}\u{1F700}-\u{1F77F}\u{1F780}-\u{1F7FF}\u{1F800}-\u{1F8FF}\u{1F900}-\u{1F9FF}\u{1FA00}-\u{1FAFF}\u{2600}-\u{26FF}\u{2700}-\u{27BF}\u{2300}-\u{23FF}]/gu, '').trim();
  }

  const pararFalar = () => {
    window.speechSynthesis.cancel();
    setFalando(false);
  }

  const falarTexto = (mensagem) => {
    pararFalar();
    const textoLimpo = limparTextoParaFala(mensagem);
    const utterance = new SpeechSynthesisUtterance(textoLimpo);
    utterance.lang = 'pt-BR';
    if (vozFixa) utterance.voice = vozFixa;
    utterance.rate = velocidade; 
    utterance.pitch = tom; 
    utterance.onstart = () => setFalando(true);
    utterance.onend = () => setFalando(false);
    window.speechSynthesis.speak(utterance);
  }

  const tocarMusicaFundo = (tema) => {
    if (musicaAtual) {
      musicaAtual.pause();
      musicaAtual.currentTime = 0;
    }
    const arquivo = MUSICAS[tema];
    if (arquivo) {
      const audio = new Audio(arquivo);
      audio.loop = true;
      audio.volume = volMusica;
      if (musicaLigada) audio.play().catch(e => console.log("Erro ao tocar:", e));
      setMusicaAtual(audio);
    }
  }

  const mudarVolumeMusica = (e) => {
    const novoVolume = parseFloat(e.target.value);
    setVolMusica(novoVolume);
    if (musicaAtual) musicaAtual.volume = novoVolume;
  }

  const toggleMusica = () => {
    if (!musicaAtual) return;
    if (musicaLigada) {
      musicaAtual.pause();
      setMusicaLigada(false);
    } else {
      musicaAtual.play().catch(e => console.log(e));
      setMusicaLigada(true);
    }
  }

  const pararMusicaTotal = () => {
    if (musicaAtual) {
      musicaAtual.pause();
      musicaAtual.currentTime = 0;
      setMusicaAtual(null);
    }
  }

  let recognition = null;
  if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.lang = 'pt-BR';
    recognition.continuous = false;
  }
  
  const ligarMicrofone = () => {
    if (falando) pararFalar();
    if (!recognition) return;
    if (ouvindo) { recognition.stop(); setOuvindo(false); return; }
    setOuvindo(true);
    recognition.start();
    recognition.onresult = (ev) => { setTexto(ev.results[0][0].transcript); setOuvindo(false); };
    recognition.onend = () => { setOuvindo(false); }
  }

  const scrollToBottom = () => messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  useEffect(() => scrollToBottom(), [mensagens, loading]);

  const rolarDado = () => {
    if (loading || rolandoDado) return;
    const audio = new Audio(somDados);
    audio.volume = 0.5;
    audio.play();
    setRolandoDado(true);
    setTimeout(() => {
      const resultado = Math.floor(Math.random() * 20) + 1;
      setRolandoDado(false);
      enviarMensagem(null, `🎲 Rolei um d20 e tirei: ${resultado}`);
    }, 1500);
  }

  // --- NOVA FUNÇÃO (ADICIONADA): PROCESSADOR DE INVENTÁRIO ---
  const processarComandosIA = (textoResposta) => {
    let novoTexto = textoResposta;
    let inventarioAtualizado = [...ficha.itens];
    let houveMudanca = false;

    // Adicionar Item [ADD: Item]
    const regexAdd = /\[ADD:\s*(.*?)\]/g;
    let matchAdd;
    while ((matchAdd = regexAdd.exec(textoResposta)) !== null) {
      const item = matchAdd[1].trim();
      inventarioAtualizado.push(item);
      novoTexto = novoTexto.replace(matchAdd[0], ''); 
      houveMudanca = true;
    }

    // Remover Item [REMOVE: Item]
    const regexRemove = /\[REMOVE:\s*(.*?)\]/g;
    let matchRemove;
    while ((matchRemove = regexRemove.exec(textoResposta)) !== null) {
      const itemParaRemover = matchRemove[1].trim();
      const index = inventarioAtualizado.indexOf(itemParaRemover);
      if (index > -1) {
        inventarioAtualizado.splice(index, 1);
        houveMudanca = true;
      }
      novoTexto = novoTexto.replace(matchRemove[0], ''); 
    }

    if (houveMudanca) {
      setFicha(prev => ({ ...prev, itens: inventarioAtualizado }));
    }

    return novoTexto.trim();
  }

  // --- FUNÇÃO AJUSTADA: AGORA ENVIA A FICHA ---
  const iniciarAventura = async (tema) => {
    setLoading(true); setMensagens([]); setJogoIniciado(true); setPodeContinuar(false);
    
    setMusicaLigada(true); 
    tocarMusicaFundo(tema);

    const loadout = LOADOUTS[tema] || LOADOUTS['medieval'];
    setFicha(loadout);

    const introManual = INTRODUCOES[tema] || INTRODUCOES['medieval'];
    const msgIntro = { tipo: 'system', text: introManual };
    setMensagens([msgIntro]);
    falarTexto(introManual);

    try {
      // Envia charData para o backend
      const response = await axios.post(`${API_URL}/api/reset`, { 
        theme: tema,
        charData: loadout
      });
      
      // Processa se a IA mandou adicionar algo
      const textoLimpo = processarComandosIA(response.data.reply);
      setMensagens(prev => [...prev, { tipo: 'bot', text: textoLimpo }]);
    } catch (error) { 
      const msgErro = error.response?.data?.reply || "Erro ao conectar.";
      setMensagens(prev => [...prev, { tipo: 'bot', text: msgErro }]); 
    } finally { 
      setLoading(false); 
    }
  }

  const continuarCampanha = async () => {
    setLoading(true); setPodeContinuar(false);
    setMensagens(prev => [...prev, { tipo: 'system', text: '⏳ Salvando lenda e avançando...' }]);
    try {
      const response = await axios.post(`${API_URL}/api/continue`);
      const intro = response.data.reply;
      setMensagens([{ tipo: 'system', text: '✨ NOVA TEMPORADA' }, { tipo: 'bot', text: intro }]);
      falarTexto(intro);
    } catch (error) { setPodeContinuar(true); } 
    finally { setLoading(false); }
  }

  // --- FUNÇÃO AJUSTADA: ENVIA FICHA E PROCESSA ITENS ---
  const enviarMensagem = async (e, textoOpcional = null) => {
    if (e) e.preventDefault();
    const txt = textoOpcional || texto;
    if (!txt.trim()) return;
    pararFalar();
    const tipoMsg = txt.includes('🎲') ? 'system' : 'user';
    
    const novasMensagens = [...mensagens, { tipo: tipoMsg, text: txt }];
    setMensagens(novasMensagens);
    
    if (tipoMsg === 'user') setTexto('');
    setLoading(true);
    try {
      // Envia charData e histórico
      const response = await axios.post(`${API_URL}/api/chat`, { 
        message: txt,
        history: novasMensagens,
        charData: ficha 
      });

      let respostaIA = response.data.reply;
      
      // Processa tags [ADD]/[REMOVE] e limpa texto
      respostaIA = processarComandosIA(respostaIA);

      if (respostaIA.includes('[FIM]')) {
        setPodeContinuar(true);
        respostaIA = respostaIA.replace('[FIM]', '');
      }
      setMensagens(prev => [...prev, { tipo: 'bot', text: respostaIA }]);
      falarTexto(respostaIA);
    } catch (error) { 
      const msgErro = error.response?.data?.reply || "Silêncio...";
      setMensagens(prev => [...prev, { tipo: 'bot', text: msgErro }]);
    } 
    finally { setLoading(false); }
  }

  const resetarJogoTotal = () => {
    setJogoIniciado(false);
    setInvAberto(false);
    pararFalar();
    pararMusicaTotal();
  }

  if (!jogoIniciado) {
    return (
      <div className="container menu-screen">
        <button className="credits-btn" onClick={() => setMostrarCreditos(true)} title="Sobre o Criador">
          <Info size={32} />
        </button>

        {mostrarCreditos && (
          <div className="modal-overlay">
            <div className="credits-box">
              <button className="btn-close-modal" onClick={() => setMostrarCreditos(false)}><X size={24}/></button>
              <h2>Mestre dos Códigos</h2>
              <div className="dev-avatar">🧙‍♂️</div>
              <p>Este RPG foi desenvolvido com magia e código por:</p>
              <h3>Paulo Oliveira</h3>
              <p className="tech-stack">React • Python • D20</p>
              
              <div className="social-links">
                <a href="https://github.com/OliveiraPauloC" target="_blank" className="social-btn"><Github size={24}/> GitHub</a>
              </div>
              
              <p className="version">Versão 1.0</p>
            </div>
          </div>
        )}

        <h1>Escolha sua Aventura <Dices size={56} className="title-icon"/></h1>
        <div className="grid-temas">
          <button className="btn-tema medieval" onClick={() => iniciarAventura('medieval')}><Sword size={64}/><span>Medieval</span></button>
          <button className="btn-tema cyberpunk" onClick={() => iniciarAventura('cyberpunk')}><Zap size={64}/><span>Cyberpunk</span></button>
          <button className="btn-tema terror" onClick={() => iniciarAventura('terror')}><Ghost size={64}/><span>Terror</span></button>
          <button className="btn-tema espacial" onClick={() => iniciarAventura('espacial')}><Rocket size={64}/><span>Espacial</span></button>
        </div>
      </div>
    )
  }

  return (
    <div className="container">

      <div className={`inventory-panel ${invAberto ? 'open' : ''}`}>
        <div className="inventory-header">
          <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
             <h2>{ficha.classe}</h2>
             <button onClick={() => setInvAberto(false)} className="btn-fechar-voz"><X size={24}/></button>
          </div>
        </div>
        
        <div className="stats-grid">
          <div className="stat-row str">
            <span className="stat-name">FOR</span>
            <div className="stat-bar-bg"><div className="stat-bar-fill" style={{width: `${(ficha.atributos.FOR/20)*100}%`}}></div></div>
            <span>{ficha.atributos.FOR}</span>
          </div>
          <div className="stat-row dex">
            <span className="stat-name">DES</span>
            <div className="stat-bar-bg"><div className="stat-bar-fill" style={{width: `${(ficha.atributos.DES/20)*100}%`}}></div></div>
            <span>{ficha.atributos.DES}</span>
          </div>
          <div className="stat-row int">
            <span className="stat-name">INT</span>
            <div className="stat-bar-bg"><div className="stat-bar-fill" style={{width: `${(ficha.atributos.INT/20)*100}%`}}></div></div>
            <span>{ficha.atributos.INT}</span>
          </div>
        </div>

        <hr style={{borderColor: 'rgba(255,255,255,0.1)', margin: '10px 0'}}/>
        
        <h3 style={{color: '#ffd700', fontFamily: 'Cinzel'}}>Mochila</h3>
        <ul className="items-list">
          {ficha.itens.map((item, i) => (
            <li key={i} className="item-card">
              <span className="item-icon">📦</span>
              <span className="item-name">{item}</span>
            </li>
          ))}
        </ul>
      </div>

      <div className="chat-box">
        <header>
          <h1>RPG Master 🎙️</h1>
          {mostrarConfig && (
            <div className="voz-selector">
              <div className="config-header">
                <h3>Configurações</h3>
                <button onClick={() => setMostrarConfig(false)} className="btn-fechar-voz"><X size={24} /></button>
              </div>
              <div className="slider-group">
                <label>Voz (Grave/Aguda): {tom}</label>
                <input type="range" min="0.5" max="1.5" step="0.1" value={tom} onChange={(e) => setTom(parseFloat(e.target.value))} />
              </div>
              <div className="slider-group">
                <label>Voz (Velocidade): {velocidade}</label>
                <input type="range" min="0.5" max="2" step="0.1" value={velocidade} onChange={(e) => setVelocidade(parseFloat(e.target.value))} />
              </div>
              <div className="slider-group" style={{marginTop: '10px', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '10px'}}>
                <label>Volume Música: {Math.round(volMusica * 100)}%</label>
                <input type="range" min="0" max="1" step="0.05" value={volMusica} onChange={mudarVolumeMusica} />
              </div>
              <button onClick={() => falarTexto("Teste de voz.")} className="btn-teste">Testar</button>
            </div>
          )}
          
          <div className="header-controls">
            <button onClick={() => setInvAberto(!invAberto)} className="btn-header" title="Inventário">
               <Backpack size={28}/>
            </button>

            <button onClick={toggleMusica} className={`btn-header music ${musicaLigada ? 'on' : 'off'}`} title="Ligar/Desligar Música">
              <Music size={28} />
            </button>
            <button onClick={() => setMostrarConfig(!mostrarConfig)} className="btn-header settings"><Settings size={28} /></button>
            {falando && <button onClick={pararFalar} className="btn-header stop"><Square size={28} fill="white" /></button>}
            {podeContinuar && <button onClick={continuarCampanha} className="btn-header continue pulsando"><FastForward size={28}/></button>}
            <button onClick={resetarJogoTotal} className="btn-header reset"><RotateCcw size={28}/></button>
          </div>
        </header>

        <div className="messages-area">
          {mensagens.map((msg, i) => (
            <div key={i} className={`message ${msg.tipo}`}>
              <div className="markdown-content"><ReactMarkdown>{msg.text}</ReactMarkdown></div>
              <div className="msg-controls">
                {(msg.tipo === 'bot' || msg.tipo === 'system') && <button onClick={() => falarTexto(msg.text)} className="btn-falar-novamente"><Volume2 size={16}/></button>}
              </div>
            </div>
          ))}
          {podeContinuar && <div className="message system">🏆 Aventura Concluída! Clique no botão verde acima.</div>}
          {loading && <div className="message bot loading-msg"><Loader2 className="spin" size={20}/> Criando situações...</div>}
          <div ref={messagesEndRef} />
        </div>
        <div className="input-container">
          
          <div className={`writing-panel ${digitando ? 'open' : ''}`}>
            <div className="writing-header">
              <span>Sua Ação</span>
              <button onClick={() => setDigitando(false)} className="btn-close-writing"><ChevronDown size={24}/></button>
            </div>
            <form onSubmit={(e) => { setDigitando(false); enviarMensagem(e); }} className="writing-form">
              <textarea 
                value={texto} 
                onChange={(e) => setTexto(e.target.value)} 
                placeholder="Descreva detalhadamente o que você vai fazer..." 
                autoFocus={digitando}
              />
              <button type="submit" className="send-btn-large">
                ENVIAR AÇÃO <Send size={20}/>
              </button>
            </form>
          </div>

          <div className="action-bar">
            <button type="button" className={`dice-btn ${rolandoDado ? 'rolling' : ''}`} onClick={rolarDado} disabled={loading || rolandoDado || podeContinuar}>
              <Dices size={28}/>
            </button>
            
            <button type="button" className={`mic-btn ${ouvindo ? 'ouvindo' : ''}`} onClick={ligarMicrofone} disabled={loading || podeContinuar}>
              {ouvindo ? <MicOff size={28}/> : <Mic size={28}/>}
            </button>

            <button type="button" className="btn-responder" onClick={() => setDigitando(true)} disabled={loading || podeContinuar}>
              <span>Responder...</span>
              <Keyboard size={24}/>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
export default App