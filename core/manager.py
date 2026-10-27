import os
import sys
import threading
import time
import traceback
from pathlib import Path

_SORGENTI = Path(__file__).resolve().parent.parent
if str(_SORGENTI) not in sys.path:          # con i sorgenti («python core\\manager.py») serve per trovare core/ e modules/; installato non serve (e' tutto dentro CLEF.exe)
    sys.path.append(str(_SORGENTI))

from core.percorsi import PERCORSI
BASE_DIR = PERCORSI.dati                    # i DATI di Lorenzo (config, memory, logs...): mai dentro la cartella del programma installato, che l'aggiornamento sostituisce
from core.logger import avvia_log
from core.versione import versione as numero_versione
VERSIONE = numero_versione(PERCORSI.risorse)
log = avvia_log(BASE_DIR / "logs", VERSIONE)   # prima di tutto il resto, cosi' anche gli errori di avvio finiscono nel log

import webview
from core.config import Config, ENV_PATH
from core.settings import Settings
from modules.monitor_module import Monitor
from modules.chat_module import Chat
from modules.n8n_module import N8n
from modules.registro_module import Registro
from modules.programmi_module import Programmi
from modules.gmail_module import Gmail
from modules.summary_module import Riassuntore
from modules.finance_module import Finanze
from modules.calendar_module import Agenda
from modules.memory_module import Memoria, IncorporatoreOpenAI
from modules.graph_module import Grafo
from modules.vision_module import Vista, finestra_nella_cattura
from modules.voice_module import Voce, TrascrittoreOpenAI, _leggi_json, _scrivi_json
from modules.wake_module import Risveglio, RiconoscitoreEsterno, RiconoscitoreFasterWhisper, riconosci_saluto
from modules.briefing_module import Resoconto, e_richiesta_resoconto
from modules.calcolo_module import calcola
from modules.tasto_module import TastoGlobale, segnale
from modules.istanza_module import Istanza, PORTA_PREDEFINITA
from modules.lingua_module import parole
from modules.promemoria_module import Promemoria
from modules.avvisi_module import Avvisi
from modules.modello_module import Modelli
from modules.stato_module import Stato, Sessioni
from modules.avvio_module import AvvioWindows
from modules.icona_module import IconaVassoio, imposta_id_applicazione, applica_icona_finestra
import core.logger as registro_errori
from core.settings import CHIAVI_MODELLO
from modules.backup_module import Backup, applica_ripristino_in_sospeso, comando as comando_backup
from modules.pc_module import Pc
from modules.casa_module import Casa, ClienteHA, credenziali_da_env
from modules.file_module import CercaFile, cartelle_predefinite
from modules.meteo_module import Meteo
from modules.giornata_module import Giornata
from modules.studio_module import Studio
from modules.bozze_module import Bozze, Scrittore
from modules.budget_module import Budget
from modules.aggiorna_module import Aggiornamenti, leggi_impostazioni as impostazioni_aggiornamenti
from modules.telefono_module import Abbinamenti, Telefono, Tailscale, PORTA_PREDEFINITA as PORTA_TELEFONO, PORTA_HTTPS_PREDEFINITA
from modules.telefono_server import ServerTelefono
from modules.telefono_servizi import ServiziTelefono, DOMINI_BASE, DOMINI_ESTESI, TESTO_AIUTO_TELEFONO
from modules.docker_module import DockerDesktop, docker_voluto

MEMORIA_DIR = BASE_DIR / "memory"
UI_DIR = PERCORSI.risorse / "ui"
MEMORIA_DIR.mkdir(exist_ok=True)
CONOSCENZA_DIR = BASE_DIR / "conoscenza"      # i documenti dell'universita': una sottocartella per materia
TITOLO_PRINCIPALE = "C.L.E.F. OS"
TITOLO_VISTA = "C.L.E.F. — Vista schermo"       # il titolo serve anche per togliere la finestra dalle fotografie dello schermo
FINESTRA_VISTA = {"normale": (420, 330), "compatta": (340, 170)}
RISPOSTA_SENZA_OPENAI = "Non riesco a raggiungere OpenAI in questo momento: la risposta non è arrivata."
INVITO_CONFERMA_VOCE = "Per confermare o annullare usi i pulsanti sullo schermo."
PROGRAMMI_SPENTI = "L'apertura dei programmi è spenta: per accenderla togli la riga CLEF_PROGRAMMI=0 dal file config\\.env e riavvia C.L.E.F."
RISVEGLIO_PYTHON = BASE_DIR / "venv_risveglio" / "Scripts" / "python.exe"      # l'ambiente a parte con un Python meno recente (lo crea INSTALLA_RISVEGLIO.bat)
RISVEGLIO_COPIONE = PERCORSI.risorse / "core" / "trascrittore.py"
MODELLI_DIR = BASE_DIR / "modelli"            # il modello di riconoscimento del risveglio (~150 MB, scaricato una volta sola); fuori da memory/ per non pesare nel Sistema
AVVIO_FILE = MEMORIA_DIR / "avvio.json"                 # le scelte sull'apertura di C.L.E.F. (per ora: il resoconto automatico)
TASTO_FILE = MEMORIA_DIR / "tasto.json"                  # il tasto della tastiera che accende e spegne il microfono (scelto dalle Impostazioni)
AVVIO_RITARDO_S = 3.0                                   # il resoconto automatico aspetta che la finestra sia comparsa
FRASE_RIPOSO = "Buonanotte, signore. Resto in ascolto."
FRASE_SPEGNIMENTO = "Buonanotte, signore. Mi spengo."
RIPOSO_ATTESA_ERRORE_S, RIPOSO_ATTESA_CARICO_S = 120, 300      # a finestra nascosta: dopo quanto, se il risveglio non funziona, la finestra ricompare
TITOLI_PROMEMORIA = {"promemoria": "Promemoria", "timer": "Timer", "sveglia": "Sveglia"}
TESTO_AIUTO = (
    "Ecco cosa so fare da solo, quando mi scrivi o mi dici una frase breve:\n"
    "• Promemoria, timer e sveglie: «ricordami domani alle 9 di chiamare Marco», «timer 10 minuti», «svegliami alle 7», «quali promemoria ho?»\n"
    "• Studio: «interrogami su analisi», «riassumi analisi per l'esame» (uso i tuoi documenti; le domande e le correzioni le scrive OpenAI)\n"
    "• File: «cerca il file della tesi», «mostrami gli ultimi file scaricati», poi «apri il primo»\n"
    "• PC: «che ore sono?», «alza il volume», «blocca il pc», «spegni il pc» (prima ti chiedo conferma)\n"
    "• Casa (Home Assistant): «accendi la luce della cucina», «spegni tutte le luci», «che temperatura c'è in salotto?», «com'è la casa?»; tapparelle, cancello, serrature e termostato chiedono sempre conferma\n"
    "• Meteo: «che tempo fa domani?», «devo portare l'ombrello?» (la città si sceglie nelle Impostazioni)\n"
    "• Soldi: «budget cibo 250 euro», «come sono messo con i budget?», «com'è andato il mese?»; nella schermata Bilancio puoi anche correggere o cancellare un movimento\n"
    "• Backup: «fai il backup», «quando è stato l'ultimo backup?»\n"
    "• Programmi: «apri Spotify» · Schermo: «guarda lo schermo» · Conti: «fai 85,90+2573,62» · Giornata: «dammi il resoconto»\n"
    "Le risposte alle mail le prepari dalla schermata Email (pulsante «Prepara una risposta»): le apri in Gmail e le invii tu, io non invio niente. "
    "Per tutto il resto ti rispondo come in una normale chat."
)
COMANDI_LOCALI = (
    "Il programma esegue da solo, senza di te, quando Lorenzo scrive o dice una frase breve e sola: promemoria, timer e sveglie (per esempio «ricordami alle 17 di chiamare Marco»), "
    "interrogazioni sui documenti di studio («interrogami su analisi»), ricerca e apertura di file, volume, luminosità, blocco, spegnimento e riavvio del PC, accendere e spegnere luci e prese di casa, tapparelle, cancello, serrature e termostato (Home Assistant), meteo, "
    "budget e resoconto del mese, backup. Tu non puoi eseguirli e non devi mai dire di averli eseguiti: se Lorenzo li chiede dentro una frase lunga, digli di scrivere solo il comando breve. "
    "Le bozze di risposta alle mail le prepara la schermata Email (pulsante «Prepara una risposta»): tu non scrivi né invii risposte."
)
COMANDI_TELEFONO = (
    "Il programma esegue da solo, senza di te, quando Lorenzo scrive o dice una frase breve e sola: accendere e spegnere luci e prese di casa e regolare il termostato (Home Assistant), "
    "meteo, conti, il resoconto. Tu non puoi eseguirli e non devi mai dire di averli eseguiti: se Lorenzo li chiede dentro una frase lunga, digli di scrivere solo il comando breve.")
NOTA_TELEFONO = (
    "IMPORTANTE: Lorenzo ti scrive dal TELEFONO (accesso a distanza, piccola schermata). Da qui puoi solo LEGGERE (agenda, mail, bilancio, memoria, stato di casa) e rispondere. "
    "NON puoi aggiungere, modificare o cancellare spese, eventi o mail, né usare il PC (programmi, volume, blocco, spegnimento, schermo, file, backup): se Lorenzo lo chiede, digli "
    "con gentilezza che da telefono non si può e che si fa dal PC. Rispondi in modo breve.")
AVVISO_TELEFONO_NON_FATTO = "\n\n⚠ Attenzione: dal telefono non posso scrivere né modificare nulla (spese, eventi, mail): non ho cambiato niente. Si fa dal PC."
AVVISO_TELEFONO_NON_ESEGUITO = ("\n\n⚠ Attenzione: non ho eseguito nessun comando. Per accendere o spegnere qualcosa in casa mi scriva una frase breve e sola, "
                                "per esempio «accendi la luce della cucina».")
_RICHIESTE_AIUTO = {("cosa", "sai", "fare"), ("che", "cosa", "sai", "fare"), ("cosa", "puoi", "fare"), ("che", "cosa", "puoi", "fare"), ("aiuto",), ("help",), ("comandi",),
                    ("quali", "comandi", "hai"), ("quali", "sono", "i", "comandi"), ("elenco", "comandi"), ("lista", "comandi"), ("elenco", "dei", "comandi"),
                    ("cosa", "sai", "fare", "da", "solo"), ("che", "cosa", "sai", "fare", "da", "solo")}
_CORTESIA_AIUTO = {"clef", "per", "favore", "piacere", "grazie", "ehi", "ok", "dai", "senti", "scusa", "allora", "ciao", "adesso", "dimmi"}


def e_richiesta_aiuto(testo):
    """«cosa sai fare?», «aiuto», «quali comandi hai?»: la lista dei comandi che il programma capisce da solo."""
    t = str(testo or "").strip()
    if not t or len(t) > 60:
        return False
    return tuple(p.n for p in parole(t) if p.n not in _CORTESIA_AIUTO) in _RICHIESTE_AIUTO


def _cartella_dialogo():
    """La costante del selettore di cartelle, nelle versioni vecchie e nuove di PyWebView."""
    fd = getattr(webview, "FileDialog", None)
    if fd is not None and hasattr(fd, "FOLDER"):
        return fd.FOLDER
    return getattr(webview, "FOLDER_DIALOG", 20)


def _numero(testo, tipo, predefinito):
    """Valore numerico scritto nel file .env; se manca o non e' un numero valido si usa quello predefinito."""
    try:
        v = tipo(str(testo).replace(",", "."))
        return v if v == v and v not in (float("inf"), float("-inf")) else predefinito
    except (TypeError, ValueError):
        return predefinito


def titolo_voce(testo):
    """Titolo di una chat nata da una conversazione a voce: il microfono e l'inizio della prima frase."""
    t = " ".join(str(testo or "").split())
    if len(t) > 36:
        t = t[:36].rsplit(" ", 1)[0].rstrip(",;:.-") + "…" if " " in t[:36] else t[:36] + "…"
    return "🎙 " + (t or "Conversazione")


class CLEFApi:
    """Centralino: espone alla pagina le funzioni e le collega ai moduli in modules/."""

    def __init__(self):
        Config.check()
        # un backup scelto prima di chiudere si rimette a posto ADESSO, prima che i moduli leggano i file (se qualcosa va storto, C.L.E.F. parte lo stesso)
        try:
            self._ripristino = applica_ripristino_in_sospeso(BASE_DIR)
        except Exception as e:
            log.error("Ripristino del backup non applicato (%s: %s)", type(e).__name__, str(e)[:200])
            self._ripristino = {"ok": False, "testo": "Non sono riuscito a rimettere a posto il backup scelto: i dati attuali sono intatti."}
        if self._ripristino:
            log.info("Ripristino del backup: %s", str(self._ripristino.get("testo", ""))[:200])
        # Gli underscore (_) dicono a PyWebView di IGNORARE queste variabili
        self._window = None
        self._settings = Settings(BASE_DIR / "config" / "settings.json")
        self._sessioni = Sessioni(BASE_DIR / "logs" / "sessioni.json", VERSIONE)       # come e' finita l'ultima volta (schermata Stato)
        # i modelli di OpenAI (chat e trascrizione): il modello in uso puo' cambiare mentre C.L.E.F. e' aperto, per questo i moduli ricevono la FUNZIONE che lo dice
        self._modelli = Modelli(self._settings, Config.OPENAI_API_KEY, Config.OPENAI_MODEL, Config.OPENAI_MODEL_TRASCRIZIONE)
        url_n8n = self._settings.get().get("n8n") or Config.N8N_WEBHOOK_URL   # se cambi l'URL, riavvia C.L.E.F.
        self._monitor = Monitor(MEMORIA_DIR, url_n8n, Config.OPENAI_API_KEY)
        # n8n: i moduli che ne hanno bisogno (posta, finanze...) riceveranno self._n8n
        self._n8n = N8n(url_n8n, token=Config.N8N_TOKEN)
        self._gmail = Gmail(self._n8n, riassuntore=Riassuntore(Config.OPENAI_API_KEY, modello=self._modelli.chat))
        self._finanze = Finanze(self._n8n, os.environ.get("FINANZE_SHEET_ID", ""), os.environ.get("FINANZE_SCHEDA", "Foglio2"))
        self._agenda = Agenda(self._n8n)
        # la memoria (documenti per materia + cose dette in chat): se non parte, il resto di C.L.E.F. funziona lo stesso
        try:
            self._memoria = Memoria(CONOSCENZA_DIR, MEMORIA_DIR / "memoria.db", IncorporatoreOpenAI(Config.OPENAI_API_KEY))
        except Exception as e:
            log.error("Memoria non avviata (%s: %s): la chat funziona senza", type(e).__name__, str(e)[:200])
            self._memoria = None
        self._grafo = Grafo(self._memoria, self._finanze) if self._memoria else None
        # la vista schermo: guarda lo schermo di continuo solo se Lorenzo lo accende; la finestra mobile e' una seconda finestra creata al volo
        self._vista_lock = threading.RLock()
        self._vista_finestra = None
        self._vista_opzioni = {"finestra": True, "includi_proprie": False}
        self._registro = Registro(MEMORIA_DIR / "azioni.jsonl")          # il diario di cio' che C.L.E.F. fa con la tua conferma (schermata Sistema)
        self._vista = Vista(su_avvio=self._vista_avviata, su_stop=self._vista_fermata, registro=self._registro.scrivi)
        # i programmi del PC: «apri Spotify» in chat o a voce. L'elenco lo legge da solo dal menu Start e lo tiene aggiornato; si spegne con CLEF_PROGRAMMI=0 nel file .env
        self._programmi = Programmi(MEMORIA_DIR / "programmi.json", registro=self._registro.scrivi) if Config.PROGRAMMI else None
        # le funzioni "da assistente": promemoria, avvisi, backup, comandi del PC, ricerca file, meteo, studio, bozze di mail, budget
        reg = self._registro.scrivi
        self._promemoria = Promemoria(MEMORIA_DIR / "promemoria.json", su_scatto=self._promemoria_scattato, registro=reg)
        self._avvisi = Avvisi(MEMORIA_DIR / "avvisi.json", self._agenda, self._gmail, attivo=self._avvisi_voluti, su_avviso=self._avviso_nuovo, registro=reg)
        if self._ripristino and self._ripristino.get("testo"):
            self._avvisi.aggiungi("info", str(self._ripristino["testo"]), "Ripristino del backup", persistente=True)
        self._modelli.collega_registro(self._registro.scrivi)
        scadenza_modello = self._modelli.avviso()
        if scadenza_modello:        # un modello di OpenAI sta per essere ritirato (o lo e' gia'): lo si dice subito, con cosa fare
            self._avvisi.aggiungi("info", scadenza_modello, "Modello di OpenAI in scadenza", persistente=True)
        self._backup = Backup(BASE_DIR, MEMORIA_DIR / "backup.json", registro=reg)
        self._pc = Pc(registro=reg)
        # la casa: luci, prese, clima, tapparelle, cancello e serrature tramite Home Assistant. Indirizzo e chiave stanno solo nel file .env (HA_URL, HA_TOKEN)
        self._casa = Casa(MEMORIA_DIR / "casa.json", ClienteHA(lambda: credenziali_da_env(ENV_PATH)), registro=reg)
        self._cerca_file = CercaFile(MEMORIA_DIR / "cartelle_file.json", predefinite=cartelle_predefinite(conoscenza=CONOSCENZA_DIR), registro=reg)
        self._meteo = Meteo(citta=lambda: self._settings.get().get("citta", ""), registro=reg)
        self._giornata = Giornata(self._agenda, self._promemoria, self._meteo)
        self._budget = Budget(MEMORIA_DIR / "budget.json", self._finanze, su_avviso=self._budget_avviso, attivo=self._avvisi_voluti, registro=reg)
        self._studio = Studio(self._memoria, Config.OPENAI_API_KEY, self._modelli.chat, MEMORIA_DIR / "studio.json", registro=reg) if self._memoria else None
        self._bozze = Bozze(self._gmail, Scrittore(Config.OPENAI_API_KEY, self._modelli.chat), registro=reg)
        # la chat riceve gli "strumenti": leggi_finanze, cerca_eventi, elenca_mail, leggi_mail, cerca_memoria ed elenca_memoria LEGGONO; tutti gli altri possono solo PROPORRE (la scrittura parte dal pulsante Conferma)
        self._chat = Chat(MEMORIA_DIR / "chat.json", Config.OPENAI_API_KEY,
                          istruzioni_extra=lambda: self._settings.get().get("pers", ""),
                          strumenti=(self._finanze.strumenti_chat() + self._finanze.strumenti_correzione() + self._agenda.strumenti_chat() + self._gmail.strumenti_chat()
                                     + (self._memoria.strumenti_chat() if self._memoria else []) + self._vista.strumenti_chat() + self._pc.strumenti_chat() + self._casa.strumenti_chat()),
                          memoria=self._memoria, modello=self._modelli.chat, comandi=self._comando_locale, registro=self._registro_chat,
                          apre_programmi=self._programmi is not None, comandi_locali=COMANDI_LOCALI, titoli_ai=Config.TITOLI_AI)
        # la voce: usa la stessa chat di sempre (ogni conversazione a voce diventa una chat in cartella "Voce", ricordata come tutte le altre)
        self._voce_lock = threading.RLock()
        self._voce_chat = None
        self._voce = Voce(MEMORIA_DIR, self._voce_turno, Config.OPENAI_API_KEY, Config.GOOGLE_TTS_API_KEY,
                          voce=Config.VOCE_NOME, velocita=_numero(Config.VOCE_VELOCITA, float, None),
                          limite_caratteri=_numero(Config.VOCE_LIMITE_CARATTERI, int, 950_000), limite_minuti=_numero(Config.VOCE_LIMITE_MINUTI, int, 600),
                          soglia_min=_numero(Config.VOCE_SOGLIA, float, 0.012), dispositivo_ingresso=Config.VOCE_MICROFONO,
                          dispositivo_uscita=Config.VOCE_ALTOPARLANTE, pronuncia=Config.VOCE_PRONUNCIA, registro=self._registro.scrivi,
                          dopo_turno=self._voce_poi, modello_trascrizione=self._modelli.trascrizione, prezzo_minuto=self._modelli.prezzo_trascrizione)
        # il risveglio a voce: «buongiorno Clef» lo accende e gli fa fare il resoconto, «buonanotte Clef» lo mette a riposo. Ascolta in locale: l'audio non esce dal PC
        self._riposo = False                         # True: finestra nascosta, C.L.E.F. in ascolto di «buongiorno Clef»
        self._ridotta = False                        # la finestra e' stata ridotta a icona (invece che nascosta)
        self._istanza = None                         # la porta che impedisce di avere due copie accese (la imposta main)
        self._riposo_lock = threading.RLock()
        self._sveglia_lock = threading.Lock()
        # se esiste l'ambiente a parte (Python 3.13, creato da INSTALLA_RISVEGLIO.bat) il riconoscimento gira li; altrimenti dentro questo stesso Python
        self._riconoscitore = RiconoscitoreEsterno(RISVEGLIO_PYTHON, RISVEGLIO_COPIONE, Config.RISVEGLIO_MODELLO or "base", MODELLI_DIR)
        if not self._riconoscitore.installato():
            self._riconoscitore = RiconoscitoreFasterWhisper(Config.RISVEGLIO_MODELLO or "base", MODELLI_DIR)
        self._risveglio = Risveglio(MEMORIA_DIR / "risveglio.json", self._risveglio_evento, self._riconoscitore, occupato=self._voce.occupata,
                                    dispositivo=Config.VOCE_MICROFONO, soglia_min=_numero(Config.VOCE_SOGLIA, float, 0.012), attivo_predefinito=Config.RISVEGLIO,
                                    bloccato=not Config.RISVEGLIO, nomi_extra=[x.strip() for x in Config.RISVEGLIO_NOMI.split(",") if x.strip()],
                                    registro=self._registro.scrivi)
        self._resoconto = Resoconto(self._monitor, self._gmail, MEMORIA_DIR / "resoconto.json", rinfresca=self._rinfresca_per_resoconto, registro=self._registro.scrivi,
                                    giornata=self._giornata.righe)
        # l'accesso dal telefono (Android, tramite Tailscale): una chat a parte, SENZA gli strumenti del PC. Solo lettura (agenda, mail, bilancio, memoria) e casa;
        # luci, prese e termostato si comandano, serrature/cancelli/garage/tapparelle solo se Lorenzo lo permette. Spento di partenza: lo accende dalle Impostazioni.
        letture_tel = [st for st in (self._finanze.strumenti_chat() + self._agenda.strumenti_chat() + self._gmail.strumenti_chat()
                                     + (self._memoria.strumenti_chat() if self._memoria else [])) if getattr(st, "tipo", "proposta") == "lettura"]
        self._servizi_tel = ServiziTelefono(
            self._casa, self._agenda, self._gmail, self._finanze, TrascrittoreOpenAI(Config.OPENAI_API_KEY, self._modelli.trascrizione) if Config.OPENAI_API_KEY else None,
            comandi=[("casa", self._casa.comando), ("meteo", self._meteo.comando), ("aiuto", lambda t: TESTO_AIUTO_TELEFONO if e_richiesta_aiuto(t) else None),
                     ("resoconto", lambda t: self._resoconto.testo_chat() if e_richiesta_resoconto(t) else None), ("calcolo", calcola)],
            registro=reg, domini_casa=lambda: DOMINI_ESTESI if self._telefono.estesi() else DOMINI_BASE)
        self._chat_tel = Chat(MEMORIA_DIR / "chat_telefono.json", Config.OPENAI_API_KEY, istruzioni_extra=lambda: self._settings.get().get("pers", ""),
                              strumenti=letture_tel + self._casa.strumenti_chat(), memoria=self._memoria, modello=self._modelli.chat, comandi=self._servizi_tel.comando_locale,
                              registro=self._registro.scrivi, apre_programmi=False, comandi_locali=COMANDI_TELEFONO, titoli_ai=Config.TITOLI_AI, nota_ambito=NOTA_TELEFONO,
                              avviso_non_fatto=AVVISO_TELEFONO_NON_FATTO, avviso_non_eseguito=AVVISO_TELEFONO_NON_ESEGUITO)
        self._servizi_tel.collega_chat(self._chat_tel)
        self._telefono_ab = Abbinamenti(BASE_DIR / "config" / "telefoni.json")
        porta_tel = _numero(Config.TELEFONO_PORTA, int, PORTA_TELEFONO)
        porta_tel = porta_tel if 1024 <= porta_tel <= 65535 and porta_tel != _numero(Config.PORTA_ISTANZA, int, PORTA_PREDEFINITA) else PORTA_TELEFONO
        https_tel = _numero(Config.TELEFONO_HTTPS_PORTA, int, PORTA_HTTPS_PREDEFINITA)
        self._telefono = Telefono(MEMORIA_DIR / "telefono.json", self._telefono_ab,
                                  lambda porta: ServerTelefono(porta, self._telefono_ab, self._servizi_tel.dizionario(), PERCORSI.risorse / "ui" / "telefono",
                                                               identita_richiesta=Config.TELEFONO_IDENTITA, host_extra=[h.strip().lower() for h in Config.TELEFONO_HOST.split(",") if h.strip()],
                                                               su_abbinato=lambda nome: self._telefono.nuovo_abbinamento(nome), versione=VERSIONE),
                                  Tailscale(porta_https=https_tel if https_tel in (443, 8443, 10000) else PORTA_HTTPS_PREDEFINITA), porta=porta_tel,
                                  bloccato=not Config.TELEFONO, registro=reg, avviso=self._avvisi.aggiungi)
        self._monitor.registra("Modulo Chat", self._chat.pronto)
        self._monitor.registra("Workflow n8n", self._n8n.pronto)
        self._monitor.registra("Modulo Email", self._gmail.pronto)
        self._monitor.registra("Modulo Finanze", self._finanze.pronto)
        self._monitor.registra("Modulo Agenda", self._agenda.pronto)
        self._monitor.registra("Modulo Memoria", self._memoria.pronto if self._memoria else (lambda: False))
        self._monitor.registra("Vista schermo", self._vista.pronto)
        self._monitor.registra("Voce", self._voce.pronto)
        if self._programmi:
            self._monitor.registra("Programmi", self._programmi.pronto)
            self._programmi.avvia()          # legge i programmi installati in secondo piano e li tiene aggiornati
        self._monitor.registra("Promemoria", self._promemoria.pronto)
        self._monitor.registra("Home Assistant", self._casa.pronto, facoltativo=True)
        self._monitor.registra("Avvisi", self._avvisi.pronto)
        self._monitor.registra("Backup", self._backup.pronto)
        self._monitor.registra("Cerca file", self._cerca_file.pronto)
        self._monitor.registra("Accesso dal telefono", self._telefono.pronto, facoltativo=True)
        if self._riconoscitore.installato() and Config.RISVEGLIO:
            # conta come «sistema» solo se il programma di riconoscimento e' installato e il risveglio e' voluto (spento per scelta = non e' un guasto)
            self._monitor.registra("Risveglio a voce", lambda: (not self._risveglio.voluto()) or self._risveglio.pronto())
        self._stato = Stato(BASE_DIR, BASE_DIR / "logs", VERSIONE, monitor=self._monitor, modelli=self._modelli, sessioni=self._sessioni,
                            chiavi=lambda: {"OpenAI": bool(Config.OPENAI_API_KEY), "Google (voce)": bool(Config.GOOGLE_TTS_API_KEY), "n8n (parola d'ordine)": bool(Config.N8N_TOKEN)},
                            cartelle=[("Programma", PERCORSI.programma), ("Dati e memoria", MEMORIA_DIR), ("Registri", BASE_DIR / "logs")],
                            crash_precedente=lambda: registro_errori.CRASH_PRECEDENTE)
        # avvio con Windows (si sceglie dalle Impostazioni) e icona vicino all'orologio (facoltativa: serve la libreria pystray)
        self._avvio = AvvioWindows(BASE_DIR, registro=self._registro.scrivi, avvio_installato=PERCORSI.avvio if PERCORSI.installato else None)
        # aggiornamento automatico (solo col programma installato; non installa mai senza la Conferma di Lorenzo)
        imp = impostazioni_aggiornamenti()
        self._aggiorna = Aggiornamenti(PERCORSI, VERSIONE, repo=imp["repo"], token=imp["token"], scadenza_token=imp["scadenza"], automatico=imp["automatico"],
                                       acceso=imp["acceso"], cartella_memoria=MEMORIA_DIR, chiudi_programma=self._spegni_programma, registro=self._registro.scrivi)
        self._icona = IconaVassoio(UI_DIR / "clef.png", {"apri": self._icona_apri, "riposo": self._icona_riposo, "log": self._icona_log, "esci": self._icona_esci},
                                   riposo_possibile=lambda: self._modo_buonanotte() == "riposo")
        self._icona_livello, self._icona_testo = "ok", ""
        self._stato_breve = {"livello": "ok", "titolo": "", "quando": None, "da_controllare": 0}
        if self._icona_voluta():
            r_icona = self._icona.avvia()
            if not r_icona["ok"]:
                log.info("Icona vicino all'orologio non attiva: %s", r_icona["errore"])
        threading.Thread(target=self._ciclo_stato, daemon=True, name="clef-stato").start()
        self._aggiorna.avvia()
        self._telefono.avvia()           # solo se Lorenzo l'aveva acceso (di partenza e' spento)
        threading.Thread(target=self._avvio_servizi_pc, daemon=True, name="clef-servizi-pc").start()      # tiene aggiornati il puntino nel menu della pagina e quello sull'icona
        r_ris = self._risveglio.avvia()
        if not r_ris["ok"]:
            log.info("Risveglio a voce non acceso: %s", str(r_ris.get("errore", ""))[:160])
        # il tasto del microfono: un tasto della tastiera (scelto dalle Impostazioni) accende e spegne la conversazione a voce da qualunque programma
        self._tasto = TastoGlobale(self._tasto_premuto, TASTO_FILE, registro=self._registro.scrivi)
        r_tasto = self._tasto.avvia()
        if not r_tasto.get("ok"):
            log.info("Tasto del microfono non attivo: %s", str(r_tasto.get("errore", ""))[:160])
        for modulo in (self._promemoria, self._avvisi, self._backup, self._cerca_file, self._budget):
            modulo.avvia()           # ciascuno ha il suo ciclo in secondo piano, con un'attesa iniziale: non rallentano l'apertura
        self._gmail.precarica()      # legge posta, finanze e agenda in secondo piano: aprire le schermate sara' subito pronto
        self._finanze.precarica()
        self._agenda.precarica()
        if self._memoria:       # le chat scritte prima della memoria entrano in memoria in secondo piano
            threading.Thread(target=lambda: self._memoria.sincronizza_chat(self._chat.lista()), daemon=True).start()
        log.info("Moduli collegati: chat, monitoraggio, impostazioni, n8n, email, finanze, agenda, memoria, vista schermo, voce, programmi, risveglio, resoconto, tasto del microfono, "
                 "promemoria, avvisi, backup, comandi del PC, ricerca file, meteo, studio, bozze di mail, budget (modello %s, trascrizione %s)",
                 self._modelli.chat(), self._modelli.trascrizione())

    # ---- icona vicino all'orologio ----
    def _icona_voluta(self):
        v = self._settings.get().get("icona")
        return Config.ICONA and (v is not False)

    def _in_thread(self, f, nome):
        # le voci del menu dell'icona girano nel thread dell'icona: quello che dura (resoconto, buonanotte) va fatto altrove
        threading.Thread(target=f, daemon=True, name=nome).start()

    def _icona_apri(self): self._in_thread(self._apri_da_icona, "clef-icona-apri")
    def _icona_riposo(self): self._in_thread(lambda: self._riposa(parla=False), "clef-icona-riposo")
    def _icona_log(self): self._stato.apri_cartella_log()
    def _icona_esci(self): self._in_thread(self._spegni_programma, "clef-icona-esci")

    def _avvio_servizi_pc(self):
        """Col programma installato non c'e' piu' CLEF.bat: Docker Desktop (serve a n8n) lo accende C.L.E.F.; la voce di avvio vecchia si sposta sul programma nuovo."""
        try:
            r = self._avvio.migra_voce_vecchia()
            if r.get("fatto"):
                log.info("Voce di avvio con Windows spostata sul programma installato")
        except Exception as e:
            log.info("Avvio con Windows non controllato (%s)", type(e).__name__)
        try:
            r = DockerDesktop(voluto=docker_voluto()).avvia_se_serve()
            log.info("Docker Desktop: %s", r["esito"])
        except Exception as e:
            log.info("Docker Desktop non controllato (%s)", type(e).__name__)

    def _icona_aggiorna(self):
        try:
            self._icona_aggiorna_ora()
        except Exception as e:
            log.info("Icona non aggiornata (%s)", type(e).__name__)

    def _icona_aggiorna_ora(self):
        titolo = "C.L.E.F." + (" — a riposo, in ascolto" if self._riposo else "") + (f" — {self._icona_testo.lower()}" if self._icona_testo and self._icona_livello != "ok" else "")
        self._icona.aggiorna(self._icona_livello, titolo, self._icona_testo or "tutto a posto")

    def _stato_aggiorna(self, r):
        """Ricorda l'ultimo livello dello stato (tutto a posto / da controllare / problema): lo usano il puntino nel menu della pagina e l'icona."""
        self._stato_breve = {"livello": r["livello"], "titolo": r["titolo"], "quando": r["generato"], "da_controllare": len(r["da_controllare"])}
        self._icona_livello, self._icona_testo = r["livello"], r["titolo"]
        if self._icona.attiva():
            self._icona_aggiorna()

    def _ciclo_stato(self):
        """Ogni cinque minuti rilegge lo stato (lo stesso della schermata Stato). Prima attende un poco, per non rallentare l'apertura."""
        time.sleep(45)
        while True:
            try:
                self._stato_aggiorna(self._stato.riepilogo())
            except Exception as e:
                log.info("Stato non aggiornato (%s)", type(e).__name__)
            time.sleep(300)

    def _set_window(self, window, nascosta=False):
        self._window = window
        self._riposo = bool(nascosta)
        self._icona_aggiorna()
        if nascosta:
            threading.Thread(target=self._guardia_riposo, daemon=True, name="clef-guardia-riposo").start()

    def _comando_locale(self, testo):
        """Messaggi che il programma esegue da solo, senza OpenAI. Ordine: se c'e' un'interrogazione in corso la frase e' la risposta; poi i comandi della vista
        schermo, i promemoria, i comandi del PC, la ricerca dei file, il backup, il meteo, il budget, lo studio, «apri <programma>», «cosa sai fare», infine
        «dammi il resoconto» (e «buongiorno Clef», scritto o detto durante una conversazione a voce: e' la stessa cosa che fa il risveglio) e i conti
        («fai 85,90+2573,62», «quanto fa 12 per 5»): li fa il programma, in modo esatto, e la risposta e' sempre in testo semplice.
        Se un modulo ha un guasto il comando passa al successivo (e alla fine alla chat): un errore non deve fermare tutto il resto."""
        passi = []
        if self._studio is not None and self._studio.in_corso():
            passi.append(("studio", self._studio.comando))
        passi += [("vista", self._vista.comando), ("promemoria", self._promemoria.comando), ("pc", self._pc.comando), ("casa", self._casa.comando), ("file", self._cerca_file.comando),
                  ("backup", lambda t: comando_backup(self._backup, t)), ("meteo", self._meteo.comando), ("budget", self._budget.comando)]
        if self._studio is not None:
            passi.append(("studio", self._studio.comando))
        if self._programmi is not None:
            passi.append(("programmi", self._programmi.comando))
        passi.append(("aiuto", lambda t: TESTO_AIUTO if e_richiesta_aiuto(t) else None))
        passi.append(("resoconto", lambda t: self._resoconto.testo_chat() if (e_richiesta_resoconto(t) or riconosci_saluto(t, True, self._nomi_extra()) == "buongiorno") else None))
        passi.append(("calcolo", calcola))
        for nome, f in passi:
            try:
                r = f(testo)
            except Exception as e:
                # niente testo dell'errore: potrebbe contenere cio' che Lorenzo ha scritto. Il tipo e il punto del programma bastano per trovare il guasto
                tb = traceback.extract_tb(e.__traceback__)[-1] if e.__traceback__ else None
                log.error("Comando locale «%s» non riuscito (%s, %s)", nome, type(e).__name__, f"{Path(tb.filename).name}:{tb.lineno}" if tb else "?")
                continue
            if r is not None:
                return r
        return None

    # ---- avvisi, promemoria e budget: cosa succede quando scattano ----
    def _avvisi_voluti(self):
        v = self._settings.get().get("avvisi")
        return v if isinstance(v, bool) else True

    def _avvisi_voce_voluta(self):
        v = self._settings.get().get("avvisi_voce")
        return v if isinstance(v, bool) else True

    def _parla_avviso(self, testo, suono=False):
        """Lo dice a voce se la voce e' libera e Lorenzo la vuole; altrimenti, se 'suono', un breve segnale (una sveglia non deve passare in silenzio). -> True se parlato."""
        parlato = False
        if self._avvisi_voce_voluta():
            try:
                parlato = bool(self._voce.parla(testo).get("ok"))
            except Exception as e:
                log.warning("Avviso non letto a voce (%s)", type(e).__name__)
        if not parlato and suono:
            try:
                segnale("avviso")
            except Exception:
                pass
        return parlato

    def _promemoria_scattato(self, p):
        """Un promemoria, un timer o una sveglia e' scaduto (in un thread a parte). Resta sullo schermo finche' Lorenzo non lo chiude; se la finestra e' nascosta
        (C.L.E.F. a riposo) lo senti comunque a voce o con un segnale."""
        try:
            self._avvisi.aggiungi(p["tipo"], self._promemoria.frase_schermo(p), TITOLI_PROMEMORIA.get(p["tipo"], "Promemoria"), persistente=True)
        except Exception as e:
            log.error("Promemoria scattato ma non mostrato (%s)", type(e).__name__)
        self._parla_avviso(self._promemoria.frase_voce(p), suono=True)

    def _avviso_nuovo(self, a):
        """Un avviso proattivo dell'agenda o della posta: a voce solo gli appuntamenti (le mail le scrive un estraneo: restano sullo schermo)."""
        if a.get("tipo") == "evento":
            self._parla_avviso(a.get("testo", ""), suono=True)

    def _budget_avviso(self, tipo, testo, titolo, persistente):
        self._avvisi.aggiungi(tipo, testo, titolo, persistente)
        if tipo == "budget":
            self._parla_avviso(testo)

    def _budget_presto(self):
        """Dopo una spesa registrata o corretta: ricontrolla subito i budget (i dati sono gia' aggiornati in memoria)."""
        threading.Thread(target=self._budget.controlla, daemon=True, name="clef-budget-subito").start()

    def _registro_chat(self, tipo, testo, ok=True):
        self._registro.scrivi(tipo, testo, ok)
        if tipo == "azione" and ok:
            self._budget_presto()

    def _scegli_cartella(self):
        w = self._window
        if w is None:
            return None
        try:
            r = w.create_file_dialog(_cartella_dialogo())
        except Exception as e:
            log.warning("Selettore di cartelle non aperto (%s)", type(e).__name__)
            return None
        return str(r[0]) if r else None

    # ==========================================
    # METODI PUBBLICI (ESPOSTI ALL'INTERFACCIA HTML)
    # ==========================================

    # --- Chat (modules/chat_module.py) ---
    def list_chats(self): return self._chat.lista()
    def new_chat(self): return self._chat.nuova()
    def rename_chat(self, chat_id, titolo): return self._chat.rinomina(chat_id, titolo)
    def delete_chat(self, chat_id): return self._chat.elimina(chat_id)
    def send_message(self, chat_id, testo): return self._chat.invia(chat_id, testo)
    def confirm_action(self, chat_id, proposta_id): return self._chat.conferma(chat_id, proposta_id)
    def cancel_action(self, chat_id, proposta_id): return self._chat.annulla(chat_id, proposta_id)

    def attach_file(self, chat_id=None):
        if not self._window:
            return []
        percorsi = self._window.create_file_dialog(webview.OPEN_DIALOG, allow_multiple=True)
        percorsi = list(percorsi or [])
        nomi = self._chat.aggiungi_allegati(percorsi)
        if len(nomi) < len(percorsi):          # qualche file non si e' potuto allegare: la pagina lo dice (non resta in silenzio)
            return {"nomi": nomi, "errore": "Non sono riuscito ad allegare " + ("il file" if len(percorsi) - len(nomi) == 1 else f"{len(percorsi) - len(nomi)} file")
                    + ": si allegano testo, PDF e foto (png, jpg, webp), fino a 4 foto e 25 MB ciascuno."}
        return nomi

    # --- Monitoraggio (modules/monitor_module.py) ---
    def get_system_status(self): return self._monitor.stato()

    # --- Impostazioni (core/settings.py, salvate in config/settings.json) ---
    def get_settings(self): return self._settings.get()
    def save_settings(self, settings):
        # i modelli di OpenAI si cambiano solo con la prova (usa_modello): dalla schermata Impostazioni non passano
        if isinstance(settings, dict):
            settings = {k: v for k, v in settings.items() if k not in CHIAVI_MODELLO}
        return self._settings.salva(settings)

    # --- Avvio con Windows e icona vicino all'orologio (modules/avvio_module.py, modules/icona_module.py) ---
    def get_avvio(self): return self._avvio.stato()
    def set_avvio(self, attivo, modo="riposo"): return self._avvio.imposta(attivo, modo)
    def get_icona(self):
        ok, perche = self._icona.disponibile()
        return {"voluta": self._icona_voluta(), "attiva": self._icona.attiva(), "disponibile": ok, "problema": perche or self._icona.errore,
                "bloccata": not Config.ICONA}
    def set_icona(self, voluta):
        if voluta is not True and voluta is not False:
            return dict(self.get_icona(), ok=False)
        self._settings.salva({"icona": voluta})
        if voluta and Config.ICONA and not self._icona.attiva():
            if self._icona.avvia()["ok"]:
                self._icona_aggiorna()
        elif not voluta:
            self._icona.ferma()
        return dict(self.get_icona(), ok=True)

    # --- Stato di C.L.E.F. (modules/stato_module.py): cosa funziona, cosa no e perche' ---
    def get_stato(self):
        r = self._stato.riepilogo()
        try:
            self._stato_aggiorna(r)
        except Exception as e:
            log.info("Stato non ricordato (%s)", type(e).__name__)
        return r
    def get_stato_breve(self):
        r = dict(self._stato_breve)
        r["aggiornamento"] = self._aggiorna.da_vedere()          # c'e' una versione nuova (o il permesso di GitHub sta per scadere): pallino sull'ingranaggio
        return r

    # --- Telefono (modules/telefono_module.py, telefono_server.py, telefono_servizi.py): accesso da Android tramite Tailscale. Spento di partenza ---
    def get_telefono(self):
        """Tutto quello che serve alla scheda Telefono delle Impostazioni: interruttore, Tailscale, indirizzo, codice in corso, telefoni abbinati."""
        try:
            return self._telefono.stato()
        except Exception as e:
            log.error("Stato del telefono non letto (%s)", type(e).__name__)
            return {"errore": "Non riesco a leggere lo stato dell'accesso dal telefono."}
    def set_telefono(self, opzioni):
        """opzioni: {"attivo": True/False} (interruttore) e/o {"estesi": True/False} (permetti anche serrature, cancelli, garage e tapparelle)."""
        if not isinstance(opzioni, dict):
            return {"ok": False, "errore": "Richiesta non valida."}
        r = {"ok": True}
        if "attivo" in opzioni:
            r = self._telefono.imposta(opzioni.get("attivo") is True)
        if r.get("ok") and "estesi" in opzioni:
            r = self._telefono.imposta_estesi(opzioni.get("estesi") is True)
        return r
    def nuovo_codice_telefono(self): return self._telefono.nuovo_codice()
    def revoca_telefono(self, id_telefono): return self._telefono.revoca(str(id_telefono))
    def revoca_telefoni(self): return self._telefono.revoca_tutti()
    def tailscale_telefono(self, azione, confermato=False):
        """«Rendi raggiungibile dal telefono» (azione 'attiva') o «Smetti» ('spegni'). Cambia come il PC e' raggiungibile: serve il «Sì» (confermato=True)."""
        return self._telefono.tailscale(azione, confermato is True)

    # --- Aggiornamenti (modules/aggiorna_module.py): controllo in secondo plano; si installa SOLO con la Conferma di Lorenzo ---
    def get_aggiornamenti(self): return self._aggiorna.stato()
    def controlla_aggiornamenti(self): return self._aggiorna.controlla()
    def installa_aggiornamento(self, confermato=False): return self._aggiorna.installa(confermato is True)
    def get_rapporto(self): return {"testo": self._stato.rapporto()}
    def open_logs_folder(self): return self._stato.apri_cartella_log()

    # --- Modelli di OpenAI (modules/modello_module.py): date di ritiro, prova e cambio sicuro ---
    def get_modelli(self): return self._modelli.stato()
    def prova_modello(self, tipo, modello): return self._modelli.prova(tipo, modello)
    def usa_modello(self, tipo, modello): return self._modelli.prova_e_usa(tipo, modello)
    def torna_modello_precedente(self, tipo): return self._modelli.torna_indietro(tipo)

    # --- Posta (modules/gmail_module.py, tramite n8n) ---
    def get_emails(self): return self._gmail.email()
    def summarize_email(self, account, mail): return self._gmail.sintesi(account, mail)

    # --- Finanze (modules/finance_module.py, tramite n8n) ---
    def get_balance(self): return self._finanze.bilancio()

    # --- Agenda (modules/calendar_module.py, tramite n8n) ---
    def get_agenda(self): return self._agenda.agenda()
    def get_agenda_mese(self, anno, mese): return self._agenda.mese(anno, mese)

    # --- Memoria (modules/memory_module.py): documenti per materia e ricordi della chat ---
    def get_memory(self):
        return self._memoria.stato() if self._memoria else {"errore": "La memoria non è partita: controlla il terminale Python."}
    def update_memory(self):
        return self._memoria.aggiorna() if self._memoria else {"ok": False, "errore": "La memoria non è partita: controlla il terminale Python."}
    def open_knowledge_folder(self):
        return self._memoria.apri_cartella() if self._memoria else {"ok": False, "errore": "La memoria non è partita: controlla il terminale Python."}

    # --- Grafo (modules/graph_module.py): materie, cose dette in chat, consigli di C.L.E.F. ed economia, collegati dal programma ---
    def get_graph(self):
        return self._grafo.costruisci() if self._grafo else {"errore": "La memoria non è partita: controlla il terminale Python."}
    def forget_memory(self, ricordo_id):
        if not self._memoria:
            return {"ok": False, "errore": "La memoria non è partita: controlla il terminale Python."}
        r = self._memoria.dimentica_ricordo(ricordo_id)
        if isinstance(r, dict) and r.get("ok"):
            self._registro.scrivi("memoria", "Ho dimenticato un ricordo, come hai chiesto.", True)
        return r

    # --- Registro delle azioni (modules/registro_module.py) ---
    def get_actions(self, limite=40):
        return {"voci": self._registro.ultimi(limite), "file": str(MEMORIA_DIR / "azioni.jsonl")}

    # --- Casa (modules/casa_module.py): Home Assistant. Indirizzo e chiave sono nel file .env e NON passano mai dalla pagina ---
    def get_casa(self, forza=False):
        """Tutto quello che serve alla schermata Casa: il collegamento, i dispositivi scelti con il loro stato."""
        forza = forza is True
        col = self._casa.collegamento(forza=forza)
        fid = self._casa.fiducia()
        cert = col.get("certificato") if isinstance(col.get("certificato"), dict) else None
        r = {"configurato": self._casa.configurato(), "collegato": bool(col["ok"]), "errore": col["errore"], "tipo_errore": col["tipo"], "versione": col["versione"],
             "nome": col["nome"], "dispositivi": [], "errore_stati": "",
             "certificato": {"impronta": cert.get("impronta", ""), "host": cert.get("host", "")} if cert else None,
             "fiducia": {"impronta": fid["sha256"], "host": fid["host"]} if fid else None}
        if r["collegato"] or self._casa.dispositivi():
            s = self._casa.stato_casa(forza=forza)
            r["dispositivi"], r["errore_stati"] = s["dispositivi"], s["errore"]
        return r
    def get_casa_disponibili(self):
        try:
            return {"ok": True, **self._casa.elenco_disponibili()}
        except Exception as e:
            from modules.casa_module import CasaErrore
            if isinstance(e, CasaErrore):
                return {"ok": False, "errore": str(e), "voci": [], "nascosti": 0}
            log.error("Elenco dei dispositivi di Home Assistant non letto (%s)", type(e).__name__)
            return {"ok": False, "errore": "Non riesco a leggere l'elenco di Home Assistant.", "voci": [], "nascosti": 0}
    def casa_fidati(self, impronta):
        """«Mi fido di questo certificato»: l'impronta e' quella che la pagina ha mostrato; C.L.E.F. la confronta con quella vera del momento."""
        try:
            return self._casa.fidati(impronta if isinstance(impronta, str) else "")
        except Exception as e:
            log.error("Certificato di Home Assistant non accettato (%s)", type(e).__name__)
            return {"ok": False, "errore": "Non sono riuscito a controllare il certificato (errore interno): controlla il registro."}
    def casa_non_fidarti(self):
        try:
            return self._casa.non_fidarti()
        except Exception as e:
            log.error("Fiducia nel certificato non tolta (%s)", type(e).__name__)
            return {"ok": False, "errore": "Non sono riuscito a togliere la fiducia (errore interno)."}
    def casa_scegli(self, entita, nome=None, conferma=None):
        r = self._casa.scegli(entita, nome if isinstance(nome, str) else None, conferma if isinstance(conferma, bool) else None)
        if r.get("ok"):
            self._registro.scrivi("casa", f"Dispositivo di casa scelto o modificato: «{str(nome or entita)[:60]}».", True)
        return r
    def casa_togli(self, entita):
        r = self._casa.togli(entita)
        if r.get("ok"):
            self._registro.scrivi("casa", f"Dispositivo di casa tolto dall'elenco: {str(entita)[:60]}.", True)
        return r
    def casa_azione(self, entita, azione, valore=None, confermato=False):
        """Un comando dai pulsanti della schermata Casa. Luci e prese subito; il resto solo dopo il clic su «Sì» (confermato=True)."""
        try:
            return self._casa.azione(str(entita), str(azione), valore, confermato is True)
        except Exception as e:
            log.error("Comando di casa non riuscito (%s)", type(e).__name__)
            return {"ok": False, "testo": "Non sono riuscito a mandare il comando (errore interno): controlla il registro."}

    # --- Programmi (modules/programmi_module.py): i programmi installati sul PC, che C.L.E.F. apre su richiesta ---
    def get_programs(self):
        if self._programmi is None:
            return {"attivo": False, "n": 0, "esclusi": 0, "aggiornato": None, "in_corso": False, "errore": None, "voci": []}
        st = self._programmi.stato()
        st["attivo"], st["voci"] = True, self._programmi.elenco()
        return st
    def refresh_programs(self):
        if self._programmi is None:
            return {"ok": False, "errore": PROGRAMMI_SPENTI}
        r = self._programmi.aggiorna("schermata Programmi")
        self._registro.scrivi("programma", f"Elenco dei programmi riletto ({r['n']} trovati)." if r["ok"] else "Rilettura dei programmi non riuscita.", r["ok"])
        return r
    def open_program(self, nome):
        if self._programmi is None:
            return {"ok": False, "esito": "spento", "testo": PROGRAMMI_SPENTI}
        return self._programmi.apri(nome, da="schermata Programmi")
    def set_program_pinned(self, nome, fissato):
        if self._programmi is None:
            return {"ok": False, "errore": PROGRAMMI_SPENTI}
        return self._programmi.fissa(nome, fissato)
    def set_program_excluded(self, nome, escluso):
        if self._programmi is None:
            return {"ok": False, "errore": PROGRAMMI_SPENTI}
        r = self._programmi.escludi(nome, escluso)
        if r.get("ok"):
            self._registro.scrivi("programma", f"{'Escluso' if escluso else 'Riammesso'} il programma «{nome}» (schermata Programmi).", True)
        return r

    # --- Avvisi e promemoria (modules/avvisi_module.py, modules/promemoria_module.py) ---
    def get_notices(self):
        """Gli avvisi da mostrare (promemoria scaduti, appuntamenti vicini, mail nuove, budget...). La pagina li chiede ogni pochi secondi e poi li conferma."""
        return {"avvisi": self._avvisi.in_attesa()}
    def ack_notices(self, ids):
        return self._avvisi.conferma(ids)
    def get_reminders(self):
        return self._promemoria.stato()
    def delete_reminder(self, id_voce):
        if not isinstance(id_voce, str):
            return {"ok": False, "errore": "Promemoria non valido."}
        return self._promemoria.elimina(id_voce)
    def snooze_reminder(self, minuti=10):
        """Il pulsante «Rimanda 10 minuti» di un promemoria scattato."""
        if isinstance(minuti, bool) or not isinstance(minuti, (int, float)) or not 1 <= minuti <= 240:
            return {"ok": False, "testo": "Minuti non validi."}
        return self._promemoria.rimanda_ultimo(minuti * 60)

    # --- Backup (modules/backup_module.py) ---
    def get_backup(self):
        st = self._backup.stato()
        st["ripristino"] = self._backup.ripristino_in_sospeso() is not None
        return st
    def run_backup(self):
        """Il pulsante «Fai il backup adesso»."""
        return self._backup.fai_backup("pulsante")
    def set_backup(self, opzioni):
        """opzioni: {"attivo": bool, "includi_chiavi": bool}. Le chiavi (file .env) entrano nella copia solo se Lorenzo lo sceglie."""
        if not isinstance(opzioni, dict):
            return {"ok": False, "errore": "Opzioni non valide."}
        return self._backup.imposta(opzioni.get("attivo"), opzioni.get("includi_chiavi"))
    def add_backup_folder(self):
        percorso = self._scegli_cartella()
        if not percorso:
            return {"ok": False, "annullato": True}
        return self._backup.aggiungi_cartella(percorso)
    def remove_backup_folder(self, percorso):
        if not isinstance(percorso, str):
            return {"ok": False, "errore": "Cartella non valida."}
        return self._backup.togli_cartella(percorso)
    def prepare_restore(self, nome, cartella=None):
        """Sceglie la copia da rimettere: parte alla prossima apertura di C.L.E.F."""
        if not isinstance(nome, str) or (cartella is not None and not isinstance(cartella, str)):
            return {"ok": False, "testo": "Copia non valida."}
        return self._backup.prepara_ripristino(nome, cartella)
    def cancel_restore(self):
        return self._backup.annulla_ripristino()

    # --- Ricerca dei file (modules/file_module.py): cartelle in cui C.L.E.F. cerca; la ricerca si fa in chat («cerca il file della tesi») ---
    def get_file_folders(self):
        return self._cerca_file.stato()
    def add_file_folder(self):
        percorso = self._scegli_cartella()
        if not percorso:
            return {"ok": False, "annullato": True}
        return self._cerca_file.aggiungi_cartella(percorso)
    def remove_file_folder(self, percorso):
        if not isinstance(percorso, str):
            return {"ok": False, "errore": "Cartella non valida."}
        return self._cerca_file.togli_cartella(percorso)

    # --- Bozze di risposta alle mail (modules/bozze_module.py): le prepara, non le invia mai ---
    def draft_reply(self, account, mail, indicazioni=""):
        if not isinstance(account, str) or (indicazioni is not None and not isinstance(indicazioni, str)):
            return {"ok": False, "errore": "Richiesta non valida."}
        return self._bozze.prepara(account, mail, indicazioni or "")
    def open_draft(self, id_bozza, testo):
        return self._bozze.apri_in_gmail(id_bozza, testo)
    def discard_draft(self, id_bozza):
        return self._bozze.scarta(id_bozza)

    # --- Movimenti e budget (modules/finance_module.py, modules/budget_module.py) ---
    def list_movements(self, quanti=30):
        if isinstance(quanti, bool) or not isinstance(quanti, int) or not 1 <= quanti <= 200:
            quanti = 30
        return self._finanze.movimenti_recenti(quanti)
    def edit_movement(self, id_mov, importo=None, data_iso=None):
        """Corregge importo e/o data di un movimento. La pagina chiede conferma a Lorenzo prima di chiamarlo."""
        if not isinstance(id_mov, str):
            return {"ok": False, "testo": "Movimento non valido."}
        r = self._finanze.modifica(id_mov, importo=importo, data_iso=data_iso)
        self._registro.scrivi("azione", "Movimento corretto dalla schermata Bilancio." if r.get("ok") else "Correzione di un movimento non riuscita (schermata Bilancio).", bool(r.get("ok")))
        if r.get("ok"):
            self._budget_presto()
        return r
    def delete_movement(self, id_mov):
        """Cancella un movimento (le due celle del foglio si svuotano; si recupera da «Cronologia delle versioni» di Google Fogli). La pagina chiede conferma prima."""
        if not isinstance(id_mov, str):
            return {"ok": False, "testo": "Movimento non valido."}
        r = self._finanze.cancella(id_mov)
        self._registro.scrivi("azione", "Movimento cancellato dalla schermata Bilancio." if r.get("ok") else "Cancellazione di un movimento non riuscita (schermata Bilancio).", bool(r.get("ok")))
        if r.get("ok"):
            self._budget_presto()
        return r
    def get_budget(self):
        return self._budget.stato_mese()
    def set_budget(self, categoria, importo):
        if not isinstance(categoria, str):
            return {"ok": False, "testo": "Categoria non valida."}
        return self._budget.imposta(categoria, importo)
    def remove_budget(self, categoria):
        if not isinstance(categoria, str):
            return {"ok": False, "testo": "Categoria non valida."}
        return self._budget.togli(categoria)

    # --- Vista schermo (modules/vision_module.py): condivisione continua dello schermo, con finestra mobile ---
    def get_vision(self):
        st = self._vista.stato()
        st["opzioni"], st["finestra_aperta"] = dict(self._vista_opzioni), self._vista_finestra is not None
        return st
    def start_vision(self, schermo=None):
        return self._vista.avvia(schermo)        # la finestra mobile si apre da sola (_vista_avviata)
    def stop_vision(self):
        return self._vista.ferma()
    def get_vision_frame(self, ultimo_id=None, larghezza=480):
        r = self._vista.miniatura(ultimo_id, larghezza)
        r["stato"]["opzioni"], r["stato"]["finestra_aperta"] = dict(self._vista_opzioni), self._vista_finestra is not None
        return r
    def set_vision(self, opzioni):
        """opzioni: {"schermo": 1|2.., "finestra": bool, "includi_proprie": bool}. Cio' che non e' valido viene ignorato."""
        if not isinstance(opzioni, dict):
            return {"ok": False, "errore": "Opzioni non valide."}
        if "schermo" in opzioni:
            r = self._vista.imposta_schermo(opzioni["schermo"])
            if not r["ok"]:
                return r
        for k in ("finestra", "includi_proprie"):
            if isinstance(opzioni.get(k), bool):
                self._vista_opzioni[k] = opzioni[k]
        if self._vista.attiva():
            self._vista_applica_esclusione()
            if "finestra" in opzioni and isinstance(opzioni["finestra"], bool):
                self._apri_finestra_vista() if opzioni["finestra"] else self._chiudi_finestra_vista()
        return {"ok": True}
    def vision_window(self, azione):
        """azione: 'apri', 'chiudi', 'compatta' o 'normale'."""
        if not isinstance(azione, str):
            return {"ok": False, "errore": "Azione non valida."}
        if azione == "apri":
            return self._apri_finestra_vista()
        if azione == "chiudi":
            return self._chiudi_finestra_vista()
        if azione in FINESTRA_VISTA:
            return self._ridimensiona_finestra_vista(*FINESTRA_VISTA[azione])
        return {"ok": False, "errore": "Azione non valida."}

    def _vista_avviata(self):
        self._vista_applica_esclusione()
        if self._vista_opzioni["finestra"]:
            self._apri_finestra_vista()

    def _vista_fermata(self, motivo="utente"):
        self._chiudi_finestra_vista()
        finestra_nella_cattura(TITOLO_PRINCIPALE, True)       # finita la condivisione, la finestra principale torna normale

    def _vista_applica_esclusione(self):
        """La finestra mobile e' sempre fuori dalle fotografie (altrimenti si fotograferebbe all'infinito); quella principale solo se Lorenzo non
        ha scelto di includerla. Su Windows meno recenti non funziona: allora nessun danno, si vede e basta."""
        finestra_nella_cattura(TITOLO_VISTA, False)
        finestra_nella_cattura(TITOLO_PRINCIPALE, self._vista_opzioni["includi_proprie"])

    def _apri_finestra_vista(self):
        with self._vista_lock:
            if self._vista_finestra is not None:
                return {"ok": True}
            try:
                posizione = {}
                try:
                    schermo = webview.screens[0]
                    posizione = {"x": max(0, int(schermo.width) - 450), "y": 70}
                except Exception:
                    pass
                w = webview.create_window(TITOLO_VISTA, url=str(UI_DIR / "clef_vista.html"), js_api=self, width=FINESTRA_VISTA["normale"][0],
                                          height=FINESTRA_VISTA["normale"][1], min_size=(260, 130), on_top=True, resizable=True, background_color="#000000", **posizione)
                try:
                    w.events.closed += self._vista_chiusa
                except Exception:
                    pass
                self._vista_finestra = w
            except Exception as e:
                log.error("Finestra mobile non aperta (%s: %s)", type(e).__name__, str(e)[:200])
                return {"ok": False, "errore": "Non riesco ad aprire la finestra mobile: la condivisione funziona lo stesso, la vedi nella schermata Schermo."}
        threading.Timer(1.5, self._vista_applica_esclusione).start()      # la finestra esiste davvero solo un attimo dopo
        return {"ok": True}

    def _chiudi_finestra_vista(self):
        with self._vista_lock:
            w, self._vista_finestra = self._vista_finestra, None
        if w is not None:
            try:
                w.destroy()
            except Exception as e:
                log.warning("Finestra mobile non chiusa (%s)", type(e).__name__)
        return {"ok": True}

    def _vista_chiusa(self):
        """Lorenzo ha chiuso la finestra mobile: la condivisione continua (la vede nella schermata Schermo) finche' non la ferma."""
        with self._vista_lock:
            self._vista_finestra = None

    def _ridimensiona_finestra_vista(self, larghezza, altezza):
        w = self._vista_finestra
        if w is None:
            return {"ok": False, "errore": "La finestra mobile non è aperta."}
        try:
            w.resize(larghezza, altezza)
        except Exception as e:
            log.warning("Finestra mobile non ridimensionata (%s)", type(e).__name__)
            return {"ok": False, "errore": "Non riesco a ridimensionare la finestra."}
        return {"ok": True}

    def _chiudi_tutto(self):
        """Chiusa la finestra principale: si ferma la condivisione e si chiude anche la finestra mobile (altrimenti il programma resterebbe aperto)."""
        try:
            self._icona.ferma()
        except Exception as e:
            log.warning("Icona non fermata (%s)", type(e).__name__)
        try:
            self._sessioni.chiudi()              # annota che e' stata una chiusura normale (altrimenti la prossima volta la schermata Stato lo segnala)
        except Exception as e:
            log.warning("Chiusura non annotata (%s)", type(e).__name__)
        for modulo in (self._promemoria, self._avvisi, self._backup, self._cerca_file, self._budget, self._aggiorna, self._telefono):
            try:
                modulo.ferma()
            except Exception as e:
                log.warning("Modulo non fermato (%s)", type(e).__name__)
        try:
            self._tasto.chiudi()                 # il tasto torna libero per gli altri programmi
        except Exception as e:
            log.warning("Tasto del microfono non chiuso (%s)", type(e).__name__)
        try:
            self._voce.ferma()
        finally:
            try:
                self._vista.ferma()
            finally:
                try:
                    self._risveglio.ferma()
                finally:
                    if self._programmi:
                        self._programmi.ferma()
                    self._chiudi_finestra_vista()
                    if self._istanza is not None:
                        self._istanza.chiudi()

    # --- Voce (modules/voice_module.py): chat vocale a botta e risposta ---
    def get_voice(self):
        st = self._voce.stato()
        with self._voce_lock:
            chat_id = self._voce_chat
        st["chat_id"] = chat_id
        st["proposta"] = self._chat.proposta_attesa(chat_id) if chat_id else None
        return st
    def start_voice(self):
        with self._voce_lock:
            if not self._voce.attiva():
                self._voce_chat = None       # ogni conversazione a voce e' una chat nuova
        return self._voce.avvia()
    def stop_voice(self):
        return self._voce.ferma()
    def interrupt_voice(self):
        return self._voce.interrompi()
    def set_voice(self, opzioni):
        """opzioni: {"voce": "Charon", "velocita": 0.9}. Cio' che non e' valido viene rifiutato."""
        if not isinstance(opzioni, dict):
            return {"ok": False, "errore": "Opzioni non valide."}
        return self._voce.imposta(opzioni.get("voce"), opzioni.get("velocita"))
    def test_voice(self, voce=None, velocita=None, breve=False):
        """Fa sentire una voce con una frase di prova (breve: solo il nome); torna quando ha finito di parlare."""
        if (voce is not None and not isinstance(voce, str)) or (velocita is not None and (isinstance(velocita, bool) or not isinstance(velocita, (int, float)))):
            return {"ok": False, "errore": "Voce o velocità non valide."}
        return self._voce.prova(voce, velocita, breve is True)

    # --- Tasto del microfono (modules/tasto_module.py) ---
    def get_hotkey(self):
        """Stato per le Impostazioni: se Windows lo permette, quale tasto e' scelto, se e' attivo e l'eventuale motivo per cui non lo e'."""
        return self._tasto.stato()
    def set_hotkey(self, impostazione):
        """impostazione: {"codice": "Pause", "ctrl": false, "alt": false, "maiusc": false, "win": false} (codice = quello della tastiera nella pagina),
        oppure None per togliere il tasto. Si ricorda."""
        if impostazione is None:
            return self._tasto.togli()
        if not isinstance(impostazione, dict):
            return {"ok": False, "errore": "Tasto non valido."}
        return self._tasto.imposta(impostazione.get("codice"), impostazione.get("ctrl") is True, impostazione.get("alt") is True,
                                   impostazione.get("maiusc") is True, impostazione.get("win") is True)
    def pause_hotkey(self, pausa):
        """La pagina lo mette in pausa mentre aspetta il nuovo tasto (altrimenti premere quello vecchio accenderebbe il microfono)."""
        return self._tasto.sospendi(pausa is True)

    def _tasto_premuto(self):
        """Il tasto della tastiera: conversazione accesa -> la spegne; sta parlando (per esempio il resoconto) -> lo zittisce; altrimenti accende il
        microfono, anche se C.L.E.F. e' a riposo (la finestra ricompare). Un bip dice com'e' andata (CLEF_TASTO_SUONO=0 lo toglie)."""
        bip = segnale if Config.TASTO_SUONO else (lambda tipo: None)
        st = self._voce.stato()
        if st["attiva"]:
            self.stop_voice()
            bip("spento")
            return
        if st["fase"] in ("penso", "parlo"):
            self._voce.interrompi()
            bip("spento")
            return
        if self._riposo:
            self._mostra_finestra()
        bip("acceso")                          # il bip prima di aprire il microfono: cosi' non finisce nella registrazione
        r = self.start_voice()
        if not r.get("ok"):
            errore = str(r.get("errore") or "Non riesco ad accendere il microfono.")
            log.info("Tasto del microfono: microfono non acceso (%s)", errore[:120])
            self._voce.segnala(errore)
            bip("errore")

    def _voce_turno(self, testo):
        """Un messaggio detto a voce: passa dalla chat di sempre e torna il testo da leggere. Le conferme restano ai pulsanti."""
        if riconosci_saluto(testo, nome_obbligatorio=False, nomi_extra=self._nomi_extra()) == "buonanotte":
            frase = FRASE_RIPOSO if self._modo_buonanotte() == "riposo" else FRASE_SPEGNIMENTO
            return {"parla": frase, "mostra": frase, "poi": "buonanotte"}         # la conversazione si chiude e C.L.E.F. va a riposo dopo aver parlato
        with self._voce_lock:
            nuova = self._voce_chat is None
            if nuova:
                self._voce_chat = self._chat.nuova("Voce")["id"]
            chat_id = self._voce_chat
        r = self._chat.invia(chat_id, testo, voce=True)
        testo_r = str(r.get("t") or "")
        if testo_r.startswith("Errore OpenAI"):         # il testo tecnico dell'errore si legge a schermo, non a voce
            if nuova:
                self._chat.elimina(chat_id)              # la chat non ha avuto nessuno scambio: non la lascio vuota
                with self._voce_lock:
                    self._voce_chat = None
            return {"parla": RISPOSTA_SENZA_OPENAI, "mostra": testo_r}
        if nuova:
            self._chat.rinomina(chat_id, titolo_voce(testo))
        parla = testo_r
        if isinstance(r.get("proposta"), dict) and r["proposta"].get("stato") == "attesa":
            parla += "\n" + INVITO_CONFERMA_VOCE
        return {"parla": parla, "mostra": testo_r}

    # --- Risveglio a voce e resoconto (modules/wake_module.py, modules/briefing_module.py) ---
    def get_wake(self):
        """Stato per la pagina: il risveglio (ascolto), l'ultimo resoconto e se C.L.E.F. e' a riposo."""
        return {"risveglio": self._risveglio.stato(), "resoconto": self._resoconto.stato(), "riposo": self._riposo, "buonanotte": Config.BUONANOTTE,
                "modello_scelto": self._riconoscitore.modello, "resoconto_auto": self._auto_voluto()}
    def set_wake(self, attivo):
        """Acceso/spento dalle Impostazioni (si ricorda). La pagina legge poi lo stato con get_wake."""
        r = self._risveglio.imposta(attivo)
        if r.get("ok"):
            self._registro.scrivi("voce", "Risveglio a voce " + ("acceso" if attivo else "spento") + " dalle Impostazioni.", True)
        return r
    def set_auto_briefing(self, attivo):
        """Dalle Impostazioni: il resoconto parte da solo quando si apre C.L.E.F. (si ricorda)."""
        if not isinstance(attivo, bool):
            return {"ok": False, "errore": "Valore non valido."}
        try:
            pref = _leggi_json(AVVIO_FILE)
            pref["resoconto_auto"] = attivo
            _scrivi_json(AVVIO_FILE, pref)
        except Exception as e:
            log.error("Scelta del resoconto automatico non salvata (%s)", type(e).__name__)
            return {"ok": False, "errore": "Non riesco a salvare la scelta."}
        self._registro.scrivi("voce", "Resoconto automatico all'apertura " + ("acceso" if attivo else "spento") + " dalle Impostazioni.", True)
        return {"ok": True}
    def _auto_voluto(self):
        v = _leggi_json(AVVIO_FILE).get("resoconto_auto")
        return v if isinstance(v, bool) else bool(Config.RESOCONTO_AUTO)
    def _avvio_automatico(self, ritardo=None):
        """Appena C.L.E.F. si apre con la finestra visibile il resoconto parte da solo, come se si fosse detto «buongiorno Clef».
        Non parte se C.L.E.F. e' a riposo (partito nascosto all'accensione del PC: li si aspetta il saluto) o se e' stato spento dalle Impostazioni."""
        if self._riposo or not self._auto_voluto():
            return False
        time.sleep(AVVIO_RITARDO_S if ritardo is None else ritardo)
        if self._riposo or self._resoconto.in_corso():
            return False
        self._sveglia(mostra=False)
        return True
    def _apri_da_icona(self):
        """Un secondo avvio (CLEF.bat) mentre C.L.E.F. e' gia' acceso: la finestra compare e, se era a riposo, il resoconto parte come all'apertura."""
        era_riposo = self._riposo
        ok = self._mostra_finestra()
        if ok and era_riposo:
            self._avvio_automatico(ritardo=1.0)
        return ok
    def run_briefing(self):
        """Il pulsante «Fammi il resoconto»: lo fa subito (a voce se la voce e' disponibile)."""
        if self._resoconto.in_corso():
            return {"ok": False, "errore": "Il resoconto è già in corso."}
        threading.Thread(target=self._sveglia, kwargs={"mostra": False}, daemon=True, name="clef-resoconto-pulsante").start()
        return {"ok": True}
    def good_night(self):
        """Il pulsante «Buonanotte»: come dirlo a voce."""
        threading.Thread(target=self._riposa, kwargs={"parla": True}, daemon=True, name="clef-buonanotte-pulsante").start()
        return {"ok": True, "modo": self._modo_buonanotte()}

    def _nomi_extra(self):
        return [x.strip() for x in Config.RISVEGLIO_NOMI.split(",") if x.strip()]

    def _rinfresca_per_resoconto(self):
        """Prima del resoconto: ricontrolla n8n adesso e rilegge in secondo piano le schede che dipendono da lui (cosi' non resta un vecchio errore)."""
        self._n8n.controlla_ora()
        self._gmail.precarica()
        self._finanze.precarica()
        self._agenda.precarica()

    def _risveglio_evento(self, tipo):
        """Chiamata dal risveglio (in un thread a parte) quando sente «buongiorno Clef» o «buonanotte Clef»."""
        if tipo == "buongiorno":
            self._sveglia()
        elif tipo == "buonanotte":
            self._riposa(parla=True)

    def _voce_poi(self, poi):
        """Chiamata dalla voce dopo aver letto una risposta che chiedeva un seguito: «buonanotte» detto in conversazione."""
        if poi == "buonanotte":
            threading.Thread(target=self._riposa, kwargs={"parla": False}, daemon=True, name="clef-buonanotte").start()

    def _modo_buonanotte(self):
        """«riposo» (finestra nascosta, resta in ascolto) solo se c'e' qualcuno che sa risvegliarlo; altrimenti «chiudi»: una finestra nascosta senza
        orecchie non si potrebbe piu' riaprire se non rilanciando CLEF.bat."""
        if Config.BUONANOTTE == "chiudi" or not self._risveglio.in_ascolto():
            return "chiudi"
        return "riposo"

    def _sveglia(self, mostra=True):
        """«Buongiorno Clef»: la finestra ricompare e C.L.E.F. saluta e fa il resoconto (a voce, e scritto nella Home). Una volta alla volta."""
        if not self._sveglia_lock.acquire(blocking=False):
            return
        try:
            if mostra:
                self._mostra_finestra()
            self._resoconto.esegui(self._voce.parla)
        except Exception as e:
            log.error("Risveglio: resoconto non riuscito: %s: %s", type(e).__name__, str(e)[:200])
        finally:
            self._sveglia_lock.release()

    def _riposa(self, parla=True):
        """«Buonanotte Clef»: si ferma tutto cio' che e' acceso (conversazione, condivisione dello schermo), saluta e poi o nasconde la finestra
        (restando in ascolto di «buongiorno Clef») o si chiude del tutto."""
        with self._riposo_lock:
            modo = self._modo_buonanotte()
            if self._voce.attiva():
                self._voce.ferma("Buonanotte.")
            if parla:
                r = self._voce.parla(FRASE_RIPOSO if modo == "riposo" else FRASE_SPEGNIMENTO)
                if not r.get("ok"):
                    log.info("Buonanotte detta senza voce: %s", str(r.get("errore", ""))[:120])
            try:
                self._vista.ferma()
            except Exception as e:
                log.warning("Condivisione dello schermo non fermata: %s", type(e).__name__)
            if modo == "chiudi":
                self._registro.scrivi("voce", "Buonanotte: C.L.E.F. si spegne.", True)
                self._spegni_programma()
            elif self._nascondi_finestra():
                self._registro.scrivi("voce", "Buonanotte: C.L.E.F. è a riposo (finestra nascosta, in ascolto di «buongiorno Clef»).", True)
            else:
                self._registro.scrivi("voce", "Buonanotte: non sono riuscito a nascondere la finestra.", False)

    def _nascondi_finestra(self):
        w = self._window
        if w is None:
            return False
        try:
            w.hide()
        except Exception as e:
            log.warning("Finestra non nascosta (%s): provo a ridurla a icona", type(e).__name__)
            try:
                w.minimize()
            except Exception:
                return False
            self._ridotta = True
            return True
        self._riposo = True
        self._icona_aggiorna()
        return True

    def _mostra_finestra(self):
        """Fa comparire la finestra (anche se era nascosta o ridotta a icona) e la porta davanti."""
        w = self._window
        if w is None:
            return False
        try:
            w.show()
        except Exception as e:
            log.warning("Finestra non mostrata: %s", type(e).__name__)
            return False
        if self._ridotta:                  # era stata ridotta a icona (non nascosta): la riporto a grandezza normale
            self._ridotta = False
            try:
                w.restore()
            except Exception:
                pass
        try:
            w.on_top = True          # un attimo in primo piano: Windows non sempre porta davanti da solo una finestra che compare
            w.on_top = False
        except Exception:
            pass
        self._riposo = False
        self._icona_aggiorna()
        return True

    def _spegni_programma(self):
        w = self._window
        if w is not None:
            try:
                w.destroy()
            except Exception as e:
                log.warning("Finestra non chiusa (%s)", type(e).__name__)
        else:
            self._chiudi_tutto()

    def _guardia_riposo(self):
        """Se C.L.E.F. e' partito NASCOSTO (all'accensione del PC) ma il risveglio non riesce a mettersi in ascolto, la finestra ricompare con il motivo
        nella Home: altrimenti resterebbe un programma invisibile che non risponde a nessuno."""
        inizio = time.monotonic()
        while self._riposo:
            st = self._risveglio.stato()
            trascorso = time.monotonic() - inizio
            if st["fase"] in ("ascolto", "pausa"):
                return
            if st["fase"] in ("problema", "spento") or (st["fase"] == "errore" and trascorso > RIPOSO_ATTESA_ERRORE_S) or trascorso > RIPOSO_ATTESA_CARICO_S:
                log.warning("Avvio a riposo: il risveglio non e' in ascolto (%s): mostro la finestra", st["fase"])
                self._mostra_finestra()
                return
            time.sleep(2)

    def _pronto_per_riposo(self):
        """True se ha senso partire con la finestra nascosta: il risveglio e' voluto e puo' funzionare."""
        return self._risveglio.in_grado()


def main():
    # da terminale il debug e' acceso (clic destro -> Ispeziona); CLEF.bat lo spegne con CLEF_DEBUG=0
    debug = os.environ.get("CLEF_DEBUG", "1") != "0"
    ui_path = UI_DIR / "clef_ui.html"
    # una sola copia alla volta: se C.L.E.F. e' gia' acceso (magari nascosto, a riposo) gli chiedo di farsi vedere ed esco
    porta = _numero(Config.PORTA_ISTANZA, int, PORTA_PREDEFINITA)
    istanza = Istanza(porta if 1024 <= porta <= 65535 else PORTA_PREDEFINITA)
    if not istanza.prendi():
        log.info("C.L.E.F. era gia' acceso: gli ho chiesto di mostrarsi")
        return
    api = CLEFApi()
    api._istanza = istanza
    # «CLEF.bat riposo» (usato all'accensione del PC): parte con la finestra nascosta, ma solo se il risveglio puo' davvero ascoltare
    riposo = "riposo" in [a.lower() for a in sys.argv[1:]] or os.environ.get("CLEF_RIPOSO") == "1"
    nascosta = bool(riposo and api._pronto_per_riposo())
    if riposo and not nascosta:
        log.info("Avvio a riposo richiesto ma il risveglio non e' pronto: apro la finestra")
    imposta_id_applicazione()          # Windows: questo e' «C.L.E.F.», non «Python»: il pulsante nella barra non si mescola con altri programmi Python
    window = webview.create_window(TITOLO_PRINCIPALE, url=str(ui_path), js_api=api, width=1280, height=800, resizable=True, background_color="#000000",
                                   hidden=nascosta)
    api._set_window(window, nascosta)
    threading.Thread(target=applica_icona_finestra, args=(TITOLO_PRINCIPALE, UI_DIR / "clef.ico"), daemon=True, name="clef-icona-finestra").start()
    istanza.ascolta(api._apri_da_icona)
    window.events.closed += api._chiudi_tutto
    if not nascosta:        # aperto a mano, con la finestra visibile: il resoconto parte da solo (se non e' stato spento dalle Impostazioni)
        threading.Thread(target=api._avvio_automatico, daemon=True, name="clef-avvio-automatico").start()
    webview.start(debug=debug)
    log.info("C.L.E.F. chiuso")


if __name__ == "__main__":
    main()
