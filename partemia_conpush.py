import pandas as pd
from SPARQLWrapper import SPARQLWrapper, POST, JSON

# ===============================================================================
# CLASSE BASE: Handler
# Contiene il percorso/URL del database
# ===============================================================================

class Handler:
    def __init__(self):
        self.dbPathOrUrl = "" #parte vuota, si imposta dopo

    def getDbPathOrUrl(self):
        return self.dbPathOrUrl
    
    def setDbPathOrUrl(self, pathOrUrl):
        self.dbPathOrUrl = pathOrUrl
        return True
    
# ===============================================================================
# UploadHandler - figlia di Handler
# Definisce il metodo pushDataToDb (astratto qui, poi implementato nelle sottoclassi)
# ===============================================================================

class UploadHandler(Handler):
    def __init__(self):
        super().__init__() # chiama il costruttore di Handler

    def pushDataToDb(self, path): #le sottoclassi implementeranno questa logica
        pass

# ===============================================================================
# Query-Handler - figlia di Handler
# Definisce il metodo getById (astratto qui, poi implementato nelle sottoclassi)
# ===============================================================================

class QueryHandler(Handler):
    def __init__(self):
        super().__init__() # chiama il costruttore di Handler

    def getById(self, id): # le sottoclassi implementeranno questa logica
        pass

# ===============================================================================
# CitationUploadHandler - PARTE ALICE
# Legge CSV e carica nel database a grafo (Blazegraph)
# ===============================================================================

class CitationUploadHandler(UploadHandler):
    def __init__(self):
        super().__init__()

    def pushDataToDb(self, path):
        #1. Leggi il CSV con Pandas
        df = pd.read_csv(path, keep_default_na=None)


        #3. Connettiti a Blazegraph
        sparql = SPARQLWrapper(self.dbPathOrUrl)
        sparql.setMethod("POST")

        #4. Per ogni riga del CSV, crea una "triple" RDF e caricala
        for _, row in df.iterrows():

            #Costruiamo l'URI univoco per questa citazione
            citation_uri = f"https://opencitations.net/citation/{row['oci']}"

            #Costruiamo la query SPARQL per inserire i dati
            query = f"""
            PREFIX cito: <http://purl.org/spar/cito/>
            PREFIX datacite: <http://purl.org/spar/datacite/>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

            INSERT DATA {{
                <{citation_uri}> a cito:Citation ;
                    cito:hasCitingEntity <https://opencitations.net/entity/{row['citing']}> ;
                    cito:hasCitedEntity <https://opencitations.net/entity/{row['cited']}> ;
                    cito:hasCreationDate "{row['creation']}"^^xsd:string ;
                    cito:hasTimespan "{row['timespan']}"^^xsd:string ;
                    cito:isJournalSelfCitation "{row['journal_sc']}"^^xsd:string ;
                    cito:isAuthorSelfCitation "{row['author_sc']}"^^xsd:string . 
            }}
            """

            sparql.setQuery(query)
            sparql.query()
        return True

# ===============================================================================
# BibliographicEntityUploadHandler - PARTE DI ADRIANA
# Legge JSON e carica nel database relazionale (SQLite)
# ===============================================================================

class BibliographicEntityUploadHandler(UploadHandler):
    def __init__(self):
        super().__init__()

    def pushDataToDb(self, path):
        #qui va implementata la lettura del JSON e il caricamento in SQLite
        pass

# ===============================================================================
# CitationQueryHandler - PARTE ALICE
# Interroga il database a grafo (Blazegraph) e restituisce DataFrame
# ===============================================================================

class CitationQueryHandler(QueryHandler):
    def __init__(self):
        super().__init__()

    def getById(self, id):
        pass

    def getAllCitations(self):
        sparql = SPARQLWrapper(self.dbPathOrUrl)
        sparql.setReturnFormat(JSON)

        sparql.setQuery("""
            PREFIX cito: <http://purl.org/spar/cito/>

            SELECT ?citation ?citing ?cited ?creation ?timespan ?journal_sc ?author_sc
            WHERE {
                ?citation a cito:Citation ;
                    cito:hasCitingEntity ?citing ;
                    cito:hasCitedEntity ?cited ;
                    cito:hasCreationDate ?creation ;
                    cito:hasTimespan ?timespan ;
                    cito:isJournalSelfCitation ?journal_sc ;
                    cito:isAuthorSelfCitation ?author_sc .
            }
        """)

        results = sparql.query().convert()

        # Converto il risultato in un DataFrame Pandas
        rows = []
        for r in results["results"]["bindings"]:
            rows.append({
                "citation": r["citation"]["value"],
                "citing": r["citing"]["value"],
                "cited": r["cited"]["value"],
                "creation": r["creation"]["value"],
                "timespan": r["timespan"]["value"],
                "journal_sc": r["journal_sc"]["value"],
                "author_sc": r["author_sc"]["value"],
            })               

        return pd.DataFrame(rows)         

    def getAllAuthorSelfCitations(self):
        sparql = SPARQLWrapper(self.dbPathOrUrl)
        sparql.setReturnFormat(JSON)

        sparql.setQuery("""
            PREFIX cito: <http://purl.org/spar/cito/>
            
            SELECT ?citation ?citing ?cited ?creation ?timespan ?journal_sc ?author_sc
            WHERE {
                ?citation a cito:Citation ;
                    cito:hasCitingEntity ?citing ;
                    cito:hasCitedEntity ?cited ;
                    cito:hasCreationDate ?creation ;
                    cito:hasTimespan ?timespan ;
                    cito:isJournalSelfCitation ?journal_sc ;
                    cito:isAuthorSelfCitation ?author_sc .
                FILTER(?author_sc = "yes")
            }
        """)

        results = sparql.query().convert()

        rows = []
        for r in results["results"]["bindings"]:
            rows.append({
                "citation": r["citation"]["value"],
                "citing": r["citing"]["value"],
                "cited": r["cited"]["value"],
                "creation": r["creation"]["value"],
                "timespan": r["timespan"]["value"],
                "journal_sc": r["journal_sc"]["value"],
                "author_sc": r["author_sc"]["value"],
            })
        
        return pd.DataFrame(rows)


    def getAllJournalSelfCitations(self):
        sparql = SPARQLWrapper(self.dbPathOrUrl)
        sparql.setReturnFormat(JSON)

        sparql.setQuery("""
            PREFIX cito: <http://purl.org/spar/cito/>
            
            SELECT ?citation ?citing ?cited ?creation ?timespan ?journal_sc ?author_sc
            WHERE {
                ?citation a cito:Citation ;
                    cito:hasCitingEntity ?citing ;
                    cito:hasCitedEntity ?cited ;
                    cito:hasCreationDate ?creation ;
                    cito:hasTimespan ?timespan ;
                    cito:isJournalSelfCitation ?journal_sc ;
                    cito:isAuthorSelfCitation ?author_sc .
                FILTER(?journal_sc = "yes")
            }
        """)

        results = sparql.query().convert()

        rows = []
        for r in results["results"]["bindings"]:
            rows.append({
                "citation": r["citation"]["value"],
                "citing": r["citing"]["value"],
                "cited": r["cited"]["value"],
                "creation": r["creation"]["value"],
                "timespan": r["timespan"]["value"],
                "journal_sc": r["journal_sc"]["value"],
                "author_sc": r["author_sc"]["value"],
            })
        
        return pd.DataFrame(rows)

    def getCitationsWithinTimespan(self, min_timespan, max_timespan):
        sparql = SPARQLWrapper(self.dbPathOrUrl)
        sparql.setReturnFormat(JSON)

        #Costruisco il FILTER in base ai parametri ricevuti
        filters = []
        if min_timespan:
            filters.append(f'?timespan >= "{min_timespan}"')
        if max_timespan:
            filters.append(f'?timespan <= "{max_timespan}"')
        
        filter_clause = f"FILTER({' && '.join(filters)})" if filters else ""

        sparql.setQuery(f"""
            PREFIX cito: <http://purl.org/spar/cito/>
            
            SELECT ?citation ?citing ?cited ?creation ?timespan ?journal_sc ?author_sc
            WHERE {{
                ?citation a cito:Citation ;
                    cito:hasCitingEntity ?citing ;
                    cito:hasCitedEntity ?cited ;
                    cito:hasCreationDate ?creation ;
                    cito:hasTimespan ?timespan ;
                    cito:isJournalSelfCitation ?journal_sc ;
                    cito:isAuthorSelfCitation ?author_sc .
                {filter_clause}
            }}
        """)

        results = sparql.query().convert()

        rows = []
        for r in results["results"]["bindings"]:
            rows.append({
                "citation": r["citation"]["value"],
                "citing": r["citing"]["value"],
                "cited": r["cited"]["value"],
                "creation": r["creation"]["value"],
                "timespan": r["timespan"]["value"],
                "journal_sc": r["journal_sc"]["value"],
                "author_sc": r["author_sc"]["value"],
            })
        
        return pd.DataFrame(rows)

    def getCitationsWithinDate(self, start_date, end_date):
        sparql = SPARQLWrapper(self.dbPathOrUrl)
        sparql.setReturnFormat(JSON)

        #Costruisco il FILTER in base ai parametri ricevuti
        filters = []
        if start_date:
            filters.append(f'?creation >= "{start_date}"')
        if end_date:
            filters.append(f'?creation <= "{end_date}"')
        
        filter_clause = f"FILTER({' && '.join(filters)})" if filters else ""

        sparql.setQuery(f"""
            PREFIX cito: <http://purl.org/spar/cito/>
            
            SELECT ?citation ?citing ?cited ?creation ?timespan ?journal_sc ?author_sc
            WHERE {{
                ?citation a cito:Citation ;
                    cito:hasCitingEntity ?citing ;
                    cito:hasCitedEntity ?cited ;
                    cito:hasCreationDate ?creation ;
                    cito:hasTimespan ?timespan ;
                    cito:isJournalSelfCitation ?journal_sc ;
                    cito:isAuthorSelfCitation ?author_sc .
                {filter_clause}
            }}
        """)

        results = sparql.query().convert()

        rows = []
        for r in results["results"]["bindings"]:
            rows.append({
                "citation": r["citation"]["value"],
                "citing": r["citing"]["value"],
                "cited": r["cited"]["value"],
                "creation": r["creation"]["value"],
                "timespan": r["timespan"]["value"],
                "journal_sc": r["journal_sc"]["value"],
                "author_sc": r["author_sc"]["value"],
            })
        
        return pd.DataFrame(rows)

# ===============================================================================
# BibliographicEntityQueryHandler - PARTE DI ADRIANA
# Interroga il database relazionale e restituisce DataFrame
# ===============================================================================

class BibliographicEntityQueryHandler(QueryHandler):
    def __init__(self):
        super().__init__()

    def getById(self, id):
        pass

    def getAllBibliographicEntities(self):
        pass

    def getBibliographicEntitiesWithTitle(self, title):
        pass

    def getBibliographicEntitiesWithAuthor(self, author):
        pass

    def getBibliographicEntitiesWithinPublicationDate(self, start_date, end_date):
        pass

    def getBibliographicEntitiesWithVenue(self, venue):
        pass



# TEST CHE CARICA TUTTO SU BLAZEGRAPH, IL RISULTATO è TOT 92022, mi conta tutti i file del csv (se ho capito bene)
#cit = CitationUploadHandler()
#cit.setDbPathOrUrl("http://localhost:9999/blazegraph/sparql")
#cit.pushDataToDb("dh_citations.csv")
#print("Caricamento completato!")

#TEST getAllCitations, questo restituisce una tabella di 13.146 righe e 7 colonne, cioò i dati del csv caricato, ma attraverso Blazegraph (quindi credo mi confermi che il blazegraph sia stato popolato correttamente)
cit_qh = CitationQueryHandler()
cit_qh.setDbPathOrUrl("http://localhost:9999/blazegraph/sparql")
result = cit_qh.getAllCitations()
print(result)
print("Righe totali:", len(result))

#TEST getCitationsWithinTimespan
result2 = cit_qh.getCitationsWithinTimespan("P1Y", "P5Y")
print(result2)
print("Righe con timespan tra 1 e 5 anni:", len(result2))

#TEST getCitationsWithinDate
result3 = cit_qh.getCitationsWithinDate("2010", "2015")
print(result3)
print("Righe con data tra 2010 e 2015:", len(result3))