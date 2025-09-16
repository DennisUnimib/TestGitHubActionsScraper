import aiohttp
import asyncio
from bs4 import BeautifulSoup
import pandas as pd
from tqdm import tqdm
import time
from datetime import datetime

# -----------------------------
# PARAMETRI GENERALI
# -----------------------------
base_url = "https://www.trovacasa.it"
start_url = f"{base_url}/case-in-vendita/milano"
headers = {"User-Agent": "Mozilla/5.0"}
MAX_CONCURRENT_REQUESTS = 10
db_path = "Database_annunci.csv"
colonne_standard = ['_id','url','titolo','prezzo','indirizzo','attivo','data_comparsa','data_aggiornamento','data_scomparsa']

oggi = datetime.today().strftime('%Y-%m-%d')

# -----------------------------
# FUNZIONI UTILI
# -----------------------------
def uniforma_df(df, colonne_standard):
    """Mantiene solo le colonne standard, resetta indice e rimuove duplicati su _id"""
    for col in colonne_standard:
        if col not in df.columns:
            df[col] = pd.NA
    df = df[colonne_standard].copy()
    df = df.reset_index(drop=True)
    df = df.drop_duplicates(subset=['_id'], keep='last')
    return df

# -----------------------------
# SCRAPING URL ANNUNCI
# -----------------------------
async def scarica_pagina(session, url, numero_pagina):
    try:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                print(f"⚠️ Errore pagina {numero_pagina}")
                return None, None
            html = await response.text()
            soup = BeautifulSoup(html, "html.parser")

            link_annunci = [base_url + a.get("href") for a in soup.select("a.card__title.js_link_immobile") if a.get("href")]

            next_button = soup.select_one("a.pager__link.next")
            next_url = base_url + next_button.get("href") if next_button and next_button.get("href") else None

            return link_annunci, next_url
    except Exception as e:
        print(f"❌ Errore pagina {numero_pagina}: {e}")
        return None, None

async def get_urls(max_pagine=None, max_annunci=None):
    pagina_corrente = start_url
    pagina_numero = 1
    tutti_link_annunci = []
    start_time = time.time()

    async with aiohttp.ClientSession() as session:
        pbar = tqdm(total=max_pagine if max_pagine else 1000, desc="📄 Download pagine", unit="pagina")

        while pagina_corrente:
            link_annunci, pagina_corrente = await scarica_pagina(session, pagina_corrente, pagina_numero)
            if link_annunci:
                tutti_link_annunci.extend(link_annunci)
                if max_annunci and len(tutti_link_annunci) >= max_annunci:
                    tutti_link_annunci = tutti_link_annunci[:max_annunci]
                    break
            else:
                break
            pagina_numero += 1
            pbar.update(1)
            if max_pagine and pagina_numero > max_pagine:
                break
            await asyncio.sleep(1)
        pbar.close()

    df_urls = pd.DataFrame({"url": tutti_link_annunci})
    print(f"\n✅ Totale annunci trovati: {len(tutti_link_annunci)}")
    print(f"📄 Pagine scaricate: {pagina_numero - 1}")
    print(f"⏱️ Tempo: {round(time.time() - start_time,2)} sec")
    return df_urls

# -----------------------------
# ESTRAZIONE DATI ANNUNCI
# -----------------------------
async def estrai_annuncio(session, url, semaforo):
    async with semaforo:
        try:
            async with session.get(url, headers=headers) as response:
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
                    "data_aggiornamento": oggi,
                    "data_scomparsa": None
                }
                return dati
        except Exception:
            return None

async def get_annunci(df_urls):
    urls = df_urls["url"].dropna().unique().tolist()
    semaforo = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    start_time = time.time()
    risultati = []

    async with aiohttp.ClientSession() as session:
        tasks = [estrai_annuncio(session, url, semaforo) for url in urls]
        for f in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="🔍 Estrazione annunci", unit="annuncio"):
            result = await f
            if result:
                risultati.append(result)

    df_scraping_oggi = pd.DataFrame(risultati)
    print(f"\n✅ Totale annunci estratti: {len(df_scraping_oggi)} in {round(time.time() - start_time,2)} sec")
    return df_scraping_oggi

# -----------------------------
# AGGIORNAMENTO DATABASE STORICO - VERSIONE CORRETTA
# -----------------------------
def aggiorna_db(df_scraping_oggi):
    # Carico DB
    try:
        df_db = pd.read_csv(db_path)
    except FileNotFoundError:
        df_db = pd.DataFrame(columns=colonne_standard)

    # Uniformo i dataframe iniziali
    df_db = uniforma_df(df_db, colonne_standard)
    df_scraping_oggi = uniforma_df(df_scraping_oggi, colonne_standard)

    # Merge per identificare nuovi/aggiornati/scomparsi
    df_merge = df_db.merge(df_scraping_oggi, on="_id", how="outer", indicator=True, suffixes=('_db','_today'))

    # NUOVI ANNUNCI
    df_nuovi = df_merge[df_merge['_merge']=='right_only'].copy()
    if not df_nuovi.empty:
        # Seleziono solo le colonne _today e aggiungo i metadati
        cols_today = [c for c in df_nuovi.columns if c.endswith('_today')]
        df_nuovi_clean = df_nuovi[cols_today].copy()
        
        # Rinomino le colonne rimuovendo il suffisso _today
        rename_dict = {c: c.replace('_today','') for c in cols_today}
        df_nuovi_clean = df_nuovi_clean.rename(columns=rename_dict)
        
        # Aggiungo i metadati
        df_nuovi_clean['attivo'] = True
        df_nuovi_clean['data_comparsa'] = oggi
        df_nuovi_clean['data_aggiornamento'] = oggi
        df_nuovi_clean['data_scomparsa'] = pd.NA
        
        df_nuovi = uniforma_df(df_nuovi_clean, colonne_standard)
    else:
        df_nuovi = pd.DataFrame(columns=colonne_standard)

    # ANNUNCI AGGIORNATI
    df_comuni = df_merge[df_merge['_merge']=='both'].copy()
    df_aggiornati = pd.DataFrame(columns=colonne_standard)
    
    if not df_comuni.empty:
        aggiornati_list = []
        campi_da_controllare = ['titolo','prezzo','indirizzo']
        
        for idx, row in df_comuni.iterrows():
            aggiornamenti = False
            record_aggiornato = {}
            
            # Copio tutti i dati dal database
            for col in colonne_standard:
                if col.endswith('_db'):
                    continue
                col_db = f"{col}_db"
                if col_db in row:
                    record_aggiornato[col] = row[col_db]
                else:
                    record_aggiornato[col] = row[col] if col in row else pd.NA
            
            # Controllo aggiornamenti sui campi specifici
            for campo in campi_da_controllare:
                val_db = row[f"{campo}_db"] if f"{campo}_db" in row else pd.NA
                val_today = row[f"{campo}_today"] if f"{campo}_today" in row else pd.NA
                
                if val_db != val_today:
                    aggiornamenti = True
                    record_aggiornato[campo] = val_today
            
            # Se ci sono aggiornamenti, aggiorno la data
            if aggiornamenti:
                record_aggiornato['data_aggiornamento'] = oggi
            
            aggiornati_list.append(record_aggiornato)
        
        if aggiornati_list:
            df_aggiornati = pd.DataFrame(aggiornati_list)
            df_aggiornati = uniforma_df(df_aggiornati, colonne_standard)

    # ANNUNCI SCOMPARSI
    df_scomparsi = df_merge[df_merge['_merge']=='left_only'].copy()
    if not df_scomparsi.empty:
        # Seleziono solo le colonne _db e rimuovo il suffisso
        cols_db = [c for c in df_scomparsi.columns if c.endswith('_db')]
        df_scomparsi_clean = df_scomparsi[cols_db].copy()
        
        rename_dict = {c: c.replace('_db','') for c in cols_db}
        df_scomparsi_clean = df_scomparsi_clean.rename(columns=rename_dict)
        
        # Aggiorno i metadati per annunci scomparsi
        df_scomparsi_clean['attivo'] = False
        df_scomparsi_clean['data_scomparsa'] = oggi
        df_scomparsi_clean['data_aggiornamento'] = df_scomparsi_clean['data_aggiornamento'].fillna(oggi)
        
        df_scomparsi = uniforma_df(df_scomparsi_clean, colonne_standard)
    else:
        df_scomparsi = pd.DataFrame(columns=colonne_standard)

    # ANNUNCI NON MODIFICATI (quelli che sono sia nel db che nello scraping di oggi ma senza modifiche)
    if not df_aggiornati.empty:
        ids_aggiornati = set(df_aggiornati['_id'].dropna())
    else:
        ids_aggiornati = set()
    
    if not df_nuovi.empty:
        ids_nuovi = set(df_nuovi['_id'].dropna())
    else:
        ids_nuovi = set()
    
    if not df_scomparsi.empty:
        ids_scomparsi = set(df_scomparsi['_id'].dropna())
    else:
        ids_scomparsi = set()
    
    ids_modificati = ids_aggiornati | ids_nuovi | ids_scomparsi
    df_non_modificati = df_db[~df_db['_id'].isin(ids_modificati)].copy()
    df_non_modificati = uniforma_df(df_non_modificati, colonne_standard)

    # CONCATENAZIONE FINALE
    dataframes_to_concat = []
    for df, nome in [(df_non_modificati, "non_modificati"), 
                     (df_aggiornati, "aggiornati"), 
                     (df_nuovi, "nuovi"), 
                     (df_scomparsi, "scomparsi")]:
        if not df.empty:
            # Debug: verifica che non ci siano colonne duplicate
            if df.columns.duplicated().any():
                print(f"⚠️ ATTENZIONE: DataFrame {nome} ha colonne duplicate: {df.columns[df.columns.duplicated()].tolist()}")
                df = df.loc[:, ~df.columns.duplicated()]
            dataframes_to_concat.append(df)

    if dataframes_to_concat:
        df_finale = pd.concat(dataframes_to_concat, ignore_index=True)
    else:
        df_finale = pd.DataFrame(columns=colonne_standard)

    # Pulizia finale e controllo tipi
    df_finale = uniforma_df(df_finale, colonne_standard)
    df_finale['attivo'] = df_finale['attivo'].fillna(False).astype(bool)
    
    for col in ['data_comparsa','data_aggiornamento','data_scomparsa']:
        df_finale[col] = pd.to_datetime(df_finale[col], errors='coerce').dt.strftime('%Y-%m-%d')

    # Salvataggio CSV
    df_finale.to_csv(db_path, index=False)

    # Statistiche
    print(f"📊 STATISTICHE AGGIORNAMENTO DATABASE:")
    print(f"   Annunci nuovi: {len(df_nuovi)}")
    print(f"   Annunci aggiornati: {len(df_aggiornati)}")
    print(f"   Annunci scomparsi: {len(df_scomparsi)}")
    print(f"   Annunci non modificati: {len(df_non_modificati)}")
    print(f"   Totale finale nel database: {len(df_finale)}")

# -----------------------------
# ESECUZIONE
# -----------------------------
if __name__ == "__main__":
    # Step 1: URL
    df_urls = asyncio.run(get_urls(max_pagine=10, max_annunci=250))
    # Step 2: Estrazione dati annunci
    df_scraping_oggi = asyncio.run(get_annunci(df_urls))
    # Step 3: Aggiornamento DB
    aggiorna_db(df_scraping_oggi)