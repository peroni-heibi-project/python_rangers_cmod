from pandas import DataFrame, Series, read_sql, read_csv, merge, concat, to_datetime
from SPARQLWrapper import SPARQLWrapper, POST
from sparqlite import SPARQLClient
from rdflib.plugins.stores.sparqlstore import SPARQLUpdateStore
import isodate
from json import load
from sqlite3 import connect


#CIAO!

#java -server -Xmx1g -jar blazegraph.jar



class Handler:
    def __init__(self):
        self.dbPathOrUrl = ""

    def getDbPathOrUrl(self) -> str:
        return self.dbPathOrUrl
    
    def setDbPathOrUrl(self, input:str) -> bool:
        if type(input) == str:
            self.dbPathOrUrl = input
            return True
        return False


class UploadHandler(Handler):
    def __init__(self):
        super().__init__()

    def pushDataToDb(self, path) -> bool: 
        pass


class CitationUploadHandler(UploadHandler):
    def __init__(self):
        super().__init__()
    
    def pushDataToDb(self, path:str) -> bool:
        if type(path) == str:
            df = read_csv(path, keep_default_na=None)

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
        return False
    
class BibliographicEntityUploadHandler(UploadHandler):

    def __init__(self):
        super().__init__()

    def pushDataToDb(self, path:str) -> bool:
        if type(path) == str:
            with open(path, "r", encoding="utf-8") as f:
                data = load(f)   # lista di dizionari
                
            rows_entity    = list()
            for dic in data:
                if dic["id"]:
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

            df = DataFrame(rows_entity)

            with connect(self.dbPathOrUrl) as con:
                df.to_sql("BibliographicEntity", con,
                                    if_exists="append", index=False)
            return True
        return False

class QueryHandler(Handler):
    def __init__(self):
        super().__init__()

    #we kept the implementation of the 2 getById's separate.
        
    def getById(self, id) -> DataFrame:
        pass

    


class BibliographicEntityQueryHandler(QueryHandler):
    """
    Legge dal database SQLite e restituisce DataFrame pandas.
    Ogni metodo costruisce una query SQL ed esegue read_sql(), come mostrato
    dal professore nel capitolo "Interacting with databases using Pandas".
    """

    def __init__(self):
        super().__init__()
        
    def getById(self, id) -> DataFrame:
        #the query basically adds commas when they are not already present, in order to select the id 
        #if it is contained in the list.
        with connect(self.dbPathOrUrl) as con:
            query = """
                SELECT DISTINCT be.internalId, be.title, be.pub_date, be.id
                FROM BibliographicEntity AS be
                WHERE INSTR(',' || be.id || ',' , ',' || ? || ',') > 0
            """
            df = read_sql(query, con, params=("%" + id + "%",))  
        return df


    def getAllBibliographicEntities(self) -> DataFrame:
        with connect(self.dbPathOrUrl) as con:
            query = """
                SELECT DISTINCT
                internalId, title, 
                author, pub_date,
                venue, id  
                FROM BibliographicEntity
            """
            df = read_sql(query, con)
        return df

    def getBibliographicEntitiesWithTitle(self, title) -> DataFrame:
        # LIKE con % cerca la stringa come sottostringa del titolo
        with connect(self.dbPathOrUrl) as con:
            query = """
                SELECT DISTINCT
                    internalId, title, pub_date, author,
                    id, venue
                FROM BibliographicEntity 
                WHERE title LIKE ?
            """
            df = read_sql(query, con, params=("%" + title + "%",))
        return df

    def getBibliographicEntitiesWithAuthor(self, name) -> DataFrame:
        # DISTINCT evita duplicati se il nome matcha sia givenName che familyName
        with connect(self.dbPathOrUrl) as con:
            query = """
                SELECT DISTINCT
                        internalId, title, pub_date, author,
                       id, venue
                FROM BibliographicEntity 

                WHERE author like ?
            """
            df = read_sql(query, con, params=("%" + name + "%",))
        return df

    def getBibliographicEntitiesWithinPublicationDate(self, start=None, end=None) -> DataFrame:
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
            df = read_sql(query, con, params=params)
        return df

    def getBibliographicEntitiesWithVenue(self, venue) -> DataFrame:
        with connect(self.dbPathOrUrl) as con:
            query = """
                SELECT DISTINCT internalId, title, pub_date, author,
                       id, venue

                FROM BibliographicEntity 

                WHERE venue LIKE ?
            """
            df = read_sql(query, con, params=("%" + venue + "%",))
        return df

    
class CitationQueryHandler(QueryHandler):
    def __init__(self):
        super().__init__()
    
    def convert_todf(self, query) -> DataFrame: #auxiliary function
        endpoint = self.dbPathOrUrl
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
            df = DataFrame(rows)
            return df

    def getById(self, id) -> DataFrame:
        query = f"""
        prefix oci: <https://oci.opencitations.net/virtual/ci/>
        prefix cito: <http://purl.org/spar/cito/>
        SELECT ?citing ?cited ?creation ?timespan
        WHERE 
            {{?s rdfs:label '{id}' .
            ?s cito:hasCreationDate ?creation .
            ?s cito:hasTimespan ?timespan .
            ?s cito:hasCitingEntity ?citing .
            ?s cito:hasCitedEntity ?cited }}"""
        
        df = self.convert_todf(query)
        if len(df) > 0:
            df["oci"] = id
        return df
       

    def getAllCitations(self) -> DataFrame:
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
        result = self.convert_todf(query)
        return result


    def getAllAuthorSelfCitations(self) -> DataFrame:
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
        
        result = self.convert_todf(query)
        return result
    
    def getAllJournalSelfCitations(self) -> DataFrame:
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

        result = self.convert_todf(query)
        return result
    
    def getCitationsWithinTimespan(self, beginning = "", end = "") -> DataFrame:
        df = self.getAllCitations()

        def timespan_to_days(timespan): #auxiliary function
            days = 0
            d = isodate.parse_duration(timespan)
            if hasattr(d, "days"):
                days += d.days
            if hasattr(d, "months"):
                days += (d.months * 30)
            if hasattr(d, "years"):
                days += (d.years * 365)
            return int(days)        

        if len(beginning) == 0 and len(end) == 0:
            return df
        
        else:
            df["filter"] = df["timespan"].apply(lambda x: timespan_to_days(x))

            if len(beginning) > 0:
                min = timespan_to_days(beginning)
                df = df.query(f"`filter` >= {min}")

            if len(end) > 0:
                max = timespan_to_days(end)
                df = df.query(f"`filter` <= {max}")

            df = df.reset_index(drop=True)
            df = df.drop(columns=["filter"])
            return df
            
            
    def getCitationsWithinDate(self, min = "", max = "") -> DataFrame: 
        data = self.getAllCitations()
        if len(min) == 0 and len(max) == 0:
            return data
        else:
            def normalize_string(d): #auxiliary function
                if len(d) == 4:
                    d += "-01-01"
                elif len(d) == 7:
                    d += "-01"
                return d
            
            data["filter"] = data["creation"].apply(lambda x: normalize_string(x))
            data["filter"] = to_datetime(data["filter"], format = "%Y-%m-%d" )


            if min:
                min_date = isodate.parse_date(min)
                data = data.query(f"`filter` >= '{min_date}'")

            if max: 
                if len(max) == 4:
                    max += "-12-31"
                if len(max) == 7:
                    max += "-31"
                data = data.query(f"`filter` <= '{max}'")
            data = data.drop(columns=["filter"])
            data = data.reset_index()
            return data



class IdentifiableEntity():
    def __init__(self):
        self.id = list()

    def getIds(self) -> list:
        return self.id

class BibliographicEntity(IdentifiableEntity):
    def __init__(self):
        self.title = ""
        self.author = list()
        self.publication_date = ""
        self.venue = ""
        super().__init__()

    def getTitle(self) -> str:
        return self.title
    
    def getAuthors(self) -> list:
        return self.author
    
    def getPublicationDate(self) -> str:
        return self.publication_date
    
    def getVenue(self) -> str:
        return self.venue


class Citation(IdentifiableEntity):
    def __init__(self):
        self.creation = ""
        self.timespan = ""
        self.hasCitingEntity = None
        self.hasCitedEntity = None
        super().__init__()

    def getCreation(self) -> str:
        return self.creation
    
    def getTimespan(self) -> str:
        return self.timespan
    
    def getCitingEntity(self) -> BibliographicEntity:
        return self.hasCitingEntity

    def getCitedEntity(self) -> BibliographicEntity:
        return self.hasCitedEntity

class JournalSelfCitation(Citation):
    def __init__(self):
        super().__init__()

class AuthorSelfCitation(Citation):
    def __init__(self):
        super().__init__()


class BasicQueryEngine():
    def __init__(self):
        self.citationQuery = list()
        self.bibliographicEntityQuery = list()
    
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

    
    def setFullDataFrame(self, be_df:DataFrame, cit_df:DataFrame) -> DataFrame: #auxiliary function
        #method created to avoid repeating code on the constructors of Citation entities and their subclasses
        #it merges the BE and Citation in a way that facilitates the creation of hasCitingEntity and hasCitedEntity
        mom_be = be_df
        prefix = "https://opencitations.net/entity/"
        mom_be["internalId"] = mom_be["internalId"].apply(lambda x: prefix + x) #adds the prefix in front of the elements of the internalId column in the bibliographic entries dataframe,
                                                                                #so that it can be the same as the ids found in the citing and cited columns of the citations dataframe
        full_df = cit_df
        
        citing_df = mom_be.rename(columns={"title":"title_citing",
                                           "author":"author_citing",
                                           "pub_date":"pub_date_citing",
                                           "venue":"venue_citing",
                                           "id":"id_citing"})
        
        full_df = merge(full_df, citing_df, left_on="citing", right_on="internalId", how="inner") #merges the Citations dataframe with a BE one on the "citing" column,
                                                                                                     #and the columns of the latter have been modified to make them recognizable
        cited_df = mom_be.rename(columns={"title":"title_cited",
                                          "author":"author_cited",
                                          "pub_date":"pub_date_cited",
                                          "venue":"venue_cited",
                                          "id":"id_cited"})
        
        full_df = merge(full_df, cited_df, left_on="cited", right_on="internalId", how="inner") #merges the Citations dataframe with a BE one on the "cited" column,
                                                                                                   #and the columns of the latter have been modified to make them recognizable

        return full_df
    
    def constructBibliographicEntity(self, row:Series) -> BibliographicEntity: #auxiliary function
        #additional function made to avoid repetitions in the code
        auth = row["author"].split("; ") if row["author"] else None #separates the different authors
        i = row["id"].split("; ") #separates the different ids

        bib_en = BibliographicEntity() #constructs the BE class
        if row["title"]: bib_en.title += row["title"]
        if row["author"]: bib_en.author.extend(auth)
        bib_en.id.extend(i)
        if row["pub_date"]: bib_en.publication_date += row["pub_date"]
        if row["venue"]: bib_en.venue += row["venue"]

        return bib_en
    
    def constructCitation(self, row:Series, class_to_construct = Citation) -> Citation: #auxiliary function
        #additional function made to avoid repetitions in the code
        #the row in input comes from a dataframe that has been selectfully merged to facilitate the creation of hasCitingEntity and hasCitedEntity

        #the hasCitingEntity and hasCitedEntity parameters are created before the Citation class, and
        #constructBibliographicEntity cannot be called for them due to the column names being different
        
        if row["citing"]:
                if row["id_citing"]:
                    auth_citing = row["author_citing"].split("; ") if row["author_citing"] else None
                    i_citing = row["id_citing"].split("; ")

                    citing = BibliographicEntity()
                    if row["title_citing"]: citing.title += row["title_citing"]
                    if row["author_citing"]: citing.author.extend(auth_citing)
                    citing.id.extend(i_citing)
                    if row["pub_date_citing"]: citing.publication_date += row["pub_date_citing"]
                    if row["venue_citing"]: citing.venue += row["venue_citing"]
                else:
                    citing = row["citing"]
        
        if row["cited"]:
                if row["id_cited"]:
                    auth_cited = row["author_cited"].split("; ") if row["author_cited"] else None
                    i_cited = row["id_cited"].split("; ")

                    cited = BibliographicEntity()
                    if row["title_cited"]: cited.title += row["title_cited"]
                    if row["author_cited"]: cited.author.extend(auth_cited)
                    cited.id.extend(i_cited)
                    if row["pub_date_cited"]: cited.publication_date += row["pub_date_cited"]
                    if row["venue_cited"]: cited.venue += row["venue_cited"]
                else:
                    cited = row["cited"]
        
        cit = class_to_construct()
        if row["oci"]: cit.id.extend([row["oci"]])
        if row["creation"]: cit.creation += row["creation"]
        if row["timespan"]: cit.timespan += row["timespan"]
        if row["citing"]: cit.hasCitingEntity = citing
        if row["cited"]: cit.hasCitedEntity = cited
        
        return cit
        
    def getEntityById(self, id:str):
        if id:

            be_qhandler = self.bibliographicEntityQuery #the BEQH list is initiated by default, since both constructors make use of the BE dataframe
            df_be = DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"]) #an empty dataframe is created, only having the column names

            flag = False
            for item in be_qhandler:
                    merge_be = concat([df_be, item.getAllBibliographicEntities()]) #the dataframes of the different BEQHs are merged into one
                    if not item.getById(id).empty:
                        flag = True

            if flag:
                for idx, row in merge_be.iterrows():
                        if id in row["id"]: #find the row with the right id
                            return self.constructBibliographicEntity(row)
                        
            else:
                ci_qhandler = self.citationQuery #the CQH and its functions are called only when we know it's not the id of a BE, so to avoid
                                                    #connecting to the graph unless necessary, since the process takes quite some time
                df_ci = DataFrame(columns=["oci", "creation", "citing", "cited", "timespan"])
                for item in ci_qhandler:
                    merge_cit = concat([df_ci, item.getAllCitations()]) #the dataframes of the different CQHs are merged into one

                if not merge_cit.empty:
                    full_df = self.setFullDataFrame(merge_be, merge_cit) #the BE and Citation dataframes are merged in a way that facilitates the creation of hasCitingEntity and hasCitedEntity

                    for idx, row_ci in full_df.iterrows():
                        if id in row_ci["oci"]: #find the row with the right id
                            id_class = Citation
                            if row_ci["author_citing"] == row_ci["author_cited"]:
                                id_class = AuthorSelfCitation
                            elif row_ci["venue_citing"] == row_ci["venue_cited"]:
                                id_class = JournalSelfCitation
                            return self.constructCitation(row_ci, id_class)
                    #Alice - adjusted row and turned it into row_ci everytime it was called out, because of typos
        return None
      

    def getAllCitations(self) -> list:
        result = list()

        if self.bibliographicEntityQuery:

            be_qhandler = self.bibliographicEntityQuery
            df_be = DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
            for item in be_qhandler:
                merge_be = concat([df_be, item.getAllBibliographicEntities()])
            
        if self.citationQuery:

            ci_qhandler = self.citationQuery
            df_ci = DataFrame(columns=["oci", "creation", "citing", "cited", "timespan"])
            for item in ci_qhandler:
                merge_ci = concat([df_ci, item.getAllCitations()]) #selects the all of the Citation elements using a CQH method

            final_df = self.setFullDataFrame(merge_be, merge_ci)

            for idx, row in final_df.iterrows():
                    result.append(self.constructCitation(row))
        return result

    def getAllAuthorSelfCitations(self) -> list:
        result = list()

        be_qhandler = self.bibliographicEntityQuery
        df_be = DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be = concat([df_be, item.getAllBibliographicEntities()])

        ci_qhandler = self.citationQuery
        df_ci = DataFrame(columns=["oci", "creation", "citing", "cited", "timespan"])
        for item in ci_qhandler:
            merge_asc = concat([df_ci, item.getAllAuthorSelfCitations()]) #selects the interested elements using a CQH method

        full_df = self.setFullDataFrame(merge_be, merge_asc)

        for idx, row in full_df.iterrows():
            result.append(self.constructCitation(row, AuthorSelfCitation))

        return result

    def getAllJournalSelfCitations(self) -> list:
        result = list()

        be_qhandler = self.bibliographicEntityQuery
        df_be = DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be = concat([df_be, item.getAllBibliographicEntities()])

        ci_qhandler = self.citationQuery
        df_ci = DataFrame(columns=["oci", "creation", "citing", "cited", "timespan"])
        for item in ci_qhandler:
            merge_jsc = concat([df_ci, item.getAllJournalSelfCitations()]) #selects the interested elements using a CQH method

        full_df = self.setFullDataFrame(merge_be, merge_jsc)

        for idx, row in full_df.iterrows():
            result.append(self.constructCitation(row, JournalSelfCitation))

        return result

    def getCitationsWithinTimespan(self, min_timespan:str = "", max_timespan:str = "") -> list:
        result = list()

        be_qhandler = self.bibliographicEntityQuery
        df_be = DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be = concat([df_be, item.getAllBibliographicEntities()])

        ci_qhandler = self.citationQuery
        df_ci = DataFrame(columns=["oci", "creation", "citing", "cited", "timespan"])
        for item in ci_qhandler:
            merge_ci = concat([df_ci, item.getCitationsWithinTimespan(min_timespan, max_timespan)]) #selects the interested elements using a CQH method

        final_df = self.setFullDataFrame(merge_be, merge_ci)

        for idx, row in final_df.iterrows():
                result.append(self.constructCitation(row))
        return result

    def getCitationsWithinDate(self, start_date:str = "", end_date:str = "") -> list:
        result = list()

        be_qhandler = self.bibliographicEntityQuery
        df_be = DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be = concat([df_be, item.getAllBibliographicEntities()])

        ci_qhandler = self.citationQuery
        df_ci = DataFrame(columns=["oci", "creation", "citing", "cited", "timespan"])
        for item in ci_qhandler:
            merge_ci = concat([df_ci, item.getCitationsWithinDate(start_date, end_date)]) #selects the interested elements using a CQH method

        final_df = self.setFullDataFrame(merge_be, merge_ci)

        for idx, row in final_df.iterrows():
                result.append(self.constructCitation(row))
        return result

    def getAllBibliographicEntities(self) -> list:
        result = list()
        be_qhandler = self.bibliographicEntityQuery
        df_be = DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be = concat([df_be, item.getAllBibliographicEntities()])

        for idx, row in merge_be.iterrows():
            result.append(self.constructBibliographicEntity(row))
        return result

    def getBibliographicEntitiesWithTitle(self, title:str) -> list:
        result = list()
        be_qhandler = self.bibliographicEntityQuery
        df_be = DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be = concat([df_be, item.getBibliographicEntitiesWithTitle(title)])

        for idx, row in merge_be.iterrows():
            result.append(self.constructBibliographicEntity(row))
        return result

    def getBibliographicEntitiesWithAuthor(self, author:str) -> list:
        result = list()
        be_qhandler = self.bibliographicEntityQuery
        df_be = DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be = concat([df_be, item.getBibliographicEntitiesWithAuthor(author)])

        for idx, row in merge_be.iterrows():
            result.append(self.constructBibliographicEntity(row))
        return result

    def getBibliographicEntitiesWithinDate(self, start_date:str = None, end_date:str = None) -> list:
        result = list()
        be_qhandler = self.bibliographicEntityQuery
        df_be = DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be = concat([df_be, item.getBibliographicEntitiesWithinPublicationDate(start_date, end_date)])

        for idx, row in merge_be.iterrows():
            result.append(self.constructBibliographicEntity(row))
        return result
    
    #The function has been copied with a different name, to cover for a naming inconstintency 
    #between the instructions and the functions called by the given unittest

    def getBibliographicEntitiesWithinPublicationDate(self, start_date:str = None, end_date:str = None) -> list:
        result = list()
        be_qhandler = self.bibliographicEntityQuery
        df_be = DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be = concat([df_be, item.getBibliographicEntitiesWithinPublicationDate(start_date, end_date)])

        for idx, row in merge_be.iterrows():
            result.append(self.constructBibliographicEntity(row))
        return result
    
    def getBibliographicEntitiesWithVenue(self, venue:str) -> list:
        result = list()
        be_qhandler = self.bibliographicEntityQuery
        df_be = DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be = concat([df_be, item.getBibliographicEntitiesWithVenue(venue)])

        for idx, row in merge_be.iterrows():
            result.append(self.constructBibliographicEntity(row))
        return result

    def countInstances(self, df:DataFrame, column:str, item:str): #auxilary function used only for testing
        counter = 0
        for idx, row in df.iterrows():
            if item in row[column]:
                counter += 1
        return counter

class FullQueryEngine(BasicQueryEngine):
    def __init__(self):
        super().__init__()

    def getAuthorSelfCitationsByName(self, author_name:str) -> list:
        result = list()

        be_qhandler = self.bibliographicEntityQuery
        df_be = DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be = concat([df_be, item.getBibliographicEntitiesWithAuthor(author_name)]) #selects only the BibliographicEntities with the desired author

        ci_qhandler = self.citationQuery
        df_ci = DataFrame(columns=["oci", "creation", "citing", "cited", "timespan"])
        for item in ci_qhandler:
            merge_asc = concat([df_ci, item.getAllAuthorSelfCitations()]) #selects only AuthorSelfCitations

        full_df = self.setFullDataFrame(merge_be, merge_asc)

        for idx, row in full_df.iterrows():
                result.append(self.constructCitation(row, AuthorSelfCitation))
        return result

    def getJournalSelfCitationsByName(self, journal_name:str) -> list:
        result = list()

        be_qhandler = self.bibliographicEntityQuery
        df_be = DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be = concat([df_be, item.getBibliographicEntitiesWithVenue(journal_name)]) #selects only the BibliographicEntities with the desired venue

        ci_qhandler = self.citationQuery
        df_ci = DataFrame(columns=["oci", "creation", "citing", "cited", "timespan"])
        for item in ci_qhandler:
            merge_jsc = concat([df_ci, item.getAllJournalSelfCitations()]) #selects only JournalSelfCitations

        full_df = self.setFullDataFrame(merge_be, merge_jsc)

        for idx, row in full_df.iterrows():
            result.append(self.constructCitation(row, JournalSelfCitation))
        return result

    def getCitationsOfBibEntityByTitleWithinDate(self, bib_entity_title:str, min_date:str = "", max_date:str = "") -> list:
        result = list()
        be_qhandler = self.bibliographicEntityQuery
        df_be = DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be = concat([df_be, item.getBibliographicEntitiesWithTitle(bib_entity_title)]) #selects only the BibliographicEntities with the desired venue

        ci_qhandler = self.citationQuery
        df_ci = DataFrame(columns=["oci", "creation", "citing", "cited", "timespan"])
        for item in ci_qhandler:
            merge_cit = concat([df_ci, item.getCitationsWithinDate(min_date, max_date)]) #selects only JournalSelfCitations

        full_df = self.setFullDataFrame(merge_be, merge_cit)

        for idx, row in full_df.iterrows():
            result.append(self.constructCitation(row))
        return result

    def getReferencesOfBibEntityByTitleWithinTimespan(self, bib_entity_title:str, min_timespan:str = "", max_timespan:str = "") -> list:
        result = list()
        be_qhandler = self.bibliographicEntityQuery
        df_be = DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be = concat([df_be, item.getBibliographicEntitiesWithVenue(bib_entity_title)]) #selects only the BibliographicEntities with the desired venue

        ci_qhandler = self.citationQuery
        df_ci = DataFrame(columns=["oci", "creation", "citing", "cited", "timespan"])
        for item in ci_qhandler:
            merge_cit = concat([df_ci, item.getCitationsWithinTimespan(min_timespan, max_timespan)]) #selects only JournalSelfCitations

        full_df = self.setFullDataFrame(merge_be, merge_cit)

        for idx, row in full_df.iterrows():
            result.append(self.constructCitation(row))
        return result
