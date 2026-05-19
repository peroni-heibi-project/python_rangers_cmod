import pandas as pd
from SPARQLWrapper import SPARQLWrapper, POST
from sparqlite import SPARQLClient
from rdflib.plugins.stores.sparqlstore import SPARQLUpdateStore
import isodate
from json import load
from sqlite3 import connect


#CIAO!

#java -server -Xmx1g -jar blazegraph.jar



class Handler:
    def __init__(self, dbPathOrUrl:str = ""):
        self.dbPathOrUrl = dbPathOrUrl

    def getDbPathOrUrl(self) -> str:
        return self.dbPathOrUrl
    
    def setDbPathOrUrl(self, input:str) -> bool:
        if type(input) == str:
            self.dbPathOrUrl = input
            return True
        return False


class UploadHandler(Handler):
    def __init__(self, dbPathOrUrl:str = ""):
        super().__init__(dbPathOrUrl)

    def pushDataToDb(self, path) -> bool: 
        pass

#Alice - qua sotto ho modificato cosine, cancellato il richiamo della classe che era stato fatto due volte, ho corretto anche un altro pushDatatoDb in pushDataToDb.
#Ho modificato "cito:isAuthorSelfCitation" in "cito:AuthorSelfCitation" perché il predicato non corrispondeva con quello usato nel metodo getAllAuthorSelfCitations in CitationQueryHandler. Stessa cosa per "cito:isJournalSelfCitation". Ora è uniforme. 
    
class CitationUploadHandler(UploadHandler):
    def __init__(self, dbPathOrUrl:str = ""):
        super().__init__(dbPathOrUrl)
    
    def pushDataToDb(self, path:str) -> bool:
        if type(path) == str:
            df = pd.read_csv(path, keep_default_na=None)

            sparql = SPARQLWrapper(self.dbPathOrUrl)
            sparql.setMethod("POST")

            for _, row in df.iterrows():
                #Alice - ho aggiunto il controllo dati obbligatori che dicevamo con Silvia. Tutti i dati del Citation sono obbligatori,
                #se anche solo uno è vuoto, la riga non rispetta i requisiti e non viene caricata nel database, come ci diceva Ivan.
                if not (row["oci"] and row["citing"] and row["cited"] and row["creation"] and row["timespan"] and row ["journal_sc"] and row ["author_sc"]):
                    continue
                    
                citation_uri = f"https://opencitations.net/citation/{row['oci']}"
                query = f"""
                PREFIX cito: <http://purl.org/spar/cito/>
                PREFIX datacite: <http://purl.org/spar/datacite/>
                PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
                PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

                INSERT DATA {{
                    <{citation_uri}> a cito:Citation ;
                        rdfs:label "{row['oci']}"^^xsd:string ; 
                        cito:hasCitingEntity <https://opencitations.net/entity/{row['citing']}> ;
                        cito:hasCitedEntity <https://opencitations.net/entity/{row['cited']}> ;
                        cito:hasCreationDate "{row['creation']}"^^xsd:string ;
                        cito:hasTimespan "{row['timespan']}"^^xsd:string ;
                        cito:JournalSelfCitation "{row['journal_sc']}"^^xsd:string ;
                        cito:AuthorSelfCitation "{row['author_sc']}"^^xsd:string . 
                }}
                """
                    
                sparql.setQuery(query)
                sparql.query()
            return True
    
class BibliographicEntityUploadHandler(UploadHandler):

    def __init__(self, dbPathOrUrl:str = ""):
        super().__init__(dbPathOrUrl)

    def pushDataToDb(self, path:str) -> bool:
        if type(path) == str:
            with open(path, "r", encoding="utf-8") as f:
                data = load(f)   # lista di dizionari
                
            rows_entity    = list()
            for dic in data:
                internal_id = ""
                title    = dic.get("title", "") 
                pub_date = dic.get("pub_date", "") 
                for item in dic["id"]:
                    if "omid" in item:
                        internal_id += item
                entity_id = "; ".join(dic["id"])
                author ="; ".join(dic["author"]) if len(dic["author"]) > 0 else ""
                venue = dic["venue"] if dic["venue"] else ""
                
                rows_entity.append({
                    "internalId": internal_id,
                    "title": title,
                    "author": author,
                    "pub_date": pub_date,
                    "venue" : venue,
                    "id" : entity_id
                })

            df = pd.DataFrame(rows_entity)

            with connect(self.dbPathOrUrl) as con:
                df.to_sql("BibliographicEntity", con,
                                    if_exists="append", index=False)
            return True
        return False

class QueryHandler(Handler):
    def __init__(self, dbPathOrUrl:str = ""):
        super().__init__(dbPathOrUrl)
        
    def getById(self, id) -> pd.DataFrame:
        result = pd.DataFrame()
        if (("omid" in id) or ("doi" in id) or ("openalex" in id) or ("isbn" in id)):
            with connect(self.dbPathOrUrl) as con:
                query = f"""
                SELECT be.internalId, be.title, be.pub_date,
                    ei.id
                FROM BibliographicEntity AS be
                WHERE ei.id = ?
                """
                df = pd.read_sql(query, con, params=(id,))  
                if len(df) == 0:
                    result = df  
        else:
            endpoint = 'http://127.0.0.1:9999/blazegraph/sparql'
            query = f"""
            prefix oci: <https://oci.opencitations.net/virtual/ci/>
            prefix cito: <http://purl.org/spar/cito/>
            SELECT ?oci ?citing ?cited ?creation ?timespan
            WHERE 
                {{?s rdfs:label '{id}' .
                ?s cito:hasCreationDate ?creation .
                ?s cito:hasTimespan ?timespan .
                ?s cito:hasCitingEntity ?citing .
                ?s cito:hasCitedEntity ?cited }}"""
            
            with SPARQLClient(endpoint) as client:
                res = client.query(query)
                variables = res["head"]["vars"]
                rows = list()
                for binding in res["results"]["bindings"]:
                    row = dict()
                    for var in variables:
                        if var in binding:
                            row[var] = binding[var]["value"]
                        else:
                            row[var] = ""
                    rows.append(row)                   
                df = pd.DataFrame(rows)
                if len(df) > 0:
                    result = df
                    result["oci"] = id
            return result 
            
    
#pipi = QueryHandler
#print(QueryHandler.getById(pipi, "lala"))            

class BibliographicEntityQueryHandler(QueryHandler):
    #"""
    #Legge dal database SQLite e restituisce DataFrame pandas.
    #Ogni metodo costruisce una query SQL ed esegue read_sql(), come mostrato
    #dal professore nel capitolo "Interacting with databases using Pandas".
    #"""

    def __init__(self, dbPathOrUrl:str = ""):
        super().__init__(dbPathOrUrl)


    def getAllBibliographicEntities(self) -> pd.DataFrame:
        with connect(self.dbPathOrUrl) as con:
            query = """
                SELECT DISTINCT
                internalId, title, 
                author, pub_date,
                venue, id
                       
                FROM BibliographicEntity
            """
            df = pd.read_sql(query, con)
        return df

    def getBibliographicEntitiesWithTitle(self, title) -> pd.DataFrame:
        # LIKE con % cerca la stringa come sottostringa del titolo
        with connect(self.dbPathOrUrl) as con:
            query = """
                SELECT DISTINCT
                    internalId, title, pub_date, author,
                    id, venue
                FROM BibliographicEntity 
                WHERE title LIKE ?
            """
            df = pd.read_sql(query, con, params=("%" + title + "%",))
        return df

    def getBibliographicEntitiesWithAuthor(self, name) -> pd.DataFrame:
        # DISTINCT evita duplicati se il nome matcha sia givenName che familyName
        with connect(self.dbPathOrUrl) as con:
            query = """
                SELECT DISTINCT
                        internalId, title, pub_date, author,
                       id, venue
                FROM BibliographicEntity 

                WHERE author like ?
            """
            df = pd.read_sql(query, con, params=("%" + name + "%",))
        return df

    def getBibliographicEntitiesWithinPublicationDate(self, start=None, end=None) -> pd.DataFrame:
        # Clausola WHERE costruita dinamicamente: start e end sono opzionali
        conditions = list()
        params     = list()
        if start is not None:
            conditions.append("pub_date >= ?")
            params.append(start)
        if end is not None:
            conditions.append("pub_date <= ?")
            params.append(end)
        where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        with connect(self.dbPathOrUrl) as con:
            query = f"""
                SELECT DISTINCT internalId, title, pub_date, author, venue,
                       id 
                FROM BibliographicEntity 
                {where_clause}
            """
            df = pd.read_sql(query, con, params=params)
        return df

    def getBibliographicEntitiesWithVenue(self, venue) -> pd.DataFrame:
        with connect(self.dbPathOrUrl) as con:
            query = """
                SELECT DISTINCT internalId, title, pub_date, author,
                       id, venue

                FROM BibliographicEntity 

                WHERE venue LIKE ?
            """
            df = pd.read_sql(query, con, params=("%" + venue + "%",))
        return df

    
class CitationQueryHandler(QueryHandler):
    def __init__(self, dbPathOrUrl:str = ""):
        super().__init__(dbPathOrUrl)


    def getAllCitations(self) -> pd.DataFrame:
        endpoint = 'http://127.0.0.1:9999/blazegraph/sparql'
        query = f""" 
        PREFIX cito:<http://purl.org/spar/cito/>
        
        SELECT DISTINCT ?oci ?creation ?citing ?cited ?timespan
        WHERE {{ 
            ?s cito:hasCreationDate ?creation .
            ?s rdfs:label ?oci .
            ?s cito:hasCitingEntity ?citing . 
            ?s cito:hasCitedEntity ?cited . 
            ?s cito:hasTimespan ?timespan}}
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


    def getAllAuthorSelfCitations(self) -> pd.DataFrame:
        endpoint = 'http://127.0.0.1:9999/blazegraph/sparql'
        query = """ PREFIX cito:  <http://purl.org/spar/cito/>
                
            SELECT DISTINCT ?oci ?creation ?citing ?cited ?timespan
            WHERE {{ 
                ?s cito:hasCreationDate ?creation .
                ?s rdfs:label ?oci .
                ?s cito:hasCitingEntity ?citing . 
                ?s cito:hasCitedEntity ?cited . 
                ?s cito:hasTimespan ?timespan . 
            ?s cito:AuthorSelfCitation  ?author_sc . 
            ?s cito:AuthorSelfCitation 'yes' .
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
    
    def getAllJournalSelfCitations(self) -> pd.DataFrame:
        endpoint = 'http://127.0.0.1:9999/blazegraph/sparql'
        query = """ PREFIX cito:  <http://purl.org/spar/cito/>
                
            SELECT DISTINCT ?oci ?creation ?citing ?cited ?timespan
            WHERE {{ 
                ?s cito:hasCreationDate ?creation .
                ?s rdfs:label ?oci .
                ?s cito:hasCitingEntity ?citing . 
                ?s cito:hasCitedEntity ?cited . 
                ?s cito:hasTimespan ?timespan . 
            ?s cito:JournalSelfCitation  ?journal_sc . 
            ?s cito:JournalSelfCitation 'yes' .
            ?s rdfs:label ?label}}"""
        # Alice - Corretto "?s cito:hasCitationCreationDate" in "?s cito:hasCreationDate".
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
    
    def getCitationsWithinTimespan(self, beginning = "", end = "") -> pd.DataFrame:
        endpoint = 'http://127.0.0.1:9999/blazegraph/sparql'
        query = f""" 
        PREFIX cito:  <http://purl.org/spar/cito/>
        
        SELECT DISTINCT ?oci ?creation ?citing ?cited ?timespan
        WHERE {{ 
            ?s cito:hasCreationDate ?creation .
            ?s rdfs:label ?oci .
            ?s cito:hasCitingEntity ?citing . 
            ?s cito:hasCitedEntity ?cited . 
            ?s cito:hasTimespan ?timespan}}
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
            
            t = timespan_to_days(row["timespan"])

            if len(beginning) == 0 and len(end) == 0:
                return result
            
            else:
                if len(beginning) > 0:
                    min = timespan_to_days(beginning)
                    for idx, row in result.iterrows():
                        if t < min:
                            result.drop(idx, axis=0, inplace=True)
                    result.reset_index(drop=True, inplace=True)

                if len(end) > 0:
                    max = timespan_to_days(end)
                    for idx, row in result.iterrows():
                        t = timespan_to_days(row["timespan"])
                        if t > max:
                            result.drop(idx, axis=0, inplace=True)
                    result.reset_index(drop=True, inplace=True)
                return result
            
            
    def getCitationsWithinDate(self, min = "", max = "") -> pd.DataFrame: 
        endpoint = 'http://127.0.0.1:9999/blazegraph/sparql'
        query = f"""
            PREFIX cito:  <http://purl.org/spar/cito/>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

            SELECT DISTINCT ?oci ?creation ?citing ?cited ?timespan
            WHERE {{ 
            ?s cito:hasCreationDate ?creation .
            ?s rdfs:label ?oci .
            ?s cito:hasCitingEntity ?citing . 
            ?s cito:hasCitedEntity ?cited . 
            ?s cito:hasTimespan ?timespan}}
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


class IdentifiableEntity():
    def __init__(self, id):
        self.id = list()
        for single_id in id:
            self.id.append(single_id)

    def getIds(self) -> list:
        return self.id

class BibliographicEntity(IdentifiableEntity):
    def __init__(self, id, title:str = None, author = None, publication_date:str = None, venue:str = None):
        self.title = title
        self.author = list()
        for single_author in author:
            self.author.append(single_author)
        self.publication_date = publication_date
        self.venue = venue
        super().__init__(id)

    def getTitle(self) -> str:
        return self.title
    
    def getAuthors(self) -> list:
        return self.author
    
    def getPublicationDate(self) -> str:
        return self.publication_date
    
    def getVenue(self) -> str:
        return self.venue


class Citation(IdentifiableEntity):
    def __init__(self, id, creation:str, timespan:str, hasCitingEntry:BibliographicEntity = None, hasCitedEntry: BibliographicEntity = None):
        self.creation = creation
        self.timespan = timespan
        self.hasCitingEntry = hasCitingEntry
        self.hasCitedEntry = hasCitedEntry
        super().__init__(id)

    def getCreation(self) -> str:
        return self.creation
    
    def getTimespan(self) -> str:
        return self.timespan
    
    def getCitingEntry(self) -> BibliographicEntity:
        return self.hasCitingEntry

    def getCitedEntry(self) -> BibliographicEntity:
        return self.hasCitedEntry
    
class JournalSelfCitation(Citation):
    def __init__(self, id, creation: str, timespan:str, hasCitingEntry:BibliographicEntity = None, hasCitedEntry: BibliographicEntity = None):
        super().__init__(id, creation, timespan, hasCitingEntry, hasCitedEntry)

class AuthorSelfCitation(Citation):
    def __init__(self, id, creation: str, timespan:str, hasCitingEntry:BibliographicEntity = None, hasCitedEntry: BibliographicEntity = None):
        super().__init__(id, creation, timespan, hasCitingEntry, hasCitedEntry)


class BasicQueryEngine():
    def __init__(self, citationQuery:list = [], bibliographicEntityQuery:list = []):
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
        return False

    def addBibliographicEntityHandler(self, input:BibliographicEntityQueryHandler) -> bool:
        if type(input) == BibliographicEntityQueryHandler:
            self.bibliographicEntityQuery.append(input)
            return True
        return False

    
    def getEntityById(self, id) -> IdentifiableEntity:
        pass
      

    def getAllCitations(self) -> list:
        result = list()
        for handler in self.citationQuery:
            if handler:
                df = handler.getAllCitations()
                result.extend(self.constructCitationList(df))
        return result

    def getAllAuthorSelfCitations(self) -> list:
        result = list()
        for handler in self.citationQuery:
            if handler:
                df = handler.getAllAuthorSelfCitations()
                for idx, row in df.iterrows():
                    cit = AuthorSelfCitation(
                        id=row["oci"],
                        creation=row["creation"],
                        timespan=row["timespan"]
                    )
                    result.append(cit)
        return result

    def getAllJournalSelfCitations(self) -> list:
        result = list()
        for handler in self.citationQuery:
            if handler:
                df = handler.getAllJournalSelfCitations()
                for idx, row in df.iterrows():
                    cit = JournalSelfCitation(
                        id=row["oci"],
                        creation=row["creation"],
                        timespan=row["timespan"]
                    )
                    result.append(cit)
        return result

    def getCitationsWithinTimespan(self, min_timespan:str, max_timespan:str) -> list:
        result = list()
        for handler in self.citationQuery:
            if handler:
                df = handler.getCitationsWithinTimespan(min_timespan, max_timespan)
                result.extend(self.constructCitationList(df))
        return result

    def getCitationsWithinDate(self, start_date:str, end_date:str) -> list:
        result = list()
        for handler in self.citationQuery:
            if handler:
                df = handler.getCitationsWithinDate(start_date, end_date)
                result.extend(self.constructCitationList(df))
        return result

    def constructBibliographicEntityList(self, df:pd.DataFrame) -> list:
        #additional function made to avoid repetitions in the code
        list_of_be = list()
        for idx, row in df.iterrows():
            auth = row["author"].split("; ") if row["author"] != None else None
            if len(row["id"]) > 0:
                i = row["id"].split("; ")

            bib_en = BibliographicEntity(title=row["title"] if row["title"] else None,
                                        author= auth,
                                        id= i,
                                        publication_date=row["pub_date"] if row["pub_date"] else None,
                                        venue=row["venue"] if row["venue"] else None)
            list_of_be.append(bib_en)
        return list_of_be
        
    def constructCitationList(self, df:pd.DataFrame) -> list:
        list_of_ci = list()
        for idx, row in df.iterrows():
            cit = Citation(id=row["oci"], creation=row["creation"], timespan=row["timespan"])
            list_of_ci.append(cit)
        return list_of_ci

    def getAllBibliographicEntities(self) -> list:
        qhandler = self.bibliographicEntityQuery
        result = list()
        for handler in qhandler:
            if handler:
                df = handler.getAllBibliographicEntities()
                result.extend(self.constructBibliographicEntityList(df))
        return result

    def getBibliographicEntitiesWithTitle(self, title:str) -> list:
        qhandler = self.bibliographicEntityQuery
        result = list()
        for handler in qhandler:
            if handler:
                df = handler.getBibliographicEntitiesWithTitle(title)
                result.extend(self.constructBibliographicEntityList(df))
        return result

    def getBibliographicEntitiesWithAuthor(self, author:str) -> list:
        qhandler = self.bibliographicEntityQuery
        result = list()
        for handler in qhandler:
            if handler:
                df = handler.getBibliographicEntitiesWithAuthor(author)
                result.extend(self.constructBibliographicEntityList(df))
        return result

    def getBibliographicEntitiesWithinPublicationDate(self, start_date:str = None, end_date:str = None) -> list:
        qhandler = self.bibliographicEntityQuery
        result = list()
        for handler in qhandler:
            if handler:
                df = handler.getBibliographicEntitiesWithinPublicationDate(start_date, end_date)
                result.extend(self.constructBibliographicEntityList(df))
        return result

    def getBibliographicEntitiesWithVenue(self, venue:str) -> list:
        qhandler = self.bibliographicEntityQuery
        result = list()
        for handler in qhandler:
            if handler:
                df = handler.getBibliographicEntitiesWithVenue(venue)
                result.extend(self.constructBibliographicEntityList(df))
        return result
    

class FullQueryEngine(BasicQueryEngine):
    def __init__(self, citationQuery:list = [], bibliographicEntityQuery:list = []):
        super().__init__(citationQuery, bibliographicEntityQuery)

    def getAuthorSelfCitationsByName(author_name:str) -> list:
        pass

    def getJournalSelfCitationsByName(journal_name:str) -> list:
        result = list()
        asc_list = self.getAllAuthorSelfCitations()
        for asc in asc_list:
            authors_citing = asc.getCitingEntry().getAuthors()
            authors_cited  = asc.getCitedEntry().getAuthors()
            citing_match = any(author_name in a for a in authors_citing)
            cited_match  = any(author_name in a for a in authors_cited)
            if citing_match and cited_match:
                result.append(asc)
        return result

    def getCitationsOfBibEntityByTitleWithinDate(self, bib_entity_title:str, min_date:str, max_date:str) -> list:
        result = list()
        be_qhandler = self.bibliographicEntityQuery
        ci_qhandler = self.citationQuery
        df_be = pd.DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id", "publication_date"])
        df_ci = pd.DataFrame(columns=["oci", "creation", "citing", "cited", "timespan"])

        for item in be_qhandler:
            merge_be = pd.concat([df_be, item.getBibliographicEntitiesWithTitle(bib_entity_title)])
            
        for item in ci_qhandler:
            merge_ci = pd.concat([df_ci, item.getCitationsWithinDate(min_date, max_date)])
        
        prefix = "https://opencitations.net/entity/"
        merge_be["internalId"] = merge_be["internalId"].apply(lambda x: prefix + x)

        new_df = pd.merge(merge_be, merge_ci, left_on="internalId", right_on="cited", how="inner")

        for idx, row in new_df.iterrows():
            row_be = new_df.loc[[idx], ["internalId", "title", "author", "pub_date", "venue", "id", "publication_date"]]
            row_cit = new_df.loc[[idx], ("oci", "creation", "citing", "cited", "timespan")]

            ci = self.constructCitationList(row_cit)[0]
            ci.hasCitedEntry = self.constructBibliographicEntityList(row_be)[0]
            result.append(ci)  
        return result

    def getReferencesOfBibEntityByTitleWithinTimespan(self, bib_entity_title:str, min_timespan:str, max_timespan:str) -> list:
        matching_ids = set()
        for handler in self.bibliographicEntityQuery:
            df = handler.getBibliographicEntitiesWithTitle(bib_entity_title)
            if df is not None and not df.empty:
                for idx, row in df.iterrows():
                    for single_id in row["id"].split("; "):
                        matching_ids.add(single_id.strip())
        if not matching_ids:
            return list()

        result = list()
        for handler in self.citationQuery:
            df = handler.getCitationsWithinTimespan(min_timespan, max_timespan)
            if df is not None and not df.empty:
                for idx, row in df.iterrows():
                    citing = row["citing"]
                    if any(mid in citing for mid in matching_ids):
                        cit = Citation(
                            id=row["oci"],
                            creation=row["creation"],
                            timespan=row["timespan"]
                        )
                        result.append(cit)
        return result

