from pandas import DataFrame, Series, read_sql, read_csv, merge, concat, to_datetime
from SPARQLWrapper import SPARQLWrapper, POST
from sparqlite import SPARQLClient
from rdflib.plugins.stores.sparqlstore import SPARQLUpdateStore
import isodate
from calendar import monthrange
from json import load
from sqlite3 import connect



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

# CitationUploadHandler is responsible for loading citation data from the dh_citations.csv file onto the Blazegraph database using SPARQL INSERT DATA queries.
#each row in the CSV becmone one RDF subject with multiple predicates
class CitationUploadHandler(UploadHandler):
    def __init__(self):
        super().__init__()
    
    def pushDataToDb(self, path:str) -> bool:
        if type(path) == str:
            df = read_csv(path, keep_default_na=None)

            sparql = SPARQLWrapper(self.dbPathOrUrl)
            sparql.setMethod("POST")

            for _, row in df.iterrows():
                if not (row["oci"] and row["citing"] and row["cited"] and row["creation"] and row["timespan"] and row ["journal_sc"] and row ["author_sc"]): # This is a check for mandatory fields: according to the data model, all 7 fields of a Citation are required. IF even 1 is missing, the row does not conform and must not be loaded.
                    continue # This skips the row with missing elements and moves onto the next one.
                    
                citation_uri = f"https://opencitations.net/citation/{row['oci']}"
                # Build the SPARQL INSERT DATA query. Each triple follows the Turtle syntax: subject ; predicate value .
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
                    # rdfs:label stores the OCI string so it can be retrieved later with SELECT queries.
                # hasCitingEntity and hasCitedEntity are stored as full URIs (not literals), so they can be matched against the internalId column in SQLite during the merge.
                # All other fields are stored as xsd:string literals.
                
                sparql.setQuery(query)
                sparql.query()
            return True
        return False

    
#BibliographicEntityUploadHandler loads bibliographic entity data
# from the dh_metadata.json file onto the SQLite database using to_sql().
# Each record in the JSON becomes one row in the BibliographicEntity table
class BibliographicEntityUploadHandler(UploadHandler):

    def __init__(self):
        super().__init__()

    def pushDataToDb(self, path:str) -> bool:
        if type(path) == str:
            # The JSON file is opened and parsed into a list, where each element is a dictionary representing one bibliographic record
            with open(path, "r", encoding="utf-8") as f:
                data = load(f)   # lista di dizionari
            
            # A list is used to collect one dictionary per record before converting to a DataFrame 
            rows_entity    = list()
            for dic in data:
                # Records with no id are skipped since without an internalId, the entity cannot be identified or linked in the database
                if dic["id"]:
                    internal_id = ""
                    # The method .get() with "" as default value avoids a KeyError, if the key is missing from the dictionary
                    title    = dic.get("title", "") 
                    pub_date = dic.get("pub_date", "") 
                    # The OMID is used as internalId since it matches the format
                    # used in the "citing" and "cited" columns of the CSV,
                    # making the merge between the two DataFrames possible in the BasicQueryEngine
                    for item in dic["id"]:
                        if "omid" in item:
                            internal_id += item
                    # All ids are joined into a single string separated by "; "
                    # so they fit in one column and can be recovered later as a list
                    entity_id = "; ".join(dic["id"])
                    # The same approach is used for authors: stored as a single string
                    # so that each bibliographic entity corresponds to one row in the table
                    author ="; ".join(dic["author"]) if len(dic["author"]) > 0 else ""
                    # venue can be None in the JSON, so it defaults to ""
                    # to avoid inserting None values into the database
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
            # The parameter if_exists is set to "append" instead of "replace"
            # so that pushDataToDb can be called multiple times without losing existing data.
            # The parameter index is set to False so that the DataFrame index
            # is not added to the database table
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
    #Reads from the SQLite database and returns pandas DataFrames

    def __init__(self):
        super().__init__()
        
    def getById(self, id) -> DataFrame:
        #the query basically adds commas when they are not already present, in order to select the id 
        #where it is present.
        if id[-1] == ";":
            id += " "
        with connect(self.dbPathOrUrl) as con:
            query = """
                SELECT DISTINCT internalId, title, pub_date, id
                FROM BibliographicEntity 
                WHERE '; ' || id || '; ' LIKE '; ' || ? || ';%'
            """

            df = read_sql(query, con, params=(id ,))  

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
        #% searches for the string as a substring of the title
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
        # The % on both sides of the value enables the specification
        # of the Author as a substring

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
        
        conditions = list()
        params     = list()
        if start is not None and len(start) > 0:
            conditions.append("pub_date >= ?")
            params.append(start)
        if end is not None and len(end) > 0:
            conditions.append("pub_date <= ?")
            params.append(end)
        # If no conditions were added, where_clause stays empty and the query returns all rows
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
    
        result = self.convert_todf(query)
        return result
    
    def getCitationsWithinTimespan(self, beginning = "", end = "") -> DataFrame:
        df = self.getAllCitations()
        #starts with all the citations, filters on python

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
            
            data["filter"] = data["creation"].apply(lambda x: normalize_string(x)) #uniforming the dates in the YYY MM DD format
            data["filter"] = to_datetime(data["filter"], format = "%Y-%m-%d" )


            if min:
                min_date = isodate.parse_date(min)
                data = data.query(f"`filter` >= '{min_date}'")

            if max: 
                if len(max) == 4:
                    max += "-12-31"
                if len(max) == 7: #used a little function to select the last day of the month.
                    year, month = int(max[:4]), int(max[5:7])
                    last_day = monthrange(year, month)[1]
                    max += "-" + str(last_day).zfill(2)
                data = data.query(f"`filter` <= '{max}'")
            data = data.drop(columns=["filter"])
            data = data.reset_index(drop=True)
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

    
    def setFullDataFrame(self, be_df:DataFrame, cit_df:DataFrame) -> DataFrame: # auxiliary function
        # method created to avoid repeating code on the constructors of Citation entities and their subclasses
        # it merges the BE and Citation in a way that facilitates the creation of hasCitingEntity and hasCitedEntity
        if not be_df.empty: # checks if the BibliographicEntity dataframe is empty or not
            mom_be = be_df
            prefix = "https://opencitations.net/entity/"
            mom_be["internalId"] = mom_be["internalId"].apply(lambda x: prefix + x) # adds the prefix in front of the elements of the internalId column in the bibliographic entries dataframe,
                                                                                    #so that it can be the same as the ids found in the citing and cited columns of the citations dataframe
            full_df = cit_df
            
            citing_df = mom_be.rename(columns={"internalId":"internalId_citing",
                                               "title":"title_citing",
                                               "author":"author_citing",
                                               "pub_date":"pub_date_citing",
                                               "venue":"venue_citing",
                                               "id":"id_citing"})
            
            full_df = merge(full_df, citing_df, left_on="citing", right_on="internalId_citing", how="inner") # merges the Citations dataframe with a BE one on the "citing" column,
                                                                                                             # and the columns of the latter have been modified to make them recognizable
            cited_df = mom_be.rename(columns={"internalId":"internalId_cited",
                                              "title":"title_cited",
                                              "author":"author_cited",
                                              "pub_date":"pub_date_cited",
                                              "venue":"venue_cited",
                                              "id":"id_cited"})
            
            full_df = merge(full_df, cited_df, left_on="cited", right_on="internalId_cited", how="inner") #merges the Citations dataframe with a BE one on the "cited" column,
                                                                                                    #and the columns of the latter have been modified to make them recognizable
        else: # in case the BE database is empty, it still manually adds the id_citing and id_cited columns, so that they can be added  to the Ids of the respective BEs
            df_cit = cit_df
            df_empty = DataFrame(columns=["oci", "creation", "citing","id_citing", "cited", "id_cited", "timespan"])
            full_df = concat([df_empty, df_cit])
        return full_df
    
    def constructBibliographicEntity(self, row:Series) -> BibliographicEntity: #auxiliary function
        #additional function made to avoid repetitions in the code
        auth = row["author"].split("; ") if type(row["author"]) == str  else None#separates the different authors
        i = row["id"].split("; ") #separates the different ids

        bib_en = BibliographicEntity() #constructs the BE class
        if row["title"] and type(row["title"]) == str: 
            bib_en.title += row["title"]
        if row["title"] and type(row["author"]) == str: 
            bib_en.author.extend(auth)
        bib_en.id.extend(i)
        if row["title"] and type(row["pub_date"]) == str: 
            bib_en.publication_date += row["pub_date"]
        if row["title"] and type(row["venue"]) == str: 
            bib_en.venue += row["venue"]

        return bib_en
    
    def constructCitation(self, row:Series, class_to_construct = Citation) -> Citation: #auxiliary function
        #additional function made to avoid repetitions in the code
        #the row in input comes from a dataframe that has been selectfully merged to facilitate the creation of hasCitingEntity and hasCitedEntity

        #the hasCitingEntity and hasCitedEntity parameters are created before the Citation class, and
        #constructBibliographicEntity cannot be called for them due to the column names being different
        citing = BibliographicEntity()
        if type(row["id_citing"]) == str:
            auth_citing = row["author_citing"].split("; ") if row["author_citing"] else None
            i_citing = row["id_citing"].split("; ")

            if row["title_citing"] and type(row["title_citing"]) == str: # check to see if the BE dataframe is present, if not the BE instance is created just with the id
                citing.title += row["title_citing"]
            if row["author_citing"] and type(row["author_citing"]) == str:
                citing.author.extend(auth_citing)
            citing.id.extend(i_citing)
            if row["pub_date_citing"] and type(row["pub_date_citing"]) == str:
                citing.publication_date += row["pub_date_citing"]
            if row["venue_citing"] and type(row["venue_citing"]) == str:
                citing.venue += row["venue_citing"]
        else:
            citing.id.extend([row["citing"]])
        
        cited = BibliographicEntity()
        if type(row["id_cited"]) == str: # check to see if the BE dataframe is present, if not the BE instance is created just with the id
            auth_cited = row["author_cited"].split("; ") if row["author_cited"] else None
            i_cited = row["id_cited"].split("; ")

            if row["title_cited"] and type(row["title_cited"]) == str:
                cited.title += row["title_cited"]
            if row["author_cited"] and type(row["author_cited"]) == str:
                cited.author.extend(auth_cited)
            cited.id.extend(i_cited)
            if row["pub_date_cited"] and type(row["pub_date_cited"]) == str:
                cited.publication_date += row["pub_date_cited"]
            if row["venue_cited"] and type(row["venue_cited"]) == str:
                cited.venue += row["venue_cited"]
        else:
            cited.id.extend([row["cited"]])
        
        cit = class_to_construct() # this way the same function can be used to create AuthorSelfCitation and JournalSelfCitation as well
        cit.id.extend([row["oci"]])
        cit.creation += row["creation"]
        cit.timespan += row["timespan"]
        cit.hasCitingEntity = citing
        cit.hasCitedEntity = cited
        
        return cit
    
    def getEntityById(self, id:str):
        if id:
            be_qhandler = self.bibliographicEntityQuery # the BEQH list is initiated by default, since both constructors make use of the BE dataframe
            df_be = DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"]) # an empty dataframe is created, only having the column names
            merge_be = DataFrame()
            
            if be_qhandler:
                for item in be_qhandler:
                        merge_be = concat([df_be, item.getById(id)]) # checks if the right Id is present in the QueryHandler's database

            if not merge_be.empty:
                for idx, row in merge_be.iterrows():
                    return self.constructBibliographicEntity(row) # returns the correct instance if it finds one
                        
            else:
                ci_qhandler = self.citationQuery
                df_ci = DataFrame(columns=["oci", "creation", "citing", "cited", "timespan"])
                merge_cit = DataFrame()

                for item in ci_qhandler:
                    merge_cit = concat([df_ci, item.getById(id)]) # checks if the right Id is present in the QueryHandler's database

                if not merge_cit.empty:
                    for item in be_qhandler:
                        merge_be = concat([df_be, item.getAllBibliographicEntities()]) 

                    full_df = self.setFullDataFrame(merge_be, merge_cit) # the BE and Citation dataframes are merged in a way that facilitates the creation of hasCitingEntity and hasCitedEntity

                    for idx, row_ci in full_df.iterrows():
                        if id in row_ci["oci"]: # finds the row with the right id
                            return self.constructCitation(row_ci) # constructs the Citation instance
        return None
        
    def getAllCitations(self) -> list: # The method retrieves all citations from Blazegraph, merges them with bibliographic entity data from SQLite to populate hasCitingEntity and hasCitedEntity, and returns a list of Citation objects.
        result = list()
        be_qhandler = self.bibliographicEntityQuery
        merge_be = DataFrame()
        df_be = DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"]) # Load all bibliographic entities from SQLite.
        if be_qhandler:
            for item in be_qhandler:
                merge_be = concat([df_be, item.getAllBibliographicEntities()])

        ci_qhandler = self.citationQuery
        df_ci = DataFrame(columns=["oci", "creation", "citing", "cited", "timespan"])
        for item in ci_qhandler:
            merge_ci = concat([df_ci, item.getAllCitations()]) #selects all of the Citation elements using a CQH method

        final_df = self.setFullDataFrame(merge_be, merge_ci) # This passage joins the citation DataFrame with the bibliographic entity Dataframe twice: 
                                                             #once on the citing column and once on the cited. Result is a single DataFrame.

        for idx, row in final_df.iterrows():
                result.append(self.constructCitation(row)) # creates an instance from each row and adds it to the list in output
        return result

    def getAllAuthorSelfCitations(self) -> list: # Works like getAllCitations but only retrieves citations flagged as author self-citations in Blazegraph and constructs AuthorSelfCitation objects.
        result = list()
        merge_be = DataFrame()
        be_qhandler = self.bibliographicEntityQuery
        if be_qhandler:
            df_be = DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
            for item in be_qhandler:
                merge_be = concat([df_be, item.getAllBibliographicEntities()])

        ci_qhandler = self.citationQuery
        df_ci = DataFrame(columns=["oci", "creation", "citing", "cited", "timespan"])
        for item in ci_qhandler:
            merge_asc = concat([df_ci, item.getAllAuthorSelfCitations()]) #selects the interested elements using a CQH method

        full_df = self.setFullDataFrame(merge_be, merge_asc)

        for idx, row in full_df.iterrows():
            result.append(self.constructCitation(row, AuthorSelfCitation)) # Adds the optional "AuthorSelfCitation" parameter to have 
                                                                           # the constructor build an AuthorSelfCitation class

        return result

    def getAllJournalSelfCitations(self) -> list: # Works like getAllAuthorSelfCitations but for
    # journal self-citations, constructing JournalSelfCitation objects
        result = list()
        merge_be = DataFrame()
        be_qhandler = self.bibliographicEntityQuery
        df_be = DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        if be_qhandler:
            for item in be_qhandler:
                merge_be = concat([df_be, item.getAllBibliographicEntities()])

        ci_qhandler = self.citationQuery
        df_ci = DataFrame(columns=["oci", "creation", "citing", "cited", "timespan"])
        for item in ci_qhandler:
            merge_jsc = concat([df_ci, item.getAllJournalSelfCitations()]) #selects the interested elements using a CQH method

        full_df = self.setFullDataFrame(merge_be, merge_jsc)

        for idx, row in full_df.iterrows():
            result.append(self.constructCitation(row, JournalSelfCitation)) # Adds the optional "JournalSelfCitation" parameter to have 
                                                                            # the constructor build an JournalSelfCitation class

        return result

    def getCitationsWithinTimespan(self, min_timespan:str = "", max_timespan:str = "") -> list: #retrieves all citations whose timespan falls between min_timespan and max_timespan.
        result = list()
        merge_be = DataFrame()
        be_qhandler = self.bibliographicEntityQuery
        df_be = DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        if be_qhandler:
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

    def getCitationsWithinDate(self, start_date:str = "", end_date:str = "") -> list: # Retrieves all citations whose creation date falls between start_date and end_date.
        result = list()
        merge_be = DataFrame()
        be_qhandler = self.bibliographicEntityQuery
        df_be = DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        if be_qhandler:
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
        
    def getAllBibliographicEntities(self) -> list: # creates a list with all of the BibliographicEntities present in all of the BEQH uploaded on the Engine
        result = list()
        be_qhandler = self.bibliographicEntityQuery
        df_be = DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be = concat([df_be, item.getAllBibliographicEntities()])  # This passage joins the citation DataFrame with the bibliographic entity Dataframe twice:
                                                                            #once on the citing column and once on the cited. Result is a single DataFrame.

        for idx, row in merge_be.iterrows():
            result.append(self.constructBibliographicEntity(row)) # creates an instance from each row and adds it to the list in output
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

class FullQueryEngine(BasicQueryEngine):
    def __init__(self):
        super().__init__()

    def getAuthorSelfCitationsByName(self, author_name:str) -> list: # uses both the CQH and BEQH methods to select specific entries in the respective dataframes,
                                                                     # then combines them to get the desired result
        result = list()

        be_qhandler = self.bibliographicEntityQuery
        df_be = DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be = concat([df_be, item.getBibliographicEntitiesWithAuthor(author_name)]) # selects only the BibliographicEntities with the desired author

        ci_qhandler = self.citationQuery
        df_ci = DataFrame(columns=["oci", "creation", "citing", "cited", "timespan"])
        for item in ci_qhandler:
            merge_asc = concat([df_ci, item.getAllAuthorSelfCitations()]) # selects only AuthorSelfCitations

        full_df = self.setFullDataFrame(merge_be, merge_asc)

        for idx, row in full_df.iterrows():
                result.append(self.constructCitation(row, AuthorSelfCitation))
        return result

    def getJournalSelfCitationsByName(self, journal_name:str) -> list: # uses both the CQH and BEQH methods to select specific entries in the respective dataframes,
                                                                       # then combines them to get the desired result
        result = list()
        be_qhandler = self.bibliographicEntityQuery
        df_be = DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be = concat([df_be, item.getBibliographicEntitiesWithVenue(journal_name)]) # selects only the BibliographicEntities with the desired venue

        ci_qhandler = self.citationQuery
        df_ci = DataFrame(columns=["oci", "creation", "citing", "cited", "timespan"])
        for item in ci_qhandler:
            merge_jsc = concat([df_ci, item.getAllJournalSelfCitations()]) # selects only JournalSelfCitations

        full_df = self.setFullDataFrame(merge_be, merge_jsc)

        for idx, row in full_df.iterrows():
            result.append(self.constructCitation(row, JournalSelfCitation))
        return result

    def getCitationsOfBibEntityByTitleWithinDate(self, bib_entity_title:str, min_date:str = "", max_date:str = "") -> list:
        #for this one, since only a parameter in the cited entity needs to be selected, the merge of the Citation and BE dataframes is done manually,
        #instead of calling the function getAllJournalSelfCitations
        
        result = list()
        be_qhandler = self.bibliographicEntityQuery
        df_be_citing = DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        df_be_cited = DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be_citing = concat([df_be_citing, item.getAllBibliographicEntities()])
            merge_be_cited = concat([df_be_cited, item.getBibliographicEntitiesWithTitle(bib_entity_title)]) # only the CitedEntity's title needs to be filtered

        ci_qhandler = self.citationQuery
        df_ci = DataFrame(columns=["oci", "creation", "citing", "cited", "timespan"])
        for item in ci_qhandler:
            merge_cit = concat([df_ci, item.getCitationsWithinDate(min_date, max_date)])

        # the merge here is different compared to the usual one, since the citing and cited tables need to be different, so it needs to be manually written

        prefix = "https://opencitations.net/entity/"
        merge_be_citing["internalId"] = merge_be_citing["internalId"].apply(lambda x: prefix + x)
        merge_be_cited["internalId"] = merge_be_cited["internalId"].apply(lambda x: prefix + x)
        full_df = merge_cit
        
        citing_df = merge_be_citing.rename(columns={"title":"title_citing",
                                           "author":"author_citing",
                                           "pub_date":"pub_date_citing",
                                           "venue":"venue_citing",
                                           "id":"id_citing"})
        
        full_df = merge(full_df, citing_df, left_on="citing", right_on="internalId", how="inner") 

        cited_df = merge_be_cited.rename(columns={"title":"title_cited",
                                          "author":"author_cited",
                                          "pub_date":"pub_date_cited",
                                          "venue":"venue_cited",
                                          "id":"id_cited"})
        
        full_df = merge(full_df, cited_df, left_on="cited", right_on="internalId", how="inner") 

        for idx, row in full_df.iterrows():
            result.append(self.constructCitation(row))
        return result

    def getReferencesOfBibEntityByTitleWithinTimespan(self, bib_entity_title:str, min_timespan:str = "", max_timespan:str = "") -> list:
        #for this one, since only a parameter in the cited entity needs to be selected, the merge of the Citation and BE dataframes is done manually,
        #instead of calling the function getAllJournalSelfCitations
        result = list()
        be_qhandler = self.bibliographicEntityQuery
        df_be_citing = DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        df_be_cited = DataFrame(columns=["internalId", "title", "author", "pub_date", "venue", "id"])
        for item in be_qhandler:
            merge_be_citing = concat([df_be_citing, item.getBibliographicEntitiesWithTitle(bib_entity_title)]) # only the CitingEntity's title needs to be filtered
            merge_be_cited = concat([df_be_cited, item.getAllBibliographicEntities()]) 

        ci_qhandler = self.citationQuery
        df_ci = DataFrame(columns=["oci", "creation", "citing", "cited", "timespan"])
        for item in ci_qhandler:
            merge_cit = concat([df_ci, item.getCitationsWithinTimespan(min_timespan, max_timespan)])

        # the merge here is different compared to the usual one, since the citing and cited tables need to be different, so it needs to be manually written

        prefix = "https://opencitations.net/entity/"
        merge_be_citing["internalId"] = merge_be_citing["internalId"].apply(lambda x: prefix + x)
        merge_be_cited["internalId"] = merge_be_cited["internalId"].apply(lambda x: prefix + x)
        full_df = merge_cit
        
        citing_df = merge_be_citing.rename(columns={"title":"title_citing",
                                           "author":"author_citing",
                                           "pub_date":"pub_date_citing",
                                           "venue":"venue_citing",
                                           "id":"id_citing"})
        
        full_df = merge(full_df, citing_df, left_on="citing", right_on="internalId", how="inner") 
        
        cited_df = merge_be_cited.rename(columns={"title":"title_cited",
                                          "author":"author_cited",
                                          "pub_date":"pub_date_cited",
                                          "venue":"venue_cited",
                                          "id":"id_cited"})
        
        full_df = merge(full_df, cited_df, left_on="cited", right_on="internalId", how="inner") 

        for idx, row in full_df.iterrows():
            result.append(self.constructCitation(row))
        return result
