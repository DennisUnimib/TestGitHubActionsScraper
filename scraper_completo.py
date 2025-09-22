# -*- coding: utf-8 -*-
"""
Scraping completo annunci TrovaCasa Milano - Versione GitHub Actions
"""

import aiohttp
import asyncio
from bs4 import BeautifulSoup
import pandas as pd
import time
from datetime import datetime
import os
import logging

# Configurazione logging per GitHub Actions
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# -----------------------
# Parametri generali
# -----------------------
base_url = "https://www.trovacasa.it"
start_url = f"{base_url}/case-in-vendita/milano"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
MAX_CONCURRENT_REQUESTS = 8  # Ridotto per GitHub Actions
oggi = datetime.today().strftime("%Y-%m-%d")

# -----------------------
# Funzioni
# -----------------------
async def scarica_pagina(session, url, numero_pagina):
    logger.info(f"📄 Scarico pagina {numero_pagina}")
    try:
        async with session.get(url, headers=headers, timeout=30) as response:
            if response.status != 200:
                logger.warning(f"⚠️ Errore HTTP {response.status} per pagina {numero_pagina}")
                return None, None
            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")

            link_annunci = [base_url + a.get("href") for a in soup.select("a.card__title.js_link_immobile") if a.get("href")]

            next_button = soup.select_one("a.pager__link.next")
            next_url = base_url + next_button.get("href") if next_button and next_button.get("href") else None

            logger.info(f"✅ Trovati {len(link_annunci)} annunci in pagina {numero_pagina}")
            return link_annunci, next_url
    except asyncio.TimeoutError:
        logger.error(f"⌛ Timeout per pagina {numero_pagina}")
        return None, None
    except Exception as e:
        logger.error(f"❌ Errore pagina {numero_pagina}: {e}")
        return None, None


async def get_urls(max_pagine=None):
    pagina_corrente = start_url
    pagina_numero = 1
    tutti_link_annunci = []
    start_time = time.time()

    # Timeout più lungo per GitHub Actions
    timeout = aiohttp.ClientTimeout(total=60)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        logger.info(f"🔄 Inizio scaricamento pagine (max: {max_pagine or 'tutte'})")

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

            # Pausa più lunga per GitHub Actions per evitare rate limiting
            await asyncio.sleep(2.5)

    df_urls = pd.DataFrame({"url": tutti_link_annunci})
    logger.info(f"✅ Totale annunci trovati: {len(tutti_link_annunci)}")
    logger.info(f"📄 Pagine scaricate: {pagina_numero - 1}")
    logger.info(f"⏱️ Tempo URLs: {round(time.time() - start_time,2)} sec")
    return df_urls


async def estrai_annuncio(session, url, semaforo, progress_counter):
    async with semaforo:
        try:
            async with session.get(url, headers=headers, timeout=30) as response:
                if response.status != 200:
                    return None
                html = await response.text()
                soup = BeautifulSoup(html, "html.parser")

                prezzo = soup.select_one(".price")
                titolo = soup.select_one(".immobile__title.headingOne")
                indirizzo = soup.select_one(".indirizzo")
                tag_elements = soup.select(".immobileDetails__tagLabel")

                def get_value(label):
                    for dl in soup.select("dl.row"):
                        dt = dl.find("dt", class_="term")
                        if dt and label in dt.text:
                            dd = dl.find("dd", class_="description")
                            if dd:
                                return dd.text.strip()
                    return None

                id_annuncio = get_value("Codice annuncio")
                superficie_raw = get_value("Superficie")
                num_locali_raw = get_value("Numero locali")
                num_bagni_raw = get_value("Numero bagni")
                classe_ener = get_value("Classe energetica")

                superficie = superficie_raw.split()[0].replace('.', '').replace(',', '.') if superficie_raw else None
                num_locali = int(num_locali_raw) if num_locali_raw and num_locali_raw.isdigit() else None
                num_bagni = int(num_bagni_raw) if num_bagni_raw and num_bagni_raw.isdigit() else None

                dati = {
                    "_id": id_annuncio,
                    "url": url,
                    "prezzo": prezzo.get_text(strip=True) if prezzo else "N/A",
                    "titolo": titolo.get_text(strip=True) if titolo else "N/A",
                    "indirizzo": indirizzo.get_text(strip=True) if indirizzo else "N/A",
                    "superficie_m2": superficie,
                    "num_locali": num_locali,
                    "num_bagni": num_bagni,
                    "classe_ener": classe_ener,
                    "tags": [tag.get_text(strip=True) for tag in tag_elements] if tag_elements else [],
                    "attivo": True,
                    "data_comparsa": oggi,
                    "data_aggiornamento": None,
                    "data_scomparsa": None
                }
                
                # Log progresso ogni 50 annunci
                progress_counter[0] += 1
                if progress_counter[0] % 50 == 0:
                    logger.info(f"🏠 Processati {progress_counter[0]} annunci...")
                
                return dati
        except asyncio.TimeoutError:
            logger.warning(f"⌛ Timeout per annuncio: {url}")
            return None
        except Exception as e:
            logger.warning(f"❌ Errore estrazione annuncio {url}: {e}")
            return None


async def get_annunci(df_urls):
    urls = df_urls["url"].dropna().unique().tolist()
    semaforo = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    start_time = time.time()
    risultati = []
    progress_counter = [0]  # Lista per passaggio per referenza

    logger.info(f"🔄 Inizio estrazione dati da {len(urls)} annunci")
    
    # Timeout più lungo per l'estrazione dati
    timeout = aiohttp.ClientTimeout(total=90)
    
    async with aiohttp.ClientSession(timeout=timeout) as session:
        tasks = [estrai_annuncio(session, url, semaforo, progress_counter) for url in urls]
        
        # Processa i task man mano che completano
        for i, task in enumerate(asyncio.as_completed(tasks)):
            result = await task
            if result:
                risultati.append(result)
            
            # Log progresso ogni 100 task completati
            if (i + 1) % 100 == 0:
                logger.info(f"📊 Completati {i + 1}/{len(tasks)} task")
            
            # Piccola pausa per non sovraccaricare
            if (i + 1) % 20 == 0:
                await asyncio.sleep(1)

    df_scraping_oggi = pd.DataFrame(risultati)
    logger.info(f"✅ Totale annunci estratti: {len(df_scraping_oggi)} in {round(time.time() - start_time,2)} sec")
    return df_scraping_oggi


async def scraping_completo(max_pagine=None):
    logger.info(f"🚀 Avvio scraping completo TrovaCasa Milano")
    
    # Fase 1: Raccolta URLs
    df_urls = await get_urls(max_pagine=max_pagine)
    if df_urls.empty:
        logger.error("❌ Nessun URL trovato")
        return pd.DataFrame()
    
    # Fase 2: Estrazione dati
    df_annunci = await get_annunci(df_urls)
    return df_annunci


# -----------------------
# Esecuzione da script
# -----------------------
if __name__ == "__main__":
    # Leggi configurazione da variabili d'ambiente
    max_pages = os.getenv('MAX_PAGES', '5')
    max_pages = None if max_pages == '0' else int(max_pages)
    
    logger.info(f"🚀 Configurazione: max_pagine={max_pages}")
    
    # Esegui scraping
    df_result = asyncio.run(scraping_completo(max_pagine=max_pages))

    # Salva CSV con timestamp dettagliato
    if not df_result.empty:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"trovacasa_milano_{timestamp}_{len(df_result)}_annunci_completi.csv"
        df_result.to_csv(filename, index=False, sep=';', encoding='utf-8')
        logger.info(f"✅ File salvato: {filename}")
        
        # Scrivi il nome del file per GitHub Actions
        with open('csv_filename.txt', 'w') as f:
            f.write(filename)
            
        # Statistiche finali
        logger.info(f"📊 Statistiche finali:")
        logger.info(f"   - Annunci totali: {len(df_result)}")
        logger.info(f"   - Con prezzo: {len(df_result[df_result['prezzo'] != 'N/A'])}")
        logger.info(f"   - Con superficie: {len(df_result[df_result['superficie_m2'].notna()])}")
        logger.info(f"   - Con numero locali: {len(df_result[df_result['num_locali'].notna()])}")
    else:
        logger.error("❌ Nessun annuncio estratto")
        # Crea file vuoto per evitare errori nel workflow
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        empty_filename = f"trovacasa_milano_{timestamp}_0_annunci_completi_EMPTY.csv"
        pd.DataFrame().to_csv(empty_filename, index=False)
        with open('csv_filename.txt', 'w') as f:
            f.write(empty_filename)
