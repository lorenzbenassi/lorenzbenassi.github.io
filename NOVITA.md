# Novità di C.L.E.F.

Ogni versione ha la sua sezione «## numero». Le righe di quella pubblicata compaiono in Impostazioni → Aggiornamenti, prima del «Sì, aggiorna».

## 2.1.1 — 26 ottobre 2026
- La chat vede le foto: con il «+» puoi allegare png, jpg, webp, gif o bmp e C.L.E.F. le guarda davvero (prima gli arrivava solo una massa di caratteri senza senso). Fino a 4 foto per messaggio; costano pochi millesimi di dollaro l'una.
- I file che C.L.E.F. non sa leggere (programmi, documenti Word) non vengono più mandati come caratteri a caso, e il «+» ti dice quando un file non si è potuto allegare.

## 2.1.0 — 26 ottobre 2026
- Accesso dal telefono Android: chat scritta e a voce, Casa (luci, prese, termostato) e, in sola lettura, agenda, mail e bilancio. È spento finché non lo accendi tu in Impostazioni → Telefono.
- Il telefono parla con il PC solo dentro la tua rete privata Tailscale (gratuita): niente è aperto su Internet. Ogni telefono si abbina con un codice che vale 5 minuti e si scollega dal PC quando vuoi.
- Dal telefono non si comanda il PC e non si scrive in agenda, mail o bilancio. Serrature, cancelli, garage e tapparelle restano bloccati (si possono permettere dalle Impostazioni, con il tuo «Sì»).
- Nuovo capitolo «Telefono» nelle Impostazioni, con la guida passo passo (LEGGIMI_TELEFONO.md).

## 2.0.0 — 26 ottobre 2026
- Primo installatore vero: C.L.E.F. si installa con un solo file (CLEF-win-Setup.exe), senza Python e senza cartelle da copiare a mano.
- Aggiornamenti automatici: C.L.E.F. controlla da solo se c'è una versione nuova e lo segnala con un pallino sull'ingranaggio. Non installa mai niente senza il tuo «Sì».
- I tuoi dati (chiavi, memoria, chat, registri, backup) restano dove sono e non vengono toccati dagli aggiornamenti.
- Docker Desktop lo accende C.L.E.F. stesso quando parte (prima lo faceva CLEF.bat).
- L'avvio con Windows ora lancia direttamente il programma installato.
