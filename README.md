# 🏠 TrovaCasa Milano Scraper

Scraper automatico per raccogliere URL degli annunci immobiliari di Milano da TrovaCasa.it.

## 📋 Funzionalità

- ✅ **Scraping automatico** quotidiano alle 8:00 UTC
- ✅ **Salvataggio permanente** su GitHub Releases
- ✅ **Esecuzione cloud** gratuita con GitHub Actions
- ✅ **Export CSV** con timestamp
- ✅ **Esecuzione manuale** quando necessario

## 🚀 Come Funziona

1. **GitHub Actions** esegue lo scraper ogni giorno
2. **Scarica** tutte le pagine degli annunci di Milano
3. **Estrae** gli URL degli annunci
4. **Salva** i dati in formato CSV
5. **Crea** un release GitHub con il CSV allegato

## 📊 Accesso ai Dati

I CSV sono disponibili nella sezione **[Releases](../../releases)** di questo repository:

- Ogni giorno viene creato un nuovo release
- Il nome del file include data e ora: `trovacasa_milano_YYYYMMDD_HHMMSS.csv`
- Download diretto del CSV dalla pagina del release

## 🔧 Configurazione

### Esecuzione Manuale

1. Vai su **Actions** → **TrovaCasa Scraper to GitHub Releases**
2. Clicca **"Run workflow"**
3. Specifica il numero di pagine (0 = tutte, default = 5)
4. Clicca **"Run workflow"**

### Modifica Parametri

Per modificare i parametri di default, edita il file `.github/workflows/scraper.yml`:

```yaml
# Per cambiare l'orario di esecuzione (attualmente 8:00 UTC)
schedule:
  - cron: '0 8 * * *'  # Modifica l'ora qui

# Per cambiare il numero di pagine di default
default: '5'  # Cambia questo valore
```

## 📁 Struttura File

```
├── scraper_improved.py      # Script principale di scraping
├── requirements.txt         # Dipendenze Python
├── .github/workflows/
│   └── scraper.yml         # Configurazione GitHub Actions
└── README.md               # Questo file
```

## 🛠️ Tecnologie Utilizzate

- **Python 3.11** - Linguaggio principale
- **aiohttp** - Client HTTP asincrono
- **BeautifulSoup4** - Parsing HTML
- **pandas** - Manipolazione dati e export CSV
- **GitHub Actions** - Automazione CI/CD
- **GitHub Releases** - Storage permanente

## 📈 Monitoraggio

- **Logs dettagliati** disponibili in GitHub Actions
- **Status badge** per monitorare l'ultima esecuzione
- **Release automatici** con statistiche degli annunci trovati

## ⚠️ Note Legali

Questo strumento è creato esclusivamente per scopi educativi e di ricerca. Assicurati di rispettare:

- I termini di servizio di TrovaCasa.it
- Le politiche sui robots.txt
- Le leggi sulla privacy e copyright

## 🔒 Privacy

- Repository **privato** = dati completamente privati
- Repository **pubblico** = releases pubblici ma configurabili
- Nessun dato sensibile salvato nei logs