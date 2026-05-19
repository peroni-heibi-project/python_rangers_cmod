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

#Alice - qua sotto ho modificato cosine, cancellato il richiamo della classe che era stato fatto due volte, ho corretto anche un altro pushDatatoDb in pushDataToDb    
    
class CitationUploadHandler(UploadHandler):
    def __init__(self, dbPathOrUrl:str = ""):
        super().__init__(dbPathOrUrl)
    
    def pushDataToDb(self, path:str) -> bool:
        if type(path) == str:
            df = pd.read_csv(path, keep_default_na=None)

            sparql = SPARQLWrapper(self.dbPathOrUrl)
            sparql.setMethod("POST")

            for _, row in df.iterrows():
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
        return False
    
class BibliographicEntityUploadHandler(UploadHandler):

    def __init__(self, dbPathOrUrl:str = ""):
        super().__init__(dbPathOrUrl)

    def pushDataToDb(self, path:str) -> bool:
        if type(path) == str:
            with open(path, "r", encoding="utf-8") as f:
                data = load(f)   # lista di dizionari
                
            rows_entity    = list()
            for dic in data:
                if dic.id:
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
                    be.id
                FROM BibliographicEntity AS be
                WHERE be.id = ?
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
                        
            if len(beginning) == 0 and len(end) == 0:
                return result
            
            else:
                if len(beginning) > 0:
                    min = timespan_to_days(beginning)
                    for idx, row in result.iterrows():
                        t = timespan_to_days(row["timespan"])
                        if not(min <= t <= max):
                            result.drop(idx, axis=0, inplace=True)
                    result.reset_index(drop=True, inplace=True)

                if len(end) > 0:
                    max = timespan_to_days(end)
                    for idx, row in result.iterrows():
                        t = timespan_to_days(row["timespan"])
                        if not(t <= max):
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
    
    def constructBibliographicEntity(self, row:pd.Series) -> BibliographicEntity:
        #additional function made to avoid repetitions in the code
        auth = row["author"].split("; ") if row["author"] != None else None
        i = row["id"].split("; ")

        bib_en = BibliographicEntity(title=row["title"],
                                    author= auth,
                                    id= i,
                                    publication_date=row["pub_date"],
                                    venue=row["venue"])
        return bib_en
    
    def constructCitation(self, row:pd.Series) -> Citation:
        #additional function made to avoid repetitions in the code
        auth_citing = row["author_citing"].split("; ") if row["author_citing"] != None else None
        i_citing = row["id_citing"].split("; ")

        auth_cited = row["author_cited"].split("; ") if row["author_cited"] != None else None
        i_cited = row["id_cited"].split("; ")

        citing = None
        cited = None

        if row["citing"]:
            citing = BibliographicEntity(title=row["title_citing"],
                                         author= auth_citing,
                                         id= i_citing,
                                         publication_date=row["pub_date_citing"],
                                         venue=row["venue_citing"])
        
        if row["cited"]:
            cited = BibliographicEntity(title=row["title_cited"],
                                        author= auth_cited,
                                        id= i_cited,
                                        publication_date=row["pub_date_cited"],
                                        venue=row["venue_cited"])
        
        cit = Citation(id=row["oci"],
                       creation=row["creation"],
                       timespan=row["timespan"],
                       hasCitingEntry=citing,
                       hasCitedEntry=cited)
        
        return cit
        
    def setFullDataFrame(self, be_df:pd.DataFrame, cit_df:pd.DataFrame) -> pd.DataFrame:
        mom_be = be_df
        prefix = "https://opencitations.net/entity/"
        mom_be["internalId"] = mom_be["internalId"].apply(lambda x: prefix + x)

        full_df = cit_df
        if full_df["citing"]:
            citing_df = mom_be.rename(columns={#"internalId":"InternalId_citing",
                                            "title":"title_citing",
                                            "author":"author_citing",
                                            "pub_date":"pub_date_citing",
                                            "venue":"venue_citing",
                                            "id":"id_citing"})
            
            full_df = pd.merge(full_df, citing_df, left_on="citing", right_on="internalId", how="inner")
        
        if full_df["cited"]:
            cited_df = mom_be.rename(columns={#"internalId":"internalId_cited",
                                            "title":"title_cited",
                                            "author":"author_cited",
                                            "pub_date":"pub_date_cited",
                                            "venue":"venue_cited",
                                            "id":"id_cited"})
            
            full_df = pd.merge(full_df, cited_df, left_on="cited", right_on="internalId", how="inner")

        return full_df

    def getEntityById(self, id:str):
        be_qhandler = self.bibliographicEntityQuery
        df_be = pd.DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
    
        for item in be_qhandler:
            merge_be = pd.concat([df_be, item.getAllBibliographicEntities()])

        if id[0].isalpha(): #Andrea: forse da metterci caso stringa vuota?
            for idx, row in merge_be.iterrows():
                if id in row["id"]:
                    return self.constructBibliographicEntity(row)
                
        else:
            ci_qhandler = self.citationQuery
            df_ci = pd.DataFrame(columns=["oci", "creation", "citing", "cited", "timespan"])
            for item in ci_qhandler:
                merge_cit = pd.concat([df_ci, item.getAllCitations()])

            full_df = self.setFullDataFrame(merge_be, merge_cit)

            for idx, row_ci in full_df.iterrows():
                if row_ci["oci"] == id:
                    return self.constructCitation(row)

        return None


    def constructCitationOld(self, row:pd.Series, be_df:pd.DataFrame, cit_df:pd.DataFrame) -> Citation:
        #additional function made to avoid repetitions in the code
        citing_id = None
        cited_id = None
        if row["citing"]:
            citing_id = row["citing"][33::]
        if row["cited"]:
            cited_id = row["cited"][33::]
        bib_elements = self.constructCitatingAndCited(be_df, citing_id, cited_id)
        cit = Citation(id=row["oci"],
                       creation=row["creation"],
                       timespan=row["timespan"],
                       hasCitingEntry=bib_elements[0],
                       hasCitedEntry=bib_elements[1])
        return cit
    
    
    def constructCitationList(self, df:pd.DataFrame) -> list:
        #additional function made to avoid repetitions in the code
        list_of_ci = list()

        for idx, row in df.iterrows():

            citing = self.getEntityById(row["citing"])
            cited = self.getEntityById(row["cited"])
            cit = Citation(id=row["oci"],
                           creation=row["creation"],
                           timespan=row["timespan"],
                           hasCitingEntry=citing,
                           hasCitedEntry=cited)
            
            list_of_ci.append(cit)
        return list_of_ci

    def constructBibliographicEntityList(self, df:pd.DataFrame) -> list:
        #additional function made to avoid repetitions in the code
        list_of_be = list()
        for idx, row in df.iterrows():
            auth = row["author"].split("; ") if row["author"] != None else None
            if len(row["id"]) > 0:
                i = row["id"].split("; ")

            bib_en = BibliographicEntity(title=row["title"],
                                        author= auth,
                                        id= i,
                                        publication_date=row["pub_date"],
                                        venue=row["venue"])
            list_of_be.append(bib_en)
        return list_of_be


    def getAllCitations(self) -> list:
        pass

    def getAllAuthorSelfCitations(self) -> list:
        result = list()

        be_qhandler = self.bibliographicEntityQuery
        df_be = pd.DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be = pd.concat([df_be, item.getAllBibliographicEntities()])

        ci_qhandler = self.citationQuery
        df_ci = pd.DataFrame(columns=["oci", "creation", "citing", "cited", "timespan"])
        for item in ci_qhandler:
            merge_asc = pd.concat([df_ci, item.getAllAuthorSelfCitations()])

        full_df = self.setFullDataFrame(merge_be, merge_asc)

        for idx, row in full_df.iterrows():
            auth_citing = row["author_citing"].split("; ") if row["author_citing"] != None else None
            i_citing = row["id_citing"].split("; ")

            auth_cited = row["author_cited"].split("; ") if row["author_cited"] != None else None
            i_cited = row["id_cited"].split("; ")

            citing = BibliographicEntity(title=row["title_citing"],
                                         author= auth_citing,
                                         id= i_citing,
                                         publication_date=row["pub_date_citing"],
                                         venue=row["venue_citing"])
            
            cited = BibliographicEntity(title=row["title_cited"],
                                        author= auth_cited,
                                        id= i_cited,
                                        publication_date=row["pub_date_cited"],
                                        venue=row["venue_cited"])
            
            asc = AuthorSelfCitation(id=row["oci"],
                                     creation=row["creation"],
                                     timespan=row["timespan"],
                                     hasCitingEntry=citing,
                                     hasCitedEntry=cited)

            result.append(asc)

        return result

    def getAllJournalSelfCitations(self) -> list:
        result = list()

        be_qhandler = self.bibliographicEntityQuery
        df_be = pd.DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be = pd.concat([df_be, item.getAllBibliographicEntities()])

        ci_qhandler = self.citationQuery
        df_ci = pd.DataFrame(columns=["oci", "creation", "citing", "cited", "timespan"])
        for item in ci_qhandler:
            merge_jsc = pd.concat([df_ci, item.getAllJournalSelfCitations()])

        final_df = self.setFullDataFrame(merge_be, merge_jsc)

        for idx, row in final_df.iterrows():
            auth_citing = row["author_citing"].split("; ") if row["author_citing"] != None else None
            i_citing = row["id_citing"].split("; ")

            auth_cited = row["author_cited"].split("; ") if row["author_cited"] != None else None
            i_cited = row["id_cited"].split("; ")

            citing = BibliographicEntity(title=row["title_citing"],
                                         author= auth_citing,
                                         id= i_citing,
                                         publication_date=row["pub_date_citing"],
                                         venue=row["venue_citing"])
            
            cited = BibliographicEntity(title=row["title_cited"],
                                        author= auth_cited,
                                        id= i_cited,
                                        publication_date=row["pub_date_cited"],
                                        venue=row["venue_cited"])
            
            jsc = JournalSelfCitation(id=row["oci"],
                                      creation=row["creation"],
                                      timespan=row["timespan"],
                                      hasCitingEntry=citing,
                                      hasCitedEntry=cited)

            result.append(jsc)

        return result

    def getAllJournalSelfCitationsOld(self) -> list:
        result = list()

        be_qhandler = self.bibliographicEntityQuery
        df_be = pd.DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be = pd.concat([df_be, item.getAllBibliographicEntities()])

        ci_qhandler = self.citationQuery
        df_ci = pd.DataFrame(columns=["oci", "creation", "citing", "cited", "timespan"])
        for item in ci_qhandler:
            merge_jsc = pd.concat([df_ci, item.getAllJournalSelfCitations()])

        for idx, row in merge_jsc.iterrows():
            citing_id = None
            cited_id = None
            if row["citing"]:
                citing_id = row["citing"][33::]
            if row["cited"]:
                cited_id = row["cited"][33::]
            bib_elements = self.constructCitatingAndCited(merge_be, citing_id, cited_id)
            jsc = JournalSelfCitation(id=row["oci"],
                                      creation=row["creation"],
                                      timespan=row["timespan"],
                                      hasCitingEntry=bib_elements[0],
                                      hasCitedEntry=bib_elements[1])
            result.append(jsc)
        
        return result
    

    def getCitationsWithinTimespan(self, min_time:str, max_time:str) -> list:
        pass

    def getCitationsWithinDate(self, start_date:str, end_date:str) -> list:
        pass

    
    def getAllBibliographicEntities(self) -> list:
        result = list()
        be_qhandler = self.bibliographicEntityQuery
        df_be = pd.DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be = pd.concat([df_be, item.getAllBibliographicEntities()])

        for idx, row in merge_be.iterrows():
            result.append(self.constructBibliographicEntity(row))
        return result

    def getBibliographicEntitiesWithTitle(self, title:str) -> list:
        result = list()
        be_qhandler = self.bibliographicEntityQuery
        df_be = pd.DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be = pd.concat([df_be, item.getBibliographicEntitiesWithTitle(title)])

        for idx, row in merge_be.iterrows():
            result.append(self.constructBibliographicEntity(row))
        return result

    def getBibliographicEntitiesWithAuthor(self, author:str) -> list:
        result = list()
        be_qhandler = self.bibliographicEntityQuery
        df_be = pd.DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be = pd.concat([df_be, item.getBibliographicEntitiesWithAuthor(author)])

        for idx, row in merge_be.iterrows():
            result.append(self.constructBibliographicEntity(row))
        return result

    def getBibliographicEntitiesWithinPublicationDate(self, start_date:str = None, end_date:str = None) -> list:
        result = list()
        be_qhandler = self.bibliographicEntityQuery
        df_be = pd.DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be = pd.concat([df_be, item.getBibliographicEntitiesWithinPublicationDate(start_date, end_date)])

        for idx, row in merge_be.iterrows():
            result.append(self.constructBibliographicEntity(row))
        return result
    
    def getBibliographicEntitiesWithVenue(self, venue:str) -> list:
        result = list()
        be_qhandler = self.bibliographicEntityQuery
        df_be = pd.DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be = pd.concat([df_be, item.getBibliographicEntitiesWithVenue(venue)])

        for idx, row in merge_be.iterrows():
            result.append(self.constructBibliographicEntity(row))
        return result
    

class FullQueryEngine(BasicQueryEngine):
    def __init__(self, citationQuery:list = [], bibliographicEntityQuery:list = []):
        super().__init__(citationQuery, bibliographicEntityQuery)

    def getAuthorSelfCitationsByName(self, author_name:str) -> list:
        pass

    def getJournalSelfCitationsByName(self, journal_name:str) -> list:
        result = list()
        jsc_list = self.getAllJournalSelfCitations()
        for jsc in jsc_list:
            if jsc.getCitingEntry().getVenue() == journal_name and jsc.getCitedEntry().getVenue() == journal_name:
                result.append(jsc)
        return result

    def getCitationsOfBibEntityByTitleWithinDate(self, bib_entity_title:str, min_date:str, max_date:str) -> list:
        result = list()
        be_qhandler = self.bibliographicEntityQuery
        ci_qhandler = self.citationQuery
        df_be = pd.DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        df_ci = pd.DataFrame(columns=["oci", "creation", "citing", "cited", "timespan"])

        for item in be_qhandler:
            merge_be = pd.concat([df_be, item.getBibliographicEntitiesWithTitle(bib_entity_title)])
            
        for item in ci_qhandler:
            merge_ci = pd.concat([df_ci, item.getCitationsWithinTimespan(min_date, max_date)])
        
        prefix = "https://opencitations.net/entity/"
        merge_be["internalId"] = merge_be["internalId"].apply(lambda x: prefix + x)

        new_df = pd.merge(merge_be, merge_ci, left_on="internalId", right_on="cited", how="inner")

        for idx, row in new_df.iterrows():
            row_be = new_df.loc[[idx], ["internalId", "title", "author", "pub_date", "venue", "id"]]
            row_cit = new_df.loc[[idx], ("oci", "creation", "citing", "cited", "timespan")]

            ci = self.constructCitationList(row_cit)[0]
            ci.hasCitedEntry = self.constructBibliographicEntityList(row_be)[0]
            result.append(ci)
        return result

    def getReferencesOfBibEntityByTitleWithinTimespan(self, bib_entity_title:str, min_timespan:str, max_timespan:str) -> list:
        pass
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

#Alice - qua sotto ho modificato cosine, cancellato il richiamo della classe che era stato fatto due volte, ho corretto anche un altro pushDatatoDb in pushDataToDb    
    
class CitationUploadHandler(UploadHandler):
    def __init__(self, dbPathOrUrl:str = ""):
        super().__init__(dbPathOrUrl)
    
    def pushDataToDb(self, path:str) -> bool:
        if type(path) == str:
            df = pd.read_csv(path, keep_default_na=None)

            sparql = SPARQLWrapper(self.dbPathOrUrl)
            sparql.setMethod("POST")

            for _, row in df.iterrows():
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
        return False
    
class BibliographicEntityUploadHandler(UploadHandler):

    def __init__(self, dbPathOrUrl:str = ""):
        super().__init__(dbPathOrUrl)

    def pushDataToDb(self, path:str) -> bool:
        if type(path) == str:
            with open(path, "r", encoding="utf-8") as f:
                data = load(f)   # lista di dizionari
                
            rows_entity    = list()
            for dic in data:
                if dic.id:
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
                    be.id
                FROM BibliographicEntity AS be
                WHERE be.id = ?
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
                        
            if len(beginning) == 0 and len(end) == 0:
                return result
            
            else:
                if len(beginning) > 0:
                    min = timespan_to_days(beginning)
                    for idx, row in result.iterrows():
                        t = timespan_to_days(row["timespan"])
                        if not(min <= t <= max):
                            result.drop(idx, axis=0, inplace=True)
                    result.reset_index(drop=True, inplace=True)

                if len(end) > 0:
                    max = timespan_to_days(end)
                    for idx, row in result.iterrows():
                        t = timespan_to_days(row["timespan"])
                        if not(t <= max):
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
    
    def constructBibliographicEntity(self, row:pd.Series) -> BibliographicEntity:
        #additional function made to avoid repetitions in the code
        auth = row["author"].split("; ") if row["author"] != None else None
        i = row["id"].split("; ")

        bib_en = BibliographicEntity(title=row["title"],
                                    author= auth,
                                    id= i,
                                    publication_date=row["pub_date"],
                                    venue=row["venue"])
        return bib_en
    
    def constructCitation(self, row:pd.Series) -> Citation:
        #additional function made to avoid repetitions in the code
        auth_citing = row["author_citing"].split("; ") if row["author_citing"] != None else None
        i_citing = row["id_citing"].split("; ")

        auth_cited = row["author_cited"].split("; ") if row["author_cited"] != None else None
        i_cited = row["id_cited"].split("; ")

        citing = None
        cited = None

        if row["citing"]:
            citing = BibliographicEntity(title=row["title_citing"],
                                         author= auth_citing,
                                         id= i_citing,
                                         publication_date=row["pub_date_citing"],
                                         venue=row["venue_citing"])
        
        if row["cited"]:
            cited = BibliographicEntity(title=row["title_cited"],
                                        author= auth_cited,
                                        id= i_cited,
                                        publication_date=row["pub_date_cited"],
                                        venue=row["venue_cited"])
        
        cit = Citation(id=row["oci"],
                       creation=row["creation"],
                       timespan=row["timespan"],
                       hasCitingEntry=citing,
                       hasCitedEntry=cited)
        
        return cit
        

    def getEntityById(self, id:str):
        be_qhandler = self.bibliographicEntityQuery
        df_be = pd.DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
    
        for item in be_qhandler:
            merge_be = pd.concat([df_be, item.getAllBibliographicEntities()])

        if id[0].isalpha(): #Andrea: forse da metterci caso stringa vuota?
            for idx, row in merge_be.iterrows():
                if id in row["id"]:
                    return self.constructBibliographicEntity(row)
                
        else:
            ci_qhandler = self.citationQuery
            df_ci = pd.DataFrame(columns=["oci", "creation", "citing", "cited", "timespan"])
            for item in ci_qhandler:
                merge_cit = pd.concat([df_ci, item.getAllCitations()])

            prefix = "https://opencitations.net/entity/"
            merge_be["internalId"] = merge_be["internalId"].apply(lambda x: prefix + x)

            final_df = merge_cit
            if final_df["citing"]:
                citing_df = merge_be.rename(columns={#"internalId":"InternalId_citing",
                                                "title":"title_citing",
                                                "author":"author_citing",
                                                "pub_date":"pub_date_citing",
                                                "venue":"venue_citing",
                                                "id":"id_citing"})
                
                final_df = pd.merge(merge_cit, citing_df, left_on="citing", right_on="internalId", how="inner")
            
            if final_df["cited"]:
                cited_df = merge_be.rename(columns={#"internalId":"internalId_cited",
                                                "title":"title_cited",
                                                "author":"author_cited",
                                                "pub_date":"pub_date_cited",
                                                "venue":"venue_cited",
                                                "id":"id_cited"})
                
                final_df = pd.merge(merge_cit, cited_df, left_on="cited", right_on="internalId", how="inner")

            for idx, row_ci in final_df.iterrows():
                if row_ci["oci"] == id:
                    return self.constructCitation(row)

        return None


    def constructCitationOld(self, row:pd.Series, be_df:pd.DataFrame, cit_df:pd.DataFrame) -> Citation:
        #additional function made to avoid repetitions in the code
        citing_id = None
        cited_id = None
        if row["citing"]:
            citing_id = row["citing"][33::]
        if row["cited"]:
            cited_id = row["cited"][33::]
        bib_elements = self.constructCitatingAndCited(be_df, citing_id, cited_id)
        cit = Citation(id=row["oci"],
                       creation=row["creation"],
                       timespan=row["timespan"],
                       hasCitingEntry=bib_elements[0],
                       hasCitedEntry=bib_elements[1])
        return cit
    
    
    def constructCitationList(self, df:pd.DataFrame) -> list:
        #additional function made to avoid repetitions in the code
        list_of_ci = list()

        for idx, row in df.iterrows():

            citing = self.getEntityById(row["citing"])
            cited = self.getEntityById(row["cited"])
            cit = Citation(id=row["oci"],
                           creation=row["creation"],
                           timespan=row["timespan"],
                           hasCitingEntry=citing,
                           hasCitedEntry=cited)
            
            list_of_ci.append(cit)
        return list_of_ci

    def constructBibliographicEntityList(self, df:pd.DataFrame) -> list:
        #additional function made to avoid repetitions in the code
        list_of_be = list()
        for idx, row in df.iterrows():
            auth = row["author"].split("; ") if row["author"] != None else None
            if len(row["id"]) > 0:
                i = row["id"].split("; ")

            bib_en = BibliographicEntity(title=row["title"],
                                        author= auth,
                                        id= i,
                                        publication_date=row["pub_date"],
                                        venue=row["venue"])
            list_of_be.append(bib_en)
        return list_of_be


    def getAllCitations(self) -> list:
        pass

    def getAllAuthorSelfCitations(self) -> list:
        result = list()

        be_qhandler = self.bibliographicEntityQuery
        df_be = pd.DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be = pd.concat([df_be, item.getAllBibliographicEntities()])

        ci_qhandler = self.citationQuery
        df_ci = pd.DataFrame(columns=["oci", "creation", "citing", "cited", "timespan"])
        for item in ci_qhandler:
            merge_asc = pd.concat([df_ci, item.getAllAuthorSelfCitations()])

        prefix = "https://opencitations.net/entity/"
        merge_be["internalId"] = merge_be["internalId"].apply(lambda x: prefix + x)

        final_df = merge_asc
        if final_df["citing"]:
            citing_df = merge_be.rename(columns={#"internalId":"InternalId_citing",
                                             "title":"title_citing",
                                             "author":"author_citing",
                                             "pub_date":"pub_date_citing",
                                             "venue":"venue_citing",
                                             "id":"id_citing"})
            
            final_df = pd.merge(merge_asc, citing_df, left_on="citing", right_on="internalId", how="inner")
        
        if final_df["cited"]:
            cited_df = merge_be.rename(columns={#"internalId":"internalId_cited",
                                            "title":"title_cited",
                                            "author":"author_cited",
                                            "pub_date":"pub_date_cited",
                                            "venue":"venue_cited",
                                            "id":"id_cited"})
            
            final_df = pd.merge(merge_asc, cited_df, left_on="cited", right_on="internalId", how="inner")

        for idx, row in final_df.iterrows():
            auth_citing = row["author_citing"].split("; ") if row["author_citing"] != None else None
            i_citing = row["id_citing"].split("; ")

            auth_cited = row["author_cited"].split("; ") if row["author_cited"] != None else None
            i_cited = row["id_cited"].split("; ")

            citing = BibliographicEntity(title=row["title_citing"],
                                         author= auth_citing,
                                         id= i_citing,
                                         publication_date=row["pub_date_citing"],
                                         venue=row["venue_citing"])
            
            cited = BibliographicEntity(title=row["title_cited"],
                                        author= auth_cited,
                                        id= i_cited,
                                        publication_date=row["pub_date_cited"],
                                        venue=row["venue_cited"])
            
            jsc = AuthorSelfCitation(id=row["oci"],
                                      creation=row["creation"],
                                      timespan=row["timespan"],
                                      hasCitingEntry=citing,
                                      hasCitedEntry=cited)

            result.append(jsc)

        return result

    def getAllJournalSelfCitations(self) -> list:
        result = list()

        be_qhandler = self.bibliographicEntityQuery
        df_be = pd.DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be = pd.concat([df_be, item.getAllBibliographicEntities()])

        ci_qhandler = self.citationQuery
        df_ci = pd.DataFrame(columns=["oci", "creation", "citing", "cited", "timespan"])
        for item in ci_qhandler:
            merge_jsc = pd.concat([df_ci, item.getAllJournalSelfCitations()])

        prefix = "https://opencitations.net/entity/"
        merge_be["internalId"] = merge_be["internalId"].apply(lambda x: prefix + x)

        final_df = merge_jsc
        if final_df["citing"]:
            citing_df = merge_be.rename(columns={#"internalId":"InternalId_citing",
                                             "title":"title_citing",
                                             "author":"author_citing",
                                             "pub_date":"pub_date_citing",
                                             "venue":"venue_citing",
                                             "id":"id_citing"})
            
            final_df = pd.merge(merge_jsc, citing_df, left_on="citing", right_on="internalId", how="inner")
        
        if final_df["cited"]:
            cited_df = merge_be.rename(columns={#"internalId":"internalId_cited",
                                            "title":"title_cited",
                                            "author":"author_cited",
                                            "pub_date":"pub_date_cited",
                                            "venue":"venue_cited",
                                            "id":"id_cited"})
            
            final_df = pd.merge(merge_jsc, cited_df, left_on="cited", right_on="internalId", how="inner")

        for idx, row in final_df.iterrows():
            auth_citing = row["author_citing"].split("; ") if row["author_citing"] != None else None
            i_citing = row["id_citing"].split("; ")

            auth_cited = row["author_cited"].split("; ") if row["author_cited"] != None else None
            i_cited = row["id_cited"].split("; ")

            citing = BibliographicEntity(title=row["title_citing"],
                                         author= auth_citing,
                                         id= i_citing,
                                         publication_date=row["pub_date_citing"],
                                         venue=row["venue_citing"])
            
            cited = BibliographicEntity(title=row["title_cited"],
                                        author= auth_cited,
                                        id= i_cited,
                                        publication_date=row["pub_date_cited"],
                                        venue=row["venue_cited"])
            
            jsc = JournalSelfCitation(id=row["oci"],
                                      creation=row["creation"],
                                      timespan=row["timespan"],
                                      hasCitingEntry=citing,
                                      hasCitedEntry=cited)

            result.append(jsc)

        return result

    def getAllJournalSelfCitationsOld(self) -> list:
        result = list()

        be_qhandler = self.bibliographicEntityQuery
        df_be = pd.DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be = pd.concat([df_be, item.getAllBibliographicEntities()])

        ci_qhandler = self.citationQuery
        df_ci = pd.DataFrame(columns=["oci", "creation", "citing", "cited", "timespan"])
        for item in ci_qhandler:
            merge_jsc = pd.concat([df_ci, item.getAllJournalSelfCitations()])

        for idx, row in merge_jsc.iterrows():
            citing_id = None
            cited_id = None
            if row["citing"]:
                citing_id = row["citing"][33::]
            if row["cited"]:
                cited_id = row["cited"][33::]
            bib_elements = self.constructCitatingAndCited(merge_be, citing_id, cited_id)
            jsc = JournalSelfCitation(id=row["oci"],
                                      creation=row["creation"],
                                      timespan=row["timespan"],
                                      hasCitingEntry=bib_elements[0],
                                      hasCitedEntry=bib_elements[1])
            result.append(jsc)
        
        return result
    

    def getCitationsWithinTimespan(self, min_time:str, max_time:str) -> list:
        pass

    def getCitationsWithinDate(self, start_date:str, end_date:str) -> list:
        pass

    
    def getAllBibliographicEntities(self) -> list:
        result = list()
        be_qhandler = self.bibliographicEntityQuery
        df_be = pd.DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be = pd.concat([df_be, item.getAllBibliographicEntities()])

        for idx, row in merge_be.iterrows():
            result.append(self.constructBibliographicEntity(row))
        return result

    def getBibliographicEntitiesWithTitle(self, title:str) -> list:
        result = list()
        be_qhandler = self.bibliographicEntityQuery
        df_be = pd.DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be = pd.concat([df_be, item.getBibliographicEntitiesWithTitle(title)])

        for idx, row in merge_be.iterrows():
            result.append(self.constructBibliographicEntity(row))
        return result

    def getBibliographicEntitiesWithAuthor(self, author:str) -> list:
        result = list()
        be_qhandler = self.bibliographicEntityQuery
        df_be = pd.DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be = pd.concat([df_be, item.getBibliographicEntitiesWithAuthor(author)])

        for idx, row in merge_be.iterrows():
            result.append(self.constructBibliographicEntity(row))
        return result

    def getBibliographicEntitiesWithinPublicationDate(self, start_date:str = None, end_date:str = None) -> list:
        result = list()
        be_qhandler = self.bibliographicEntityQuery
        df_be = pd.DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be = pd.concat([df_be, item.getBibliographicEntitiesWithinPublicationDate(start_date, end_date)])

        for idx, row in merge_be.iterrows():
            result.append(self.constructBibliographicEntity(row))
        return result
    
    def getBibliographicEntitiesWithVenue(self, venue:str) -> list:
        result = list()
        be_qhandler = self.bibliographicEntityQuery
        df_be = pd.DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be = pd.concat([df_be, item.getBibliographicEntitiesWithVenue(venue)])

        for idx, row in merge_be.iterrows():
            result.append(self.constructBibliographicEntity(row))
        return result
    

class FullQueryEngine(BasicQueryEngine):
    def __init__(self, citationQuery:list = [], bibliographicEntityQuery:list = []):
        super().__init__(citationQuery, bibliographicEntityQuery)

    def getAuthorSelfCitationsByName(self, author_name:str) -> list:
        pass

    def getJournalSelfCitationsByName(self, journal_name:str) -> list:
        result = list()
        jsc_list = self.getAllJournalSelfCitations()
        for jsc in jsc_list:
            if jsc.getCitingEntry().getVenue() == journal_name and jsc.getCitedEntry().getVenue() == journal_name:
                result.append(jsc)
        return result

    def getCitationsOfBibEntityByTitleWithinDate(self, bib_entity_title:str, min_date:str, max_date:str) -> list:
        result = list()
        be_qhandler = self.bibliographicEntityQuery
        ci_qhandler = self.citationQuery
        df_be = pd.DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        df_ci = pd.DataFrame(columns=["oci", "creation", "citing", "cited", "timespan"])

        for item in be_qhandler:
            merge_be = pd.concat([df_be, item.getBibliographicEntitiesWithTitle(bib_entity_title)])
            
        for item in ci_qhandler:
            merge_ci = pd.concat([df_ci, item.getCitationsWithinTimespan(min_date, max_date)])
        
        prefix = "https://opencitations.net/entity/"
        merge_be["internalId"] = merge_be["internalId"].apply(lambda x: prefix + x)

        new_df = pd.merge(merge_be, merge_ci, left_on="internalId", right_on="cited", how="inner")

        for idx, row in new_df.iterrows():
            row_be = new_df.loc[[idx], ["internalId", "title", "author", "pub_date", "venue", "id"]]
            row_cit = new_df.loc[[idx], ("oci", "creation", "citing", "cited", "timespan")]

            ci = self.constructCitationList(row_cit)[0]
            ci.hasCitedEntry = self.constructBibliographicEntityList(row_be)[0]
            result.append(ci)
        return result

    def getReferencesOfBibEntityByTitleWithinTimespan(self, bib_entity_title:str, min_timespan:str, max_timespan:str) -> list:
        pass
