# Ciao belle padelle
La repo va aggiustata perché ci sono robe a caso di default ma comunque per ora ho fatto la struttura base, Adri dovrebbe aggiungere la sua parte

Ciao sono Adri, non è obbligatorio leggere
**Come è organizzato il codice**

Il professore ha diviso tutto in tre livelli:

Il **livello 1** sono le classi del data model — oggetti Python puri che rappresentano i concetti: una pubblicazione, un autore, una citazione. Non toccano nessun database.

Il **livello 2** sono gli handler — classi che parlano con i database. Si dividono in due famiglie: gli *upload handler* che scrivono dati nel database, e i *query handler* che leggono dati dal database e li restituiscono come DataFrame pandas.

Il **livello 3** è il query engine — prende i DataFrame dagli handler e li trasforma in oggetti Python del livello 1. È il "traduttore" finale.

ALCUNE COSE CHE STO STUDIANDO:
Io sono responsabile di tutto ciò che riguarda il JSON e SQLite:

- `BibliographicEntityUploadHandler` → legge il JSON, scrive in SQLite
- `BibliographicEntityQueryHandler` → legge da SQLite, restituisce DataFrame

**Partiamo da un record del JSON file**

Quando aprite `dh_metadata.json` trovate cose come questa:

{
"title": "Revisiting Connotations Of Digital Humanists",
"author": ["Ma, Rongqian"],
"pub_date": "2022-10",
"venue": "Proceedings Of The Association For Information Science",
"id": ["omid:br/0603894473", "doi:10.1002/pra2.714"]
}

Questo è un dict, Il file ne contiene 10.708 così, in una lista.

**Cosa fa `pushDataToDb` con questo record**

Pensa al metodo come a una catena di montaggio in 5 passi:

**Passo 1 — Apre il file** con `with open(path)` e `load(f)`. Ora hai in memoria una lista di 10.708 dizionari.

**Passo 2 — Per ogni record, prepara le righe** da inserire nelle tabelle. Questo è il cuore del metodo: per quel record sopra prepara queste righe:

Per la tabella `BibliographicEntity`:

internalId: "be-6"   title: "Revisiting..."   pub_date: "2022-10”

Per la tabella `EntityId` (una riga per ogni id):

`entityId: "be-6"   id: "omid:br/0603894473"
entityId: "be-6"   id: "doi:10.1002/pra2.714"`

Per la tabella `Author`:

`authorId: "author-5"   givenName: "Rongqian"   familyName: "Ma"   entityId: "be-6"`

Per la tabella `Venue`:

`venueId: "venue-4"   title: "Proceedings Of..."   entityId: "be-6"`

**Passo 3 — Costruisce i DataFrame** da quelle liste di righe con `DataFrame(rows_...)`.

**Passo 4 — Scrive nel database** con `to_sql()`.

---

**Poi cosa fa `BibliographicEntityQueryHandler`?**

Fa il percorso inverso. Quando chiami per esempio:

`qh.getById("doi:10.1002/pra2.714")`

Esegue una query SQL che va a cercare nel database quella pubblicazione e te la restituisce come DataFrame:

`internalId   title                        pub_date   identifier
be-6         Revisiting Connotations...   2022-10    doi:10.1002/pra2.714`

---

**perché abbiamo bisogno di 4 tabelle separate** invece di mettere tutto in una tabella sola? Questa è la parte concettualmente più importante.

Immagina di voler mettere tutto in **una tabella sola**:

`title                    author          pub_date   id
Revisiting Connotations  Ma, Rongqian    2022-10    doi:10.1002/pra2.714
Revisiting Connotations  Ma, Rongqian    2022-10    omid:br/0603894473`

Vedi il problema? Lo stesso articolo appare **due volte** solo perché ha due identificatori. Se avesse 3 id apparirebbe 3 volte. Se avesse anche 2 autori apparirebbe 6 volte (3 id × 2 autori). I dati si moltiplicano e si ripetono.

Questo si chiama **ridondanza** — stai salvando le stesse informazioni più volte inutilmente.

---

**La soluzione è separare le cose che hanno cardinalità diversa.**

Un articolo ha **un solo** titolo e **una sola** data → stanno bene in `BibliographicEntity`, una riga per articolo.

Un articolo può avere **più id** → ognuno va in una riga separata in `EntityId`, collegata all'articolo tramite `entityId`.

Un articolo può avere **più autori** → stessa cosa con `Author`.

Un articolo può avere **una venue** → `Venue`.

Il collegamento avviene tramite `internalId` — è come un codice univoco che dice "questa riga di `Author` appartiene a quell'articolo in `BibliographicEntity`".

---

ESEMPIO: Se volessi sapere tutti gli autori dell'articolo con id `"doi:10.1002/pra2.714"`, come pensi che funzionerebbe la ricerca tra le tabelle?

La ricerca funziona in **tre salti**:

**Salto 1** — Vai in `EntityId` e cerchi `"doi:10.1002/pra2.714"`. Trovi:

`entityId: "be-6"   id: "doi:10.1002/pra2.714"`

Ora sai che l'articolo ha `internalId = "be-6"`.

**Salto 2** — Vai in `BibliographicEntity` e cerchi `internalId = "be-6"`. Trovi:

`internalId: "be-6"   title: "Revisiting..."   pub_date: "2022-10"`

**Salto 3** — Vai in `Author` e cerchi tutte le righe con `entityId = "be-6"`. Trovi:

`givenName: "Rongqian"   familyName: "Ma"   entityId: "be-6"`

---

Questi tre salti in SQL si fanno in una riga sola con il **JOIN** — che è esattamente quello che fa `getById()` nel codice:

`SELECT be.internalId, be.title, be.pub_date,
       ei.id AS identifier
FROM BibliographicEntity AS be
JOIN EntityId AS ei ON be.internalId = ei.entityId
WHERE ei.id = ?`

Il `JOIN ... ON be.internalId = ei.entityId` è proprio il "salto" — dice a SQLite *"collega le righe di queste due tabelle dove internalId corrisponde a entityId"*.

---

ESEMPIO 2: Immagina le quattro tabelle come quattro fogli:

**Foglio 1 — BibliographicEntity**

`internalId   title              pub_date
be-0         Digital Methods    2021
be-1         Text Mining in DH  2020
be-2         Revisiting...      2022`

**Foglio 2 — EntityId**

`entityId   id
be-0       doi:10.1111/aaa
be-0       omid:br/001
be-1       doi:10.2222/bbb
be-2       doi:10.1002/pra2.714
be-2       omid:br/0603894473`

**Foglio 3 — Author**

`authorId    givenName   familyName   entityId
author-0    John        Doe          be-0
author-1    Anna        Smith        be-0
author-2    Marco       Rossi        be-1
author-3    Rongqian    Ma           be-2`

**Foglio 4 — Venue**

`venueId    title                  entityId
venue-0    Digital Humanities Q.  be-0
venue-1    LLC Journal            be-1
venue-2    Proceedings ASIS       be-2`

---

Nota una cosa importante: **il filo che collega tutto è `internalId`**. È come un codice fiscale — ogni articolo ne ha uno solo, e tutte le altre tabelle lo usano per dire "appartengo a quell'articolo".

Ora ti faccio una domanda concreta: se ti chiedo *"chi sono gli autori di tutti gli articoli pubblicati nel 2021?"*, su **quali fogli** dovresti guardare e in che ordine?

BibliographicEntity e Author

Infatti la query SQL che fa esattamente questo è:

`SELECT be.title, a.givenName, a.familyName
FROM BibliographicEntity AS be
JOIN Author AS a ON be.internalId = a.entityId
WHERE be.pub_date = "2021"`

Traducendola in italiano parola per parola:

- `FROM BibliographicEntity AS be` → parti dal foglio BibliographicEntity, chiamalo "be" per brevità
- `JOIN Author AS a ON be.internalId = a.entityId` → collegaci il foglio Author dove i codici corrispondono
- `WHERE be.pub_date = "2021"` → tieni solo le righe del 2021
- `SELECT be.title, a.givenName, a.familyName` → mostrami solo questi tre campi

Sul nostro esempio di prima il risultato sarebbe:

`title             givenName   familyName
Digital Methods   John        Doe
Digital Methods   Anna        Smith`

---

Hai notato una cosa? `Digital Methods` appare **due volte** — una per ogni autore. Questo è normale in SQL: il JOIN moltiplica le righe. Per questo nel codice usiamo `DISTINCT` in alcuni metodi, per eliminare i duplicati quando non ci servono.

Passiamo a capire come funziona `pushDataToDb,` cioè come il codice costruisce questi quattro fogli partendo dal JSON?

priamo il codice di `pushDataToDb` e lo leggiamo insieme un pezzo alla volta.

**Pezzo 1 — Apre il file JSON**

`with open(path, "r", encoding="utf-8") as f:
    data = load(f)`

`data` ora è una lista di 10.708 dizionari Python. Ogni dizionario è un articolo. Semplice.

---

**Pezzo 2 — Prepara le liste vuote**

`rows_entity    = list()
rows_entity_id = list()
rows_author    = list()
rows_venue     = list()`

Questi sono i quattro "fogli" che stiamo costruendo — per ora vuoti. Alla fine diventeranno i quattro DataFrame da caricare nel database.

---

**Pezzo 3 — I contatori**

`entity_counter = 0
author_counter = 0
venue_counter  = 0`

Servono per generare gli id interni univoci: `"be-0"`, `"be-1"`, `"author-0"` ecc. Ogni volta che processiamo un articolo, incrementiamo il contatore di 1.

---

Adesso entriamo nel `for` — è il cuore del metodo.

`for record in data:`

Questo significa: *"per ogni articolo nella lista, fai quello che segue"*. Quindi tutto quello che è dentro il `for` si ripete 10.708 volte, una per ogni articolo.

---
**IL CICLO FOR**
1)Crea l'id interno (internal_id = "be-0", ecc.)
2)Prende i campi semplici (title, pub_date) → va in rows_entity
3)Prende gli id → va in rows_entity_id
4)Prende gli autori → va in rows_author ← questa è quella che ti ho appena spiegato
5)Prende la venue → va in rows_venue
**Prima cosa dentro il for — crea l'id interno**

`internal_id = "be-" + str(entity_counter)
entity_counter += 1`

Al primo giro `internal_id = "be-0"`, al secondo `"be-1"`, e così via. È il codice fiscale dell'articolo di cui parlavamo prima.

---

**Seconda cosa — prende i campi semplici**

`title    = record.get("title", "")
pub_date = record.get("pub_date", "")`

`.get("title", "")` significa: *"prendimi il valore del campo title, e se non esiste mettimi una stringa vuota"*. Lo facciamo così perché alcuni record nel JSON hanno campi mancanti.

Poi li mette nel foglio `BibliographicEntity`:

`rows_entity.append({
    "internalId": internal_id,
    "title":      title,
    "pub_date":   pub_date
})`

---

**Terza cosa — prende gli id**

`for single_id in record.get("id", []):
    rows_entity_id.append({
        "entityId": internal_id,
        "id":       single_id
    })`

Ricordi che `"id"` nel JSON è già una lista? Quindi iteriamo su quella lista e aggiungiamo una riga per ogni id. Tutti condividono lo stesso `internal_id` — così SQLite sa che appartengono allo stesso articolo.

Certo! Ecco la lista completa e omogenea:

Prima cosa dentro il for — crea l'id interno
pythoninternal_id = "be-" + str(entity_counter)
entity_counter += 1
Al primo giro internal_id = "be-0", al secondo "be-1", e così via. È il codice fiscale dell'articolo.

Seconda cosa — prende i campi semplici
pythontitle    = record.get("title", "")
pub_date = record.get("pub_date", "")

rows_entity.append({
    "internalId": internal_id,
    "title":      title,
    "pub_date":   pub_date
})
.get("title", "") significa: "prendimi il valore di title, e se non esiste mettimi una stringa vuota". Poi aggiunge la riga al foglio BibliographicEntity.

Terza cosa — prende gli id
pythonfor single_id in record.get("id", []):
    rows_entity_id.append({
        "entityId": internal_id,
        "id":       single_id
    })
"id" nel JSON è già una lista, quindi iteriamo direttamente. Ogni id diventa una riga separata in EntityId, tutte con lo stesso internal_id così SQLite sa che appartengono allo stesso articolo.


