# 🏠 TrovaCasa Milano Scraper COMPLETO

Scraper automatico avanzato per raccogliere **dati completi** degli annunci immobiliari di Milano da TrovaCasa.it.

## ✨ Novità Versione Completa

- 🔍 **Estrazione dati dettagliati** per ogni annuncio
- 💰 **Prezzo, superficie, locali, bagni**
- 📍 **Indirizzo e titolo completi**
- ⚡ **Classe energetica** 
- 🏷️ **Tag e caratteristiche**
- 📊 **Statistiche avanzate** nei release
- ⏱️ **Monitoraggio temporale** per analisi storiche

## 📊 Dati Estratti

Ogni annuncio include:

| Campo | Descrizione | Esempio |
|-------|-------------|---------|
| `_id` | Codice annuncio | `12345678` |
| `url` | Link all'annuncio | `https://...` |
| `prezzo` | Prezzo dell'immobile | `€ 350.000` |
| `titolo` | Titolo annuncio | `Trilocale in Via Roma` |
| `indirizzo` | Indirizzo | `Via Roma, Milano MI` |
| `superficie_m2` | Superficie in m² | `85` |
| `num_locali` | Numero locali | `3` |
| `num_bagni` | Numero bagni | `2` |
| `classe_ener` | Classe energetica | `C` |
| `tags` | Caratteristiche | `["Balcone", "Ascensore"]` |
| `data_comparsa` | Data rilevazione | `2024-12-13` |

## 🚀 Esecuzione

### Automatica
- **Ogni giorno alle 6:00 UTC** (7:00/8:00 in Italia)
- **Timeout**: 2 ore per completare tutto il processo

### Manuale
1. **Actions** → **TrovaCasa Scraper Completo**
2. **Run workflow**
3. **Scegli numero pagine** (consigliato max 10 per test)
4. **Avvia**

## 📈 Performance

| Scenario | Pagine | Annunci | Tempo Stimato |
|----------|--------|---------|---------------|
| **Test** | 3 | ~150 | 8-12 minuti |
| **Medio** | 10 | ~500 | 20-30 minuti |
| **Completo** | Tutte (~100+) | ~5000+ | 1-2 ore |

## 📥 Download Dati

I CSV sono disponibili nei **[Releases](../../releases)**:
- **Nome**: `trovacasa_milano_completo_TIMESTAMP.csv`
- **Separatore**: Punto e virgola (;)
- **Encoding**: UTF-8
- **Formato**: Pronto per Excel/Google Sheets

## ⚙️ Configurazione

### Parametri Workflow

```yaml
# Orario esecuzione (6:00 UTC)
schedule:
  - cron: '0 6 * * *'

# Timeout massimo (2 ore)
timeout-minutes: 120

# Pagine default per esecuzione manuale
default: '3'
```

### Limiti GitHub Actions
- ✅ **2000 minuti/mese** gratuiti
- ✅ **6 ore max** per job singolo
- ✅ **1 job giornaliero ≈ 30-60 minuti** → circa 30 giorni di margin

## 🔧 Personalizzazioni

### Cambiare Città
```python
# In scraper_completo.py
start_url = f"{base_url}/case-in-vendita/roma"  # Roma invece di Milano
```

### Modificare Concorrenza
```python
MAX_CONCURRENT_REQUESTS = 5  # Più conservativo
MAX_CONCURRENT_REQUESTS = 10  # Più aggressivo
```

### Aggiungere Campi
```python
# Nel metodo estrai_annuncio()
piano = get_value("Piano")
anno_costruzione = get_value("Anno di costruzione")
# Aggiungi ai dati...
```

## 📊 Analisi Dati

Il CSV può essere usato per:
- 📈 **Analisi prezzi** per zona
- 📐 **Correlazione prezzo/superficie**
- 🏘️ **Mappatura geografica**
- 📅 **Trend temporali**
- 🔍 **Filtering avanzato**

## ⚠️ Considerazioni

- **Rate Limiting**: Pause automatiche per evitare blocchi
- **Robustezza**: Gestione timeout ed errori
- **Memoria**: Ottimizzato per GitHub Actions
- **Rispetto del Sito**: User-agent appropriato e ritmi sostenibili

## 🆚 Confronto con Versione Base

| Caratteristica | Base | Completo |
|---------------|------|----------|
| **Dati** | Solo URL | 12+ campi dettagliati |
| **Tempo** | 2-5 min | 20-120 min |
| **File** | ~50KB | ~2-10MB |
| **Analisi** | Limitata | Completa |
| **Uso memoria** | Basso | Medio |

## 🔒 Privacy e Legalità

- ✅ **Solo dati pubblici**
- ✅ **Rispetto robots.txt**
- ✅ **Rate limiting appropriato**
- ✅ **Storage privato** (se repository privato)

---

*🚀 Per la versione base (solo URL), vedi branch `main`*