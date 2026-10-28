# Voltraggio Bot

*LE PAROLE SONO IMPORTANTI!*

Aggiungilo al tuo gruppo Telegram! [@voltraggiobot](https://t.me/voltraggiobot)

## Sì ma... Perché?

Sei stanco dell'abuso delle parole? Non sopporti quando la gente usa a sproposito *voltaggio* e *amperaggio*?

Beh, Jack lo era. E mi ha chiesto di mettere fine a questo sproloquio. E chi sono io per dire di no a Jack?

## Non ho capito

Neanche io.

Però ti assicuro che il bot non traccia nessun utente e nessun messaggio verrà mai salvato. Non ci credi? Controlla i sorgenti!

## Voglio il mio bot

1. Crea un bot con [@BotFather](https://t.me/botfather) e copia il token
2. Copia `settings.json.example` in `data/settings.json`
3. Inserisci il token e il tuo user id nella lista `admins`
4. Avvia il container con `docker compose up -d --build`

La cartella *data* viene montata nel container, quindi le impostazioni e le statistiche sopravvivono quando il container viene ricostruito.

Per avviare il bot senza docker: `uv run voltraggio-bot --settings data/settings.json` (aggiungi `--debug` per i log dettagliati).

### Comandi

- `/start` e `/ping`, per vedere se il bot è vivo
- `/gauss`, per una foto di Gauss
- `/stats`, per sapere quanti pesci sono stati lanciati
- `/reset` e `/stop`, solo per admins

### Sviluppo

```bash
uv sync                # installa il bot e gli strumenti di sviluppo
uv run ruff check      # lint
uv run ruff format     # formattazione
uv run ty check        # type check
uv run pytest --cov    # test
```

## Riconoscimenti

Non possiedo nessun diritto né sulla foto, né sulla gif. Ogni diritto và ai loro rispettivi proprietari.

Il codice è distribuito sotto la licenza Attribuzione-NonCommerciale 4.0 Internazionale (CC BY-NC 4.0), come anche indicato nei sorgenti.
