import aiohttp
import asyncio
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import os
import logging

# Configurazione logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# URL di partenza
base_url = "https://www.trovacasa.it"
start_url = f"{base_url}/case-in-vendita/milano"

tutti_link_annunci = []

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

async def scarica_pagina(session, url, numero_pagina):
    logger.info(f"📄 Scarico pagina {numero_pagina}: {url}")
    try:
        async with session.get(url, headers=headers, timeout=30) as response:
            if response.status != 200:
                logger.warning(f"⚠️ Errore HTTP {response.status} per pagina {numero_pagina}")
                return None, None

            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")

            # Estrazione link annunci
            link_annunci = []
            annunci = soup.select("a.card__title.js_link_immobile")
            for a in annunci:
                href = a.get("href")
                if href:
                    link_assoluto = base_url + href
                    link_annunci.append(link_assoluto)

            logger.info(f"✅ Trovati {len(link_annunci)} annunci in pagina {numero_pagina}")

            # Link "pagina successiva"
            next_button = soup.select_one("a.pager__link.next")
            next_url = base_url + next_button.get("href") if next_button and next_button.get("href") else None

            return link_annunci, next_url
    except asyncio.TimeoutError:
        logger.error(f"⌛ Timeout per pagina {numero_pagina}")
        return None, None
    except Exception as e:
        logger.error(f"❌ Errore per pagina {numero_pagina}: {e}")
        return None, None

async def main(max_pagine=None):
    """
    max_pagine = None -> scarica tutte le pagine disponibili
    max_pagine = N    -> scarica solo N pagine
    """
    global tutti_link_annunci
    tutti_link_annunci = []  # Reset della lista per esecuzioni multiple
    
    pagina_corrente = start_url
    pagina_numero = 1

    # Timeout per GitHub Actions
    timeout = aiohttp.ClientTimeout(total=60)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        while pagina_corrente:
            link_annunci, pagina_corrente = await scarica_pagina(session, pagina_corrente, pagina_numero)

            if link_annunci:
                tutti_link_annunci.extend(link_annunci)
            else:
                logger.warning(f"⚠️ Nessun annuncio trovato in pagina {pagina_numero}, interruzione")
                break

            pagina_numero += 1
            if max_pagine and pagina_numero > max_pagine:
                logger.info(f"🔄 Raggiunto il limite di {max_pagine} pagine")
                break

            # Pausa per evitare di essere bloccati
            await asyncio.sleep(2)

    # Generazione nome file con timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"url_annunci_milano_{timestamp}.csv"
    
    # Salvataggio risultati
    if tutti_link_annunci:
        df = pd.DataFrame({"url": tutti_link_annunci})
        df.to_csv(filename, index=False, encoding="utf-8")
        
        logger.info(f"✅ Totale annunci trovati: {len(tutti_link_annunci)}")
        logger.info(f"📁 File salvato: {filename}")
        
        # Scrivi il nome del file per GitHub Actions
        with open('csv_filename.txt', 'w') as f:
            f.write(filename)
    else:
        logger.error("❌ Nessun annuncio trovato")
        # Crea comunque un file vuoto per evitare errori nel workflow
        with open(f"url_annunci_milano_{timestamp}_EMPTY.csv", 'w') as f:
            f.write("url\n")
        with open('csv_filename.txt', 'w') as f:
            f.write(f"url_annunci_milano_{timestamp}_EMPTY.csv")

if __name__ == "__main__":
    # Leggi configurazione da variabili d'ambiente
    max_pages = os.getenv('MAX_PAGES', '5')
    max_pages = None if max_pages == '0' else int(max_pages)
    
    logger.info(f"🚀 Avvio scraper con max_pagine={max_pages}")
    
    asyncio.run(main(max_pagine=max_pages))