# 1. IMPORT
from json import load
from sqlite3 import connect
from pandas import DataFrame, read_sql
import pandas as pd
from rdflib import Graph, URIRef, Literal, RDF, Namespace
from SPARQLWrapper import SPARQLWrapper, POST, JSON

# 2. CLASSI - DATA MODEL CON COSTRUTTORI MA SENZA FILE
class IdentifiableEntity:
    """
    Classe radice della gerarchia del data model. Qualunque entità che possiede un identificatore (DOI, OMID, ISSN) estende questa classe). L'attributo 'id' è una lista perché la stessa entità può avere più identificatori (es. sia un DOI che un OMID).
    """

    def __init__(self):
        self.id = list()

    def getId(self):
        return list(self.id) #restituisce una copia per proteggere l'attributo interno
    
    def setId(self, identifiers):
        self.id = list(identifiers)

class BibliographicEntity(IdentifiableEntity):
    """
    Rappresenta una pubblicazione accademica (articolo, libro, capitolo...). Eredita getId() da IdentifiableEntity.
    """
    
    def __init__(self):
        super().__init__()
        self.title = ""
        self.publicationDate = ""
        self.authors = list() #lista di oggetti PErson
        self.venues = list() #lista di oggetti Venue

    def getTitle(self):
        return self.title
    
    def getPublicationDate(self):
        return self.publicationDate
    
    def getAuthors(self):
        return list(self.authors)
    
    def getVenues(self):
        return list(self.venues)
    
    def setTitle(self, title):
        self.title = title

    def setPublicationDate(self, date):
        self.publicationDate = date

    def setAuthors(self, authors):
        self.authors = list(authors)

    def setVenues(self, venues):
        self.venues = list(venues)

class Person:
    """
    Rappresenta un autore di una pubblicazione. Nel JSON il formato è "Cognome, Nome": il parsing lo fa l'handler.
    """

    def __init__(self):
        self.givenName = ""
        self.familyName = ""

    def getGivenName(self):
        return self.givenName
    
    def getFamilyName(self):
        return self.familyName
    
    def setGivenName(self, name):
        self.givenName = name

    def setFamilyName(self, name):
        self.familyName = name

class Venue(IdentifiableEntity):
    """
    Rappresenta la rivista o il libro in cui è stata pubblicata un'entità. Eredita getId() da IdentifiableEntity.
    """

    def __init__(self):
        super().__init__()
        self.title = ""

    def getTitle(self):
        return self.title
    
    def setTitle(self, title):
        self.title = title

class Citation(IdentifiableEntity):
    """
    Rappresenta una citazione: il legame tra chi cita (citingEntity) e chi è citato (citedEntity). Entrambi sono oggetti BibliographicEntity. Eredita getId() da IdentifiableEntity.
    """

    def __init__(self):
        super().__init__()
        self.citingEntity = None # oggetto BibliographicEntity
        self.citedEntity = None # oggetto BibliographicEntity
        self.creationDate = "" # es. "2020"
        self.timespan = "" # es. "P2Y3M"

    def getCitingEntity(self):
        return self.citingEntity
    
    def getCitedEntity(self):
        return self.citedEntity
    
    def getCreationDate(self):
        return self.creationDate
    
    def getTimespan(self):
        return self.timespan
    
    def setCitingEntity(self, entity):
        self.citingEntity = entity

    def setCitedEntity(self, entity):
        self.citedEntity = entity
    
    def setCreationDate(self, date):
        self.creationDate = date

    def setTimespan(self, timespan):
        self.timespan = timespan

class AuthorSelfCitation(Citation):
    """
    Citaizone in cui almeno un autore è autore sia dell'entità citante che di quella citata. Eredita tutto da Citation.
    """

    def __init__(self):
        super().__init__()


class JournalSelfCitation(Citation):
    """
    Citazione in cui la venue dell'entità citante coincide con quella dell'entità citata. Eredita tutto da Citation.
    """

    def __init__(self):
        super().__init__()


# 3. HANDLER - Classi che parlano con i database

class Handler:
    """
    Classe base per tutti gli Handler. Contiene il percorso o URL del database.
    """

    def __init__(self):
        self.dbPathOrUrl = ""

    def getDbPathOrUrl(self):
        return self.dbPathOrUrl
    
    def setDbPathOrUrl(self, pathOrUrl):
        self.dbPathOrUrl = pathOrUrl
        return True
    
class UploadHandler(Handler):
    """
    Handler per il caricamento dei dati nel database. Il metodo pushDataToDb è implementato nelle sottoclassi.
    """

    def __init__(self):
        super().__init__()

    def pushDataToDb(self, path):
        pass

class QueryHandler(Handler):
    """
    Handlder per le query sul database.
    Il metodo getById è implementato nelle sottoclassi.
    """

    def __init__(self):
        super().__init__()

    def getById(self, id):
        pass

class CitationUploadHandler(UploadHandler):
    """
    Legge il CSV delle citazione e lo carica in Blazegraph come grafi RDF usando rdflib.
    """

    def __init__(self):
        super().__init__()

    def pushDataToDb(self, path):
        pass

class CitationQueryHandler(QueryHandler):
    def __init__(self):
        super().__init__()

    def getById(self, id):
        pass

    def getAllCitations(self):
        pass

    def getAllAuthorSelfCitations(self):
        pass

    def getAllJournalSelfCitations(self):
        pass

    def getCitationsWithinTimespan(self, min_timespan, max_timespan):
        pass

    def getCitationsWithinDate(self, start_date, end_date):
        pass


# Next...JSON, database relazionale (SQLite)
# class BibliographicEntityUploadHandler(UploadHandler):...
# class BibliographicEntityQueryHandler(QueryHandler):...

# E altro next: Query Engine
# class BasicQueryEngine: ...
# class FullQueryEngine(BasicQueryEngine):...
