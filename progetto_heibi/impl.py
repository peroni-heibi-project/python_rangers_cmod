import pandas as pd
from sparqlite import SPARQLClient
from rdflib.plugins.stores.sparqlstore import SPARQLUpdateStore
from rdflib import Graph, URIRef, Literal, RDFS
import isodate
from json import load
from sqlite3 import connect


#CIAO!

#java -server -Xmx1g -jar blazegraph.jar


#Andrea
#Impostato il parametro dbPathOrUrl:str = "", così da renderlo opzionale, dato che dovrebbe essere settato ad una stringa vuota. Ho ripetuto la cosa per tutte le sottoclassi
#Cambiato setDbPathOrUrl



class Handler:
    def __init__(self, dbPathOrUrl:str = ""):
        self.dbPathOrUrl = dbPathOrUrl

    def getDbPathOrUrl(self):
        return self.dbPathOrUrl
    
    def setDbPathOrUrl(self, input): #DA CAPIRE
        self.dbPathOrUrl = input
        return True
        #if input[len(input)-3:] == ".db":
        #    self.dbPathOrUrl = input
        #    return True
        #else:
        #    return False

#Andrea
#Corretto pushDatatoDb in pushDataToDb

class UploadHandler(Handler):
    def __init__(self, dbPathOrUrl:str = ""):
        super().__init__(dbPathOrUrl)

    def pushDatatoDb(self, path): 
        db = self.getDbPathOrUrl()
        if len(db) == 0:
            return False
        def push_csv_to_blaze():
            file = pd.read_csv(path, keep_default_na=None, 
                                dtype= {
                                    "oci" : "string",
                                    "citing" : "string",
                                    "cited" : "string", 
                                    "creation" : "string", 
                                    "timespan" : "string",
                                    "journal_sc" : "string",
                                    "author_sc" : "string"
                                })

            bib_entry = Graph()
            base_oci = URIRef("https://oci.opencitations.net/virtual/ci/")
            citing = URIRef("http://purl.org/spar/cito/hasCitingEntity")
            cited = URIRef("http://purl.org/spar/cito/hasCitedEntity")
            creation = URIRef("http://purl.org/spar/cito/hasCitationCreationDate")
            timespan = URIRef("http://purl.org/spar/cito/hasCitationTimeSpan")
            journal_sc = URIRef("http://purl.org/spar/cito/JournalSelfCitation")
            author_sc = URIRef("http://purl.org/spar/cito/AuthorSelfCitation")


            for idx, row in file.iterrows():
                if row["timespan"] and row["creation"] and row["timespan"]: #controlla se ci sono tutti gli elementi obbligatori. per quanto riguarda l'id, lo crea lui from sratch.
                    subject = base_oci + row["oci"]
                    bib_entry.add((subject, RDFS.label, Literal(row["oci"], datatype=URIRef("http://www.w3.org/2001/XMLSchema#string"))))
                    bib_entry.add((subject, citing, Literal(row["citing"], datatype=URIRef("http://www.w3.org/2001/XMLSchema#string"))))
                    bib_entry.add((subject, cited, Literal(row["cited"], datatype=URIRef("http://www.w3.org/2001/XMLSchema#string"))))
                    bib_entry.add((subject, creation, Literal(row["creation"])))
                    bib_entry.add((subject, timespan, Literal(row["timespan"], datatype=URIRef("http://www.w3.org/2001/XMLSchema#string"))))
                    bib_entry.add((subject, journal_sc, Literal(row["journal_sc"], datatype=URIRef("http://www.w3.org/2001/XMLSchema#string"))))
                    bib_entry.add((subject, author_sc, Literal(row["author_sc"], datatype=URIRef("http://www.w3.org/2001/XMLSchema#string"))))
            
            store = SPARQLUpdateStore()
            endpoint = 'http://127.0.0.1:9999/blazegraph/sparql'
            store.open((endpoint, endpoint))
            for triple in bib_entry:
                    store.add(triple)
            store.close()

        def push_json_to_db():
            with open(path, "r", encoding="utf-8") as f:
                data = load(f)

            title = list()
            pub_date = list()
            venue = list()
            biben_fk = list()


            for dic in data:
                author_list = list()
                id_list = list()
                a_fk = list()
                i_fk = list()

                if dic["title"] != "":
                    title.append(dic["title"])
                else:
                    title.append(None)

                if dic["pub_date"] != "":
                    pub_date.append(dic["pub_date"])
                else:
                    pub_date.append(None)
                
                venue.append(dic["venue"])

                int_id = ""
                for i in dic["id"]:
                    id_list.append(i)
                    if "omid" in i:
                        int_id = i
                        biben_fk.append(int_id)                
                    i_fk.append(biben_fk[len(biben_fk)-1])
                
                if dic["author"]:   
                    for a in dic["author"]:
                        author_list.append(a)
                        a_fk.append(i_fk[0])

                id_db = pd.DataFrame({"biben_internalId" : pd.Series(i_fk), 
                                      "id" : pd.Series(id_list)})
                with connect(db) as con:
                    id_db.to_sql("Id", con, if_exists="append", index=False)
                
                                    
                author_db = pd.DataFrame({"name" : pd.Series(author_list),
                                          "biben_id" : pd.Series(a_fk)})
                with connect(db) as con:
                    author_db.to_sql("Author", con, if_exists="append", index=False)
                                               
        
            df = pd.DataFrame({"internal_id" : pd.Series(biben_fk),  
                               "title" : pd.Series(title),  
                               "pub_date" : pd.Series(pub_date), "venue" : pd.Series(venue) })
            
            with connect(db) as con:
                df.to_sql("BibliographicEntity", con, if_exists="replace", index=False)

        if path[len(path)-3:] == "csv":
            push_csv_to_blaze()
        elif path[len(path)-4:] == "json":
            push_json_to_db()
        return True
    
class CitationUploadHandler(UploadHandler):
    def __init__(self, dbPathOrUrl:str = ""):
        super().__init__(dbPathOrUrl)
    
class BibliographicEntityUploadHandler(UploadHandler):
    """
    Legge il file dh_metadata.json e popola un database SQLite.

    Struttura del JSON (verificata sul file reale, 10.708 record):
      "id":       lista di stringhe → ["omid:br/...", "doi:...", ...]
      "author":   lista di stringhe → ["Cognome, Nome", ...]
      "title":    stringa           → può essere ""
      "pub_date": stringa           → può essere "", es. "2022-10"
      "venue":    stringa o null    → solo titolo, nessun id separato

    Tabelle create nel database SQLite:
      BibliographicEntity  → una riga per ogni record del JSON
      EntityId             → una riga per ogni identificatore di ogni entità
      Author               → una riga per ogni autore di ogni entità
      Venue                → una riga per ogni venue non nulla
    """

    def __init__(self):
        super().__init__()

    def pushDataToDb(self, path):

        # Leggiamo il file JSON con il pattern 'with open' del professore
        with open(path, "r", encoding="utf-8") as f:
            data = load(f)   # lista di dizionari

        # Liste di dizionari temporanee, una per ogni tabella.
        # Alla fine le convertiamo in DataFrame e le carichiamo con to_sql().
        rows_entity    = list()
        rows_entity_id = list()
        rows_author    = list()
        rows_venue     = list()

        # Contatori per gli id interni univoci (es. "be-0", "author-0", "venue-0")
        entity_counter = 0
        author_counter = 0
        venue_counter  = 0

        for record in data:

            internal_id = "be-" + str(entity_counter)
            entity_counter += 1

            # Campi semplici: .get() con "" di default evita KeyError
            title    = record.get("title", "")
            pub_date = record.get("pub_date", "")

            rows_entity.append({
                "internalId": internal_id,
                "title":      title,
                "pub_date":   pub_date
            })

            # "id" è già una lista: nessun parsing necessario
            for single_id in record.get("id", []):
                rows_entity_id.append({
                    "entityId": internal_id,
                    "id":       single_id
                })

            # "author" è già una lista: ogni stringa ha formato "Cognome, Nome".
            # maxsplit=1 gestisce cognomi composti come "La Mela, Matti"
            for auth_str in record.get("author", []):
                auth_str = auth_str.strip()
                if not auth_str:
                    continue
                parts  = auth_str.split(",", maxsplit=1)
                family = parts[0].strip() if len(parts) > 0 else ""
                given  = parts[1].strip() if len(parts) > 1 else ""
                rows_author.append({
                    "authorId":   "author-" + str(author_counter),
                    "givenName":  given,
                    "familyName": family,
                    "entityId":   internal_id
                })
                author_counter += 1

            # "venue" è una stringa o None: saltiamo None e stringhe vuote
            venue = record.get("venue", None)
            if venue:
                rows_venue.append({
                    "venueId":  "venue-" + str(venue_counter),
                    "title":    venue.strip(),
                    "entityId": internal_id
                })
                venue_counter += 1

        # Convertiamo in DataFrame pandas
        df_entity    = pd.DataFrame(rows_entity)
        df_entity_id = pd.DataFrame(rows_entity_id)
        df_author    = pd.DataFrame(rows_author)
        df_venue     = pd.DataFrame(rows_venue)

        # Scriviamo nel database SQLite.
        # if_exists="append" → aggiunge senza cancellare i dati già presenti.
        # index=False → non scrive la colonna indice di pandas.
        with connect(self.dbPathOrUrl) as con:
            if not df_entity.empty:
                df_entity.to_sql("BibliographicEntity", con,
                                 if_exists="append", index=False)
            if not df_entity_id.empty:
                df_entity_id.to_sql("EntityId", con,
                                    if_exists="append", index=False)
            if not df_author.empty:
                df_author.to_sql("Author", con,
                                 if_exists="append", index=False)
            if not df_venue.empty:
                df_venue.to_sql("Venue", con,
                                if_exists="append", index=False)

        return True


#piccolo test
#pipi = UploadHandler("")
#pipi.setDbPathOrUrl("database/biben1.db")
#print(pipi.setDbPathOrUrl("data/db.db"))
#print(UploadHandler.pushDatatoDb(pipi, "data/biben-cut.json") )



class QueryHandler(Handler):
    def __init__(self, dbPathOrUrl:str = ""):
        super().__init__(dbPathOrUrl)
        
    def getById(self, id):
        endpoint = 'http://127.0.0.1:9999/blazegraph/sparql'
        query = f"""
         prefix oci: <https://oci.opencitations.net/virtual/ci/>
         prefix cito: <http://purl.org/spar/cito/>
         SELECT ?oci ?citing ?cited ?creation ?timespan
        WHERE 
            {{?s rdfs:label '{id}' .
            ?s cito:hasCitationCreationDate ?creation .
            ?s cito:hasCitationTimeSpan ?timespan .
            ?s cito:hasCitingEntity ?citing .
            ?s cito:hasCitedEntity ?cited }}"""
        
        with SPARQLClient(endpoint) as client:
            result = client.query(query)
        if len(result) > 0: #se esiste un elemento con quell'id in blazegraph:
            variables = result["head"]["vars"]
            rows = list()
            for binding in result["results"]["bindings"]:
                row = dict()
                for var in variables:
                    if var in binding:
                        row[var] = binding[var]["value"]
                    else:
                        row[var] = ""
                rows.append(row)
                df = pd.DataFrame(rows)
                df["oci"] = id
                return df
            
        else: #se non esiste, vediamo se c'è nel db:
            c = Handler.getDbPathorUrl()
            with connect(c) as con:
                query = pd.read_sql(f"""SELECT author, title, pub_date, venue FROM * 
                WHERE id = {id} """, con)
                if len(query) > 0:
                    return query
                else: 
                    return "no items found."
#print(QueryHandler.getById("06102330980-0680100982"))            

class BibliographicEntityQueryHandler(QueryHandler):
    #"""
    #Legge dal database SQLite e restituisce DataFrame pandas.
    #Ogni metodo costruisce una query SQL ed esegue read_sql(), come mostrato
    #dal professore nel capitolo "Interacting with databases using Pandas".
    #"""

    def __init__(self, dbPathOrUrl:str = ""):
        super().__init__(dbPathOrUrl)

    #def getById(self, id):
        # JOIN tra EntityId e BibliographicEntity per trovare l'entità
        # con quell'identificatore. "?" è parametro sicuro (evita SQL injection).
        with connect(self.dbPathOrUrl) as con:
            query = """
                SELECT be.internalId, be.title, be.pub_date,
                       ei.id AS identifier
                FROM BibliographicEntity AS be
                JOIN EntityId AS ei ON be.internalId = ei.entityId
                WHERE ei.id = ?
            """
            df = pd.read_sql(query, con, params=(id,))
        return df

    def getAllBibliographicEntities(self):
        # LEFT JOIN perché alcune entità potrebbero non avere autori o venue
        with connect(self.dbPathOrUrl) as con:
            query = """
                SELECT be.internalId, be.title, be.pub_date,
                       ei.id AS identifier,
                       a.givenName, a.familyName,
                       v.title AS venueTitle
                FROM BibliographicEntity AS be
                LEFT JOIN EntityId AS ei ON be.internalId = ei.entityId
                LEFT JOIN Author   AS a  ON be.internalId = a.entityId
                LEFT JOIN Venue    AS v  ON be.internalId = v.entityId
            """
            df = pd.read_sql(query, con)
        return df

    def getBibliographicEntitiesWithTitle(self, title):
        # LIKE con % cerca la stringa come sottostringa del titolo
        with connect(self.dbPathOrUrl) as con:
            query = """
                SELECT be.internalId, be.title, be.pub_date,
                       ei.id AS identifier
                FROM BibliographicEntity AS be
                LEFT JOIN EntityId AS ei ON be.internalId = ei.entityId
                WHERE be.title LIKE ?
            """
            df = pd.read_sql(query, con, params=("%" + title + "%",))
        return df

    def getBibliographicEntitiesWithAuthor(self, name):
        # DISTINCT evita duplicati se il nome matcha sia givenName che familyName
        with connect(self.dbPathOrUrl) as con:
            query = """
                SELECT DISTINCT be.internalId, be.title, be.pub_date,
                       ei.id AS identifier,
                       a.givenName, a.familyName
                FROM BibliographicEntity AS be
                JOIN      Author    AS a  ON be.internalId = a.entityId
                LEFT JOIN EntityId  AS ei ON be.internalId = ei.entityId
                WHERE a.givenName  LIKE ?
                   OR a.familyName LIKE ?
            """
            pattern = "%" + name + "%"
            df = pd.read_sql(query, con, params=(pattern, pattern))
        return df

    def getBibliographicEntitiesWithinPublicationDate(self, start=None, end=None):
        # Clausola WHERE costruita dinamicamente: start e end sono opzionali
        conditions = list()
        params     = list()
        if start is not None:
            conditions.append("be.pub_date >= ?")
            params.append(start)
        if end is not None:
            conditions.append("be.pub_date <= ?")
            params.append(end)
        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        with connect(self.dbPathOrUrl) as con:
            query = f"""
                SELECT be.internalId, be.title, be.pub_date,
                       ei.id AS identifier
                FROM BibliographicEntity AS be
                LEFT JOIN EntityId AS ei ON be.internalId = ei.entityId
                {where_clause}
            """
            df = pd.read_sql(query, con, params=params)
        return df

    def getBibliographicEntitiesWithVenue(self, venue_name):
        with connect(self.dbPathOrUrl) as con:
            query = """
                SELECT DISTINCT be.internalId, be.title, be.pub_date,
                       ei.id AS identifier,
                       v.title AS venueTitle
                FROM BibliographicEntity AS be
                JOIN      Venue     AS v  ON be.internalId = v.entityId
                LEFT JOIN EntityId  AS ei ON be.internalId = ei.entityId
                WHERE v.title LIKE ?
            """
            df = pd.read_sql(query, con, params=("%" + venue_name + "%",))
        return df
    

#Andrea
#Rinominato getAuthorSelfCitations in getAuthorSelfCitations
#Rinominato getCitationsWithinTimeSpan in getCitationsWithinTimespan

    
class CitationQueryHandler(QueryHandler):
    def __init__(self, dbPathOrUrl:str = ""):
        super().__init__(dbPathOrUrl)


    def getAllCitations(self):
        endpoint = 'http://127.0.0.1:9999/blazegraph/sparql'
        query = f""" 
        PREFIX cito:  <http://purl.org/spar/cito/>
        
        SELECT ?oci ?creation ?citing ?cited ?timespan
        WHERE {{ 
            ?s cito:hasCitationCreationDate ?creation .
            ?s rdfs:label ?oci .
            ?s cito:hasCitingEntity ?citing
            ?s cito:hasCitedEntity ?cited
            ?s cito:hasCitationTimeSpan ?timespan}}
        """
        with SPARQLClient(endpoint) as client:
            result = client.query(query)
        variables = result["head"]["vars"]
        rows = list()
        for binding in result["results"]["bindings"]:
            row = dict()
            for var in variables:
                if var in binding:
                    row[var] = binding[var]["value"]
                else:
                    row[var] = ""
            rows.append(row)
        return pd.DataFrame(rows)
    
    def getAllAuthorSelfCitations(self):
        endpoint = 'http://127.0.0.1:9999/blazegraph/sparql'
        query = """ PREFIX cito:  <http://purl.org/spar/cito/>
                
            SELECT ?oci ?creation ?citing ?cited ?timespan
            WHERE {{ 
                ?s cito:hasCitationCreationDate ?creation .
                ?s rdfs:label ?oci .
                ?s cito:hasCitingEntity ?citing
                ?s cito:hasCitedEntity ?cited
                ?s cito:hasCitationTimeSpan ?timespan
            ?s cito:AuthorSelfCitation  ?author_sc . 
            ?s cito:AuthorSelfCitation> 'yes' .
            ?s rdfs:label ?label}}"""
        
        with SPARQLClient(endpoint) as client:
            result = client.query(query)
            variables = result["head"]["vars"]
            rows = list()
            for binding in result["results"]["bindings"]:
                row = dict()
                for var in variables:
                    if var in binding:
                        row[var] = binding[var]["value"]
                    else:
                        row[var] = ""
                rows.append(row)
        return pd.DataFrame(rows)
    
    def getAllJournalSelfCitations(self):
        endpoint = 'http://127.0.0.1:9999/blazegraph/sparql'
        query = """ PREFIX cito:  <http://purl.org/spar/cito/>
                
            SELECT ?oci ?creation ?citing ?cited ?timespan
            WHERE {{ 
                ?s cito:hasCitationCreationDate ?creation .
                ?s rdfs:label ?oci .
                ?s cito:hasCitingEntity ?citing
                ?s cito:hasCitedEntity ?cited
                ?s cito:hasCitationTimeSpan ?timespan
            ?s cito:JournalSelfCitation  ?journal_sc . 
            ?s cito:JournalSelfCitation> 'yes' .
            ?s rdfs:label ?label}}"""
        with SPARQLClient(endpoint) as client:
            result = client.query(query)
            variables = result["head"]["vars"]
            rows = list()
            for binding in result["results"]["bindings"]:
                row = dict()
                for var in variables:
                    if var in binding:
                        row[var] = binding[var]["value"]
                    else:
                        row[var] = ""
                rows.append(row)
        return pd.DataFrame(rows)
    
    def getCitationsWithinTimespan(self, beginning, end):
        endpoint = 'http://127.0.0.1:9999/blazegraph/sparql'
        query = f""" 
        PREFIX cito:  <http://purl.org/spar/cito/>
        
        SELECT ?oci ?creation ?citing ?cited ?timespan
        WHERE {{ 
            ?s cito:hasCitationCreationDate ?creation .
            ?s rdfs:label ?oci .
            ?s cito:hasCitingEntity ?citing
            ?s cito:hasCitedEntity ?cited
            ?s cito:hasCitationTimeSpan ?timespan}}
        """
        with SPARQLClient(endpoint) as client:
            response = client.query(query)
            variables = response["head"]["vars"]
            rows = list()
            for binding in response["results"]["bindings"]:
                row = dict()
                for var in variables:
                    if var in binding:
                        row[var] = binding[var]["value"]
                    else:
                        row[var] = ""
                rows.append(row)
            result = pd.DataFrame(rows)

            def timespan_to_days(timespan):
                days = 0
                d = isodate.parse_duration(timespan)
                if hasattr(d, "days"):
                    days += d.days
                if hasattr(d, "months"):
                    days += (d.months * 30)
                if hasattr(d, "years"):
                    days += (d.years * 365)
                return days
            
            if len(beginning) != 0 and len(end) != 0:
                min = timespan_to_days(beginning)
                max = timespan_to_days(end)
                for idx, row in result.iterrows():
                    t = timespan_to_days(row["timespan"])
                    if not(min <= t <= max):
                        result.drop(idx, axis=0, inplace=True)
                result.reset_index(drop=True, inplace=True)
            elif len(beginning) == 0:
                max = timespan_to_days(end)
                for idx, row in result.iterrows():
                    t = timespan_to_days(row["timespan"])
                    if not(t <= max):
                        result.drop(idx, axis=0, inplace=True)
                result.reset_index(drop=True, inplace=True)
            elif len(end) == 0:
                min = timespan_to_days(beginning)
                for idx, row in result.iterrows():
                    t = timespan_to_days(row["timespan"])
                    if not(min <= t ):
                        result.drop(idx, axis=0, inplace=True)
                result.reset_index(drop=True, inplace=True)                
            return result

    def getCitationsWithinDate(self, min, max): 
        endpoint = 'http://127.0.0.1:9999/blazegraph/sparql'
        query = f"""
            PREFIX cito:  <http://purl.org/spar/cito/>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

            SELECT ?oci ?creation ?citing ?cited ?timespan
            WHERE {{ 
            ?s cito:hasCitationCreationDate ?creation .
            ?s rdfs:label ?oci .
            ?s cito:hasCitingEntity ?citing
            ?s cito:hasCitedEntity ?cited
            ?s cito:hasCitationTimeSpan ?timespan}}
            """
       
        with SPARQLClient(endpoint) as client:
            result = client.query(query)
            variables = result["head"]["vars"]
            rows = list()
            for binding in result["results"]["bindings"]:
                row = dict()
                for var in variables:
                    if var in binding:
                        row[var] = binding[var]["value"]
                    else:
                        row[var] = ""
                rows.append(row)
            
            data = pd.DataFrame(rows) 

            def normalize_string(d):
                if len(d) == 4:
                    d += "-01-01"
                elif len(d) == 7:
                    d += "-01"
                return d

            for idx,row in data.iterrows():
                date = normalize_string(row["creation"])
                d = isodate.parse_date(date)

                if min:
                    min_date = isodate.parse_date(min)
                    if min_date > d:
                        data.drop(idx, axis = 0, inplace= True)
                if max: 
                    max_date = isodate.parse_date(max)
                    if max_date < d:
                        data.drop(idx, axis = 0, inplace= True)
            return data

                
                


        
#print(CitationQueryHandler.getCitationsWithinDate("2024-07", "2025-02"))    
#print(CitationQueryHandler.getCitationsWithinTimeSpan("P0Y", ""))

#print(CitationQueryHandler.getAllCitations())
#1print(CitationQueryHandler.getAuthorSelfCitations())
#print(CitationQueryHandler.getAllJournalSelfCitations())

class IdentifiableEntity():
    def __init__(self, id:str):
        self.id = id
    
class BibliographicEntity(IdentifiableEntity):
    def __init__(self, id, title, author, publication_date, venue):
        self.title = title
        self.author = author
        self.publication_date = publication_date
        self.venue = venue
        super().__init__(id)


class Citation(IdentifiableEntity):
    def __init__(self, id, creation:str,timespan:str ):
        self.id = id
        self.creation = creation
        self.timespan = timespan
        super().__init__(id)
    
class JournalSelfCitation(Citation):
    def __init__(self, id, creation, timespan):
        super().__init__(id, creation, timespan)

class AuthorSelfCitation(Citation):
    def __init__(self, id, creation, timespan):
        super().__init__(id, creation, timespan)





class BasicQueryEngine():
    def __init__(self, citationQuery:list, bibliographicEntityQuery:list):
        self.citationQuery = citationQuery 
        self.bibliographicEntityQuery = bibliographicEntityQuery
    
    def cleanCitationHandlers(self) -> bool:
        self.citationQuery = []
        return True
    
    def cleanBibliographicEntityHandlers(self) -> bool:
        self.bibliographicEntityQuery = []
        return True
    
    def addCitationHandler(self, input:CitationQueryHandler) -> bool: 
        if type(input) == CitationQueryHandler:
            self.citationQuery.append(input)
            return True
        else:
            return False

    def addBibliographicEntityHandler(self, input:BibliographicEntityQueryHandler) -> bool:
        if type(input) == BibliographicEntityQueryHandler:
            self.bibliographicEntityQuery.append(input)
            return True
        else:
            return False
    
    def getEntityById(id):
      #primo passo: trovare il fottuto id.
      prefix_id = "https://oci.opencitations.net/virtual/ci/"
      df = QueryHandler.getById(id).iloc[0]
      if df:
        df_class = Citation(id= prefix_id + df["oci"], creation=df["creation"], timespan=df["timespan"]) 
        return df_class.id, df_class.creation , df_class.timespan
      else: 
          return None
    
    def getAllCitations() -> list:
        pass

    def getAllAuthorSelfCitations() -> list:
        pass

    def getAllJournalSelfCitations() -> list:
        pass

    def getCitationsWithinTimespan(min_time:str, max_time:str) -> list:
        pass

    def getCitationsWithinDate(start_date:str, end_date:str) -> list:
        pass

    def getAllBibliographicEntities() -> list:
        pass

    def getBibliographicEntitesWithTitle(title:str) -> list:
        pass

    def getBibliographicEntitiesWithAuthor(author:str) -> list:
        pass

    def getBibliographicEntitesWithinDate(start_date:str, end_date:str) -> list:
        pass

    def getBibliographicEntitiesWithVenue(venue:str) -> list:
        pass
    
#print(BasicQueryEngine.getEntityById("06102330980-0680100982"))

class FullQueryEngine(BasicQueryEngine):
    def __init__(self, citationQuery:str, bibliographicEntityQuery:str):
        self.citationQuery = citationQuery 
        self.bibliographicEntityQuery = bibliographicEntityQuery
        super().__init__(citationQuery, bibliographicEntityQuery)

    def getAuthorSelfCitationsByName(author_name:str) -> list:
        pass

    def getJournalSelfCitationsByName(journal_name:str) -> list:
        pass

    def getCitationsOfBibEntityByTitle(bib_entity_tutle:str, min_date:str, max_date:str) -> list:
        pass

    def getReferencesOfBibEntityByTitleWithinTimespan(bib_entity_title:str, min_timespan:str, max_timespan:str) -> list:
        pass

    
    
Bonzo = Handler()